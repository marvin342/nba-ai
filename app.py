import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats

# --- 1. CONFIG & PRO VISUALS ---
st.set_page_config(page_title="NBA Sharp AI", page_icon="🏀", layout="wide")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.95)), 
                    url("https://images.unsplash.com/photo-1504450758481-7338eba7524a?q=80&w=2069&auto=format&fit=crop");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    .game-card, .prop-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
    }
    .prop-card { border-left: 5px solid #1e88e5; transition: 0.3s; }
    .prop-card:hover { transform: translateY(-3px); background: rgba(255, 255, 255, 0.08); }
    .team-name { font-size: 24px; font-weight: 800; color: #ffffff; }
    .metric-box { text-align: center; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 12px; }
    .value-badge { padding: 5px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; border: 1px solid; }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'results' not in st.session_state: st.session_state.results = None
if 'injuries' not in st.session_state: st.session_state.injuries = {}
if 'live_stats' not in st.session_state: st.session_state.live_stats = {}
if 'smart_props' not in st.session_state: st.session_state.smart_props = []

# --- 2. DATA (Fallback Definitions) ---
NBA_STATS = {
    "Atlanta Hawks": {"ppp": 1.12, "opp_ppp": 1.13, "pace": 105.9, "stars": ["Jalen Johnson", "Zaccharie Risacher"]},
    "Boston Celtics": {"ppp": 1.21, "opp_ppp": 1.10, "pace": 95.3, "stars": ["Jayson Tatum", "Jaylen Brown"]},
    "Brooklyn Nets": {"ppp": 1.07, "opp_ppp": 1.16, "pace": 97.8, "stars": ["Cam Thomas", "Nicolas Claxton"]},
    "Charlotte Hornets": {"ppp": 1.13, "opp_ppp": 1.13, "pace": 101.5, "stars": ["LaMelo Ball", "Brandon Miller"]},
    "Chicago Bulls": {"ppp": 1.13, "opp_ppp": 1.14, "pace": 103.3, "stars": ["Josh Giddey", "Coby White"]},
    "Cleveland Cavaliers": {"ppp": 1.18, "opp_ppp": 1.11, "pace": 101.0, "stars": ["Donovan Mitchell", "Evan Mobley"]},
    "Dallas Mavericks": {"ppp": 1.14, "opp_ppp": 1.11, "pace": 100.1, "stars": ["Luka Doncic", "Kyrie Irving"]},
    "Denver Nuggets": {"ppp": 1.20, "opp_ppp": 1.15, "pace": 99.0, "stars": ["Nikola Jokic", "Jamal Murray"]},
    "Detroit Pistons": {"ppp": 1.17, "opp_ppp": 1.07, "pace": 100.1, "stars": ["Cade Cunningham", "Jaden Ivey"]},
    "Golden State Warriors": {"ppp": 1.15, "opp_ppp": 1.11, "pace": 100.8, "stars": ["Stephen Curry", "Buddy Hield"]},
    "Houston Rockets": {"ppp": 1.15, "opp_ppp": 1.10, "pace": 101.1, "stars": ["Alperen Sengun", "Jalen Green"]},
    "Indiana Pacers": {"ppp": 1.11, "opp_ppp": 1.14, "pace": 100.1, "stars": ["Tyrese Haliburton", "Pascal Siakam"]},
    "Los Angeles Clippers": {"ppp": 1.12, "opp_ppp": 1.14, "pace": 99.5, "stars": ["James Harden", "Kawhi Leonard"]},
    "Los Angeles Lakers": {"ppp": 1.16, "opp_ppp": 1.15, "pace": 98.8, "stars": ["LeBron James", "Anthony Davis"]},
    "Memphis Grizzlies": {"ppp": 1.14, "opp_ppp": 1.12, "pace": 102.1, "stars": ["Ja Morant", "Desmond Bane"]},
    "Miami Heat": {"ppp": 1.17, "opp_ppp": 1.10, "pace": 100.0, "stars": ["Jimmy Butler", "Bam Adebayo"]},
    "Milwaukee Bucks": {"ppp": 1.12, "opp_ppp": 1.14, "pace": 101.0, "stars": ["Giannis Antetokounmpo", "Damian Lillard"]},
    "Minnesota Timberwolves": {"ppp": 1.19, "opp_ppp": 1.10, "pace": 102.5, "stars": ["Anthony Edwards", "Rudy Gobert"]},
    "New Orleans Pelicans": {"ppp": 1.14, "opp_ppp": 1.21, "pace": 101.8, "stars": ["Zion Williamson", "Brandon Ingram"]},
    "New York Knicks": {"ppp": 1.20, "opp_ppp": 1.11, "pace": 98.2, "stars": ["Jalen Brunson", "Karl-Anthony Towns"]},
    "Oklahoma City Thunder": {"ppp": 1.20, "opp_ppp": 1.04, "pace": 101.5, "stars": ["Shai Gilgeous-Alexander", "Chet Holmgren"]},
    "Orlando Magic": {"ppp": 1.15, "opp_ppp": 1.12, "pace": 101.2, "stars": ["Paolo Banchero", "Franz Wagner"]},
    "Philadelphia 76ers": {"ppp": 1.16, "opp_ppp": 1.11, "pace": 100.3, "stars": ["Joel Embiid", "Tyrese Maxey"]},
    "Phoenix Suns": {"ppp": 1.13, "opp_ppp": 1.10, "pace": 100.2, "stars": ["Kevin Durant", "Devin Booker"]},
    "Portland Trail Blazers": {"ppp": 1.15, "opp_ppp": 1.13, "pace": 102.0, "stars": ["Anfernee Simons", "Shaedon Sharpe"]},
    "Sacramento Kings": {"ppp": 1.10, "opp_ppp": 1.17, "pace": 101.8, "stars": ["De'Aaron Fox", "Domantas Sabonis"]},
    "San Antonio Spurs": {"ppp": 1.17, "opp_ppp": 1.09, "pace": 95.4, "stars": ["Victor Wembanyama", "Devin Vassell"]},
    "Toronto Raptors": {"ppp": 1.14, "opp_ppp": 1.10, "pace": 101.8, "stars": ["Scottie Barnes", "RJ Barrett"]},
    "Utah Jazz": {"ppp": 1.18, "opp_ppp": 1.20, "pace": 104.5, "stars": ["Lauri Markkanen", "Keyonte George"]},
    "Washington Wizards": {"ppp": 1.12, "opp_ppp": 1.18, "pace": 106.8, "stars": ["Kyle Kuzma", "Alex Sarr"]}
}

# --- 3. LIVE DATA FETCH ---
def fetch_live_metrics():
    try:
        data = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        live_map = {}
        for _, row in data.iterrows():
            poss = row['FGA'] + (0.44 * row['FTA']) + row['TOV']
            live_map[row['TEAM_NAME']] = {"ppp": row['PTS'] / poss, "opp_ppp": row['OPP_PTS'] / poss, "pace": row['PACE']}
        return live_map
    except: return {}

@st.cache_data(ttl=3600)
def get_prop_avg(player_name):
    from nba_api.stats.static import players
    from nba_api.stats.endpoints import playergamelog
    try:
        search = players.find_players_by_full_name(player_name)
        if not search: return 0
        # Check current season
        log = playergamelog.PlayerGameLog(player_id=search[0]['id'], season='2025-26').get_data_frames()[0]
        return log.head(5)['PTS'].mean()
    except: return 0

# --- 4. ANALYTIC ENGINE ---
def run_sharp_analysis(away, home, line):
    a_base = st.session_state.live_stats.get(away, NBA_STATS.get(away))
    h_base = st.session_state.live_stats.get(home, NBA_STATS.get(home))
    a_stars = NBA_STATS.get(away, {}).get("stars", [])
    h_stars = NBA_STATS.get(home, {}).get("stars", [])
    a_ppp, h_ppp = a_base["ppp"], h_base["ppp"]
    
    for star in a_stars:
        status = st.session_state.injuries.get(star, "Available")
        if status in ["Out", "Doubtful"]: a_ppp -= 0.08
        elif status == "Questionable": a_ppp -= 0.04
    for star in h_stars:
        status = st.session_state.injuries.get(star, "Available")
        if status in ["Out", "Doubtful"]: h_ppp -= 0.08
        elif status == "Questionable": h_ppp -= 0.04

    avg_pace = (a_base["pace"] + h_base["pace"]) / 2
    proj_a = ((a_ppp + h_base["opp_ppp"]) / 2) * avg_pace
    proj_h = (((h_ppp + 0.015) + a_base["opp_ppp"]) / 2) * avg_pace 
    final_proj = proj_a + proj_h
    diff = final_proj - line
    
    if abs(diff) > 12: return ("🚫 STAY AWAY", final_proj, "Unreliable Edge", "#808080")
    if diff > 6.0: return ("🔥 OVER", final_proj, f"Edge: +{min(15.0, diff):.1f}%", "#2ecc71")
    if diff < -6.0: return ("❄️ UNDER", final_proj, f"Edge: +{min(15.0, abs(diff):.1f}%", "#e74c3c")
    return ("🚫 STAY AWAY", final_proj, "Line is too Efficient", "#3498db")

# --- 5. CALLBACKS ---
def sync_all_data():
    with st.spinner("Analyzing Every Game & Prop..."):
        st.session_state.live_stats = fetch_live_metrics()
        API_KEY = "27970d14c8e8eb9f2a217c775db6571f"
        
        try:
            o_res = requests.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds", 
                               params={"api_key": API_KEY, "regions": "us", "markets": "totals"}).json()
            st.session_state.results = o_res
            
            smart_list = []
            # Scans ALL games today
            for game in o_res:
                p_res = requests.get(f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{game['id']}/odds",
                                   params={"api_key": API_KEY, "regions": "us", "markets": "player_points"}).json()
                try:
                    outcomes = p_res['bookmakers'][0]['markets'][0]['outcomes']
                    for o in outcomes: # Scans ALL players with lines
                        if o['name'] == 'Over':
                            avg = get_prop_avg(o['description'])
                            if avg > 0:
                                smart_list.append({"name": o['description'], "line": o['point'], "avg": avg, "match": f"{game['away_team']} @ {game['home_team']}"})
                except: continue
            st.session_state.smart_props = smart_list
        except: st.error("Vegas API Down")

# --- 6. UI DISPLAY ---
st.title("🏀 NBA SHARP AI")
st.markdown("<p style='color:#888; margin-top:-20px;'>REAL-TIME QUANTITATIVE ANALYSIS • 2026 SEASON</p>", unsafe_allow_html=True)

col_left, col_mid, col_right = st.columns([1,1,1])
with col_mid:
    st.button("REFRESH ANALYTICS", on_click=sync_all_data, use_container_width=True)

tab_games, tab_props = st.tabs(["🎮 GAME OVER/UNDERS", "💎 SMART PLAYER PROPS"])

with tab_games:
    if st.session_state.results:
        for game in st.session_state.results:
            h, a = game['home_team'], game['away_team']
            try: line = game['bookmakers'][0]['markets'][0]['outcomes'][0]['point']
            except: continue
            call, proj, status, color = run_sharp_analysis(a, h, line)
            st.markdown(f"""
                <div class="game-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div style="flex: 2;">
                            <span class="team-name">{a}</span> <span style="color:#555;">at</span> <span class="team-name">{h}</span>
                            <div style="display: flex; gap: 20px; margin-top: 20px;">
                                <div class="metric-box"><p style="font-size:10px; color:#888;">VEGAS</p><p style="color:#aaa; font-weight:bold;">{line}</p></div>
                                <div class="metric-box" style="border: 1px solid {color}44;"><p style="font-size:10px; color:{color};">AI PROJ</p><p style="color:#fff; font-weight:bold;">{proj:.1f}</p></div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <h1 style="margin: 0; color: {color}; font-size: 38px; font-weight: 900;">{call.split(' ')[1]}</h1>
                            <p style="color: #fff; font-size: 12px; opacity:0.8;">{status}</p>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

with tab_props:
    if not st.session_state.smart_props:
        st.info("Click Refresh to load smart player projections for today's games.")
    else:
        for prop in st.session_state.smart_props:
            diff = prop['avg'] - prop['line']
            # Smart Logic: Over if average is > 2 pts above line, Under if > 2 pts below, else Fair
            p_color = "#2ecc71" if diff > 2.0 else "#e74c3c" if diff < -2.0 else "#3498db"
            p_call = "VALUE OVER" if diff > 2.0 else "VALUE UNDER" if diff < -2.0 else "FAIR LINE"
            
            st.markdown(f"""
                <div class="prop-card" style="border-left-color: {p_color};">
                    <div style="font-size: 11px; color: #555; margin-bottom: 5px;">{prop['match']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 20px; font-weight: 800; color: #fff;">{prop['name']}</div>
                            <div style="color: #888; font-size: 13px;">Season Avg: {prop['avg']:.1f} PTS</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: #aaa; letter-spacing:1px;">VEGAS LINE</div>
                            <div style="font-size: 24px; font-weight: bold; color: #fff;">{prop['line']}</div>
                            <span class="value-badge" style="background: {p_color}15; color: {p_color}; border-color: {p_color}44;">{p_call}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
