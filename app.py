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
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .game-card, .prop-card {
        background: rgba(255, 255, 255, 0.04); backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px;
        padding: 25px; margin-bottom: 20px;
    }
    .top-pick-card {
        background: linear-gradient(135deg, rgba(46, 204, 113, 0.15), rgba(39, 174, 96, 0.05));
        border: 2px solid #2ecc71; border-radius: 20px; padding: 20px; margin-bottom: 25px;
    }
    .parlay-box {
        background: rgba(30, 136, 229, 0.1); border: 1px dashed #1e88e5;
        border-radius: 15px; padding: 15px; margin-top: 10px;
    }
    .value-badge { padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; border: 1px solid; }
    .injury-tag { color: #ff4b4b; font-size: 10px; font-weight: bold; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# Session State
for key in ['results', 'injuries', 'live_stats', 'smart_props']:
    if key not in st.session_state: st.session_state[key] = [] if key in ['results', 'smart_props'] else {}

# --- 2. THE COMPLETE NBA DICTIONARY (ALL 30 TEAMS) ---
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

@st.cache_data(ttl=3600)
def get_prop_analysis(player_name, team_name):
    from nba_api.stats.static import players
    from nba_api.stats.endpoints import playergamelog
    try:
        search = players.find_players_by_full_name(player_name)
        if not search: return 0
        log = playergamelog.PlayerGameLog(player_id=search[0]['id'], season='2025-26').get_data_frames()[0]
        recent_avg = log.head(5)['PTS'].mean()
        
        # Usage Boost Logic
        team_stars = NBA_STATS.get(team_name, {}).get("stars", [])
        boost = 1.0
        for star in team_stars:
            if star != player_name and st.session_state.injuries.get(star) in ["Out", "Doubtful"]:
                boost += 0.12 # +12% usage for teammates when a star is out
        return recent_avg * boost
    except: return 0

# --- 3. ANALYTIC ENGINE ---
def run_sharp_analysis(away, home, line):
    a_base = st.session_state.live_stats.get(away, NBA_STATS.get(away, {"ppp":1.1, "opp_ppp":1.1, "pace":100}))
    h_base = st.session_state.live_stats.get(home, NBA_STATS.get(home, {"ppp":1.1, "opp_ppp":1.1, "pace":100}))
    a_ppp, h_ppp = a_base["ppp"], h_base["ppp"]
    
    for star in NBA_STATS.get(away, {}).get("stars", []):
        if st.session_state.injuries.get(star) in ["Out", "Doubtful"]: a_ppp -= 0.08
    for star in NBA_STATS.get(home, {}).get("stars", []):
        if st.session_state.injuries.get(star) in ["Out", "Doubtful"]: h_ppp -= 0.08

    avg_pace = (a_base["pace"] + h_base["pace"]) / 2
    proj_total = (((a_ppp + h_base["opp_ppp"])/2) + ((h_ppp + a_base["opp_ppp"])/2)) * avg_pace
    diff = proj_total - line
    
    if diff > 8.0: return ("💎 TOP PICK OVER", proj_total, f"Edge: +{abs(diff):.1f}", "#2ecc71")
    if diff < -8.0: return ("💎 TOP PICK UNDER", proj_total, f"Edge: +{abs(diff):.1f}", "#e74c3c")
    if diff > 4.0: return ("🔥 OVER", proj_total, f"Edge: +{abs(diff):.1f}", "#27ae60")
    if diff < -4.0: return ("❄️ UNDER", proj_total, f"Edge: +{abs(diff):.1f}", "#c0392b")
    return ("🚫 STAY AWAY", proj_total, "No Edge", "#3498db")

# --- 4. CALLBACKS ---
def sync_all_data():
    with st.spinner("🔄 Deep Scanning NBA 2026 Data..."):
        # RapidAPI Injury Sync
        try:
            headers = {"X-RapidAPI-Key": "55ee678671msh2dd4de4a390207bp10cd2bjsnf77bbbf65916", "X-RapidAPI-Host": "nba-injury-reports.p.rapidapi.com"}
            i_res = requests.get(f"https://nba-injury-reports.p.rapidapi.com/injuries/{datetime.now().strftime('%Y-%m-%d')}", headers=headers)
            if i_res.status_code == 200: st.session_state.injuries = {i['player']: i['status'] for i in i_res.json()}
        except: pass

        # Odds & Top Prop Search
        try:
            ODDS_KEY = "27970d14c8e8eb9f2a217c775db6571f"
            o_res = requests.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds", params={"api_key": ODDS_KEY, "regions": "us", "markets": "totals"}).json()
            st.session_state.results = o_res
            
            smart_list = []
            for game in o_res[:5]: # Search more games
                p_res = requests.get(f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{game['id']}/odds", params={"api_key": ODDS_KEY, "regions": "us", "markets": "player_points"}).json()
                try:
                    for o in p_res['bookmakers'][0]['markets'][0]['outcomes']:
                        if o['name'] == 'Over':
                            p_team = game['home_team'] if o['description'] in str(game['home_team']) else game['away_team']
                            proj = get_prop_analysis(o['description'], p_team)
                            if proj > 0:
                                smart_list.append({"name": o['description'], "line": o['point'], "proj": proj, "match": f"{game['away_team']} @ {game['home_team']}"})
                except: continue
            st.session_state.smart_props = sorted(smart_list, key=lambda x: abs(x['proj'] - x['line']), reverse=True)
        except: pass

# --- 5. UI DISPLAY ---
st.title("🏀 NBA SHARP AI")
if st.button("🚀 SCAN FOR TOP PICKS", use_container_width=True): sync_all_data()

tab1, tab2 = st.tabs(["🎮 GAME PICKS", "💎 PLAYER PROPS"])

with tab1:
    if st.session_state.results:
        for game in st.session_state.results:
            h, a = game['home_team'], game['away_team']
            try: line = game['bookmakers'][0]['markets'][0]['outcomes'][0]['point']
            except: continue
            call, proj, edge, color = run_sharp_analysis(a, h, line)
            style = "top-pick-card" if "TOP" in call else "game-card"
            st.markdown(f'<div class="{style}"><h3 style="margin:0; color:{color}">{call}</h3><b>{a} vs {h}</b><br>Vegas: {line} | AI: {proj:.1f} | {edge}</div>', unsafe_allow_html=True)

with tab2:
    if st.session_state.smart_props:
        top_props = [p for p in st.session_state.smart_props if abs(p['proj'] - p['line']) > 4.5]
        if top_props:
            st.subheader("🔥 AI Parlay Builder (Top Props)")
            with st.container():
                st.markdown('<div class="parlay-box">', unsafe_allow_html=True)
                for p in top_props[:3]:
                    st.write(f"✅ **{p['name']}**: {'OVER' if p['proj'] > p['line'] else 'UNDER'} {p['line']} pts")
                st.markdown('</div>', unsafe_allow_html=True)

        for prop in st.session_state.smart_props:
            diff = prop['proj'] - prop['line']
            p_call = "💎 TOP PICK" if abs(diff) > 4.5 else "VALUE"
            p_dir = "OVER" if diff > 0 else "UNDER"
            p_color = "#2ecc71" if diff > 2.0 else "#e74c3c" if diff < -2.0 else "#3498db"
            
            st.markdown(f"""
                <div class="prop-card" style="border-left-color: {p_color};">
                    <div style="display: flex; justify-content: space-between;">
                        <div><b>{prop['name']}</b> ({prop['match']})<br><small>AI Projection: {prop['proj']:.1f} PTS</small></div>
                        <div style="text-align: right;"><b>Line: {prop['line']}</b><br><span class="value-badge" style="color:{p_color}; border-color:{p_color}">{p_call} {p_dir}</span></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
