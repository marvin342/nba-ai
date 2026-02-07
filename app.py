import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats

# --- 1. CONFIG & PRO VISUALS (UNTOUCHED) ---
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
    .game-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
    }
    .team-name { font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; }
    .vs-text { color: #555; font-size: 18px; margin: 0 10px; }
    .metric-box { text-align: center; background: rgba(0,0,0,0.3); padding: 10px; border-radius: 12px; min-width: 100px; }
    .metric-label { font-size: 10px; color: #888; text-transform: uppercase; margin-bottom: 2px; letter-spacing: 1px; }
    .metric-value { font-size: 20px; font-weight: 700; color: #fff; }
    .stButton>button {
        background: linear-gradient(45deg, #1e88e5, #1565c0);
        color: white;
        border: none;
        padding: 15px 40px;
        border-radius: 50px;
        font-weight: bold;
        transition: 0.3s;
        box-shadow: 0 4px 15px rgba(30, 136, 229, 0.4);
    }
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 20px rgba(30, 136, 229, 0.6);
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'results' not in st.session_state: st.session_state.results = None
if 'injuries' not in st.session_state: st.session_state.injuries = {}
if 'live_stats' not in st.session_state: st.session_state.live_stats = {}

# --- 2. DATA (Fallback & Star Definitions) ---
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
            live_map[row['TEAM_NAME']] = {
                "ppp": row['PTS'] / poss,
                "opp_ppp": row['OPP_PTS'] / poss,
                "pace": row['PACE']
            }
        return live_map
    except:
        return {}

# --- NEW: PLAYER PROP ENGINE ---
@st.cache_data(ttl=3600)
def get_player_stats(player_name):
    from nba_api.stats.static import players
    from nba_api.stats.endpoints import playergamelog
    try:
        search = players.find_players_by_full_name(player_name)
        if not search: return None
        p_id = search[0]['id']
        # Fetching current 2025-26 Season Log
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2025-26').get_data_frames()[0]
        if log.empty: return "No games found for 2025-26."
        recent = log.head(5)
        return {
            "avg_pts": recent['PTS'].mean(),
            "avg_reb": recent['REB'].mean(),
            "avg_ast": recent['AST'].mean(),
            "last_5": recent[['PTS', 'REB', 'AST']].values.tolist()
        }
    except Exception as e:
        return None

# --- 4. ANALYTIC ENGINE (Logic Preserved) ---
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
    
    if abs(diff) > 12: 
        return ("🚫 STAY AWAY", final_proj, "Unreliable Edge (Trap Line)", "#808080")
    if diff > 6.0: 
        edge = min(15.0, diff)
        return ("🔥 OVER", final_proj, f"Projected Edge: +{edge:.1f}%", "#2ecc71")
    if diff < -6.0: 
        edge = min(15.0, abs(diff))
        return ("❄️ UNDER", final_proj, f"Projected Edge: +{edge:.1f}%", "#e74c3c")
    
    return ("🚫 STAY AWAY", final_proj, "Line is too Efficient", "#3498db")

# --- 5. CALLBACKS ---
def sync_live_data():
    with st.spinner("Syncing Live NBA.com Data & Vegas Odds..."):
        st.session_state.live_stats = fetch_live_metrics()
        today = datetime.now().strftime('%Y-%m-%d')
        inj_url = f"https://nba-injury-reports.p.rapidapi.com/injuries/{today}"
        headers = {"X-RapidAPI-Key": "55ee678671msh2dd4de4a390207bp10cd2bjsnf77bbbf65916", "X-RapidAPI-Host": "nba-injury-reports.p.rapidapi.com"}
        try:
            i_res = requests.get(inj_url, headers=headers)
            if i_res.status_code == 200:
                st.session_state.injuries = {item['player']: item['status'] for item in i_res.json()}
        except: pass
        
        try:
            o_res = requests.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds", 
                               params={"api_key": "27970d14c8e8eb9f2a217c775db6571f", "regions": "us", "markets": "totals"})
            if o_res.status_code == 200:
                st.session_state.results = o_res.json()
        except: st.error("Vegas API Down")

# --- 6. UI DISPLAY ---
st.title("🏀 NBA SHARP AI")
st.markdown("<p style='color:#888; margin-top:-20px;'>REAL-TIME QUANTITATIVE ANALYSIS • 2026 SEASON</p>", unsafe_allow_html=True)

# SIDEBAR PLAYER PROPS
with st.sidebar:
    st.header("👤 Player Prop Research")
    st.markdown("Check recent performance before betting.")
    p_name = st.text_input("Enter Player Name", placeholder="e.g. LeBron James")
    if p_name:
        p_data = get_player_stats(p_name)
        if isinstance(p_data, dict):
            st.subheader(f"Last 5 Avg for {p_name}")
            c1, c2, c3 = st.columns(3)
            c1.metric("PTS", f"{p_data['avg_pts']:.1f}")
            c2.metric("REB", f"{p_data['avg_reb']:.1f}")
            c3.metric("AST", f"{p_data['avg_ast']:.1f}")
            st.caption("Game Log (PTS, REB, AST):")
            st.code(p_data['last_5'])
        else:
            st.warning(p_data if p_data else "Player not found.")

col_left, col_mid, col_right = st.columns([1,1,1])
with col_mid:
    st.button("REFRESH ANALYTICS", on_click=sync_live_data)

st.write("") 

if st.session_state.results:
    for game in st.session_state.results:
        h, a = game['home_team'], game['away_team']
        try: line = game['bookmakers'][0]['markets'][0]['outcomes'][0]['point']
        except: continue
        
        call, proj, status, color = run_sharp_analysis(a, h, line)
        
        st.markdown(f"""
            <div class="game-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="flex: 2;">
                        <span class="team-name">{a}</span>
                        <span class="vs-text">at</span>
                        <span class="team-name">{h}</span>
                        <div style="display: flex; gap: 20px; margin-top: 20px;">
                            <div class="metric-box">
                                <p class="metric-label">Vegas Total</p>
                                <p class="metric-value" style="color:#aaa;">{line}</p>
                            </div>
                            <div class="metric-box" style="border: 1px solid {color}44;">
                                <p class="metric-label" style="color:{color};">AI Project</p>
                                <p class="metric-value">{proj:.1f}</p>
                            </div>
                        </div>
                    </div>
                    <div style="flex: 1; text-align: right;">
                        <h1 style="margin: 0; color: {color}; font-size: 42px; font-weight: 900; line-height: 1;">{call.split(' ')[1]}</h1>
                        <p style="margin: 10px 0 0 0; color: #fff; font-weight: 600; letter-spacing: 1px; opacity: 0.9;">{status}</p>
                        <div style="height: 4px; width: 100px; background: {color}; margin-left: auto; margin-top: 15px; border-radius: 10px;"></div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
