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
    .injury-alert { color: #ff4b4b; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-top: 5px; }
    .value-badge { padding: 4px 10px; border-radius: 50px; font-size: 10px; font-weight: bold; border: 1px solid; }
    </style>
    """, unsafe_allow_html=True)

# Session State Initialization
for key in ['results', 'injuries', 'live_stats', 'smart_props']:
    if key not in st.session_state: st.session_state[key] = [] if key in ['results', 'smart_props'] else {}

# --- 2. DATA UTILITIES ---
NBA_STATS = {
    "Oklahoma City Thunder": {"ppp": 1.20, "opp_ppp": 1.04, "pace": 101.5, "stars": ["Shai Gilgeous-Alexander", "Chet Holmgren"]},
    "Los Angeles Lakers": {"ppp": 1.16, "opp_ppp": 1.15, "pace": 98.8, "stars": ["LeBron James", "Anthony Davis"]},
    # ... add other teams as needed
}

def fetch_live_metrics():
    try:
        data = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        return {row['TEAM_NAME']: {"ppp": row['PTS']/(row['FGA']+(0.44*row['FTA'])+row['TOV']), "opp_ppp": row['OPP_PTS']/(row['FGA']+(0.44*row['FTA'])+row['TOV']), "pace": row['PACE']} for _, row in data.iterrows()}
    except: return {}

@st.cache_data(ttl=3600)
def get_prop_avg(player_name):
    from nba_api.stats.static import players
    from nba_api.stats.endpoints import playergamelog
    try:
        search = players.find_players_by_full_name(player_name)
        if not search: return 0
        log = playergamelog.PlayerGameLog(player_id=search[0]['id'], season='2025-26').get_data_frames()[0]
        return log.head(5)['PTS'].mean()
    except: return 0

# --- 3. ANALYTIC ENGINE ---
def run_sharp_analysis(away, home, line):
    a_base = st.session_state.live_stats.get(away, NBA_STATS.get(away, {"ppp": 1.1, "opp_ppp": 1.1, "pace": 100}))
    h_base = st.session_state.live_stats.get(home, NBA_STATS.get(home, {"ppp": 1.1, "opp_ppp": 1.1, "pace": 100}))
    
    a_ppp, h_ppp = a_base["ppp"], h_base["ppp"]
    
    # RapidAPI Injury Adjustment
    for star in NBA_STATS.get(away, {}).get("stars", []):
        if st.session_state.injuries.get(star) in ["Out", "Doubtful"]: a_ppp -= 0.08
    for star in NBA_STATS.get(home, {}).get("stars", []):
        if st.session_state.injuries.get(star) in ["Out", "Doubtful"]: h_ppp -= 0.08

    avg_pace = (a_base["pace"] + h_base["pace"]) / 2
    proj_total = (((a_ppp + h_base["opp_ppp"])/2) + ((h_ppp + a_base["opp_ppp"])/2)) * avg_pace
    diff = proj_total - line
    
    color = "#2ecc71" if diff > 6.0 else "#e74c3c" if diff < -6.0 else "#3498db"
    call = "🔥 OVER" if diff > 6.0 else "❄️ UNDER" if diff < -6.0 else "🚫 STAY AWAY"
    return (call, proj_total, f"Edge: {abs(diff):.1f} pts", color)

# --- 4. SYNC FUNCTION (The "Brain") ---
def sync_all_data():
    with st.spinner("🔄 Deep Sync: Injuries, Vegas, and NBA Stats..."):
        # A. Live NBA.com Stats
        st.session_state.live_stats = fetch_live_metrics()
        
        # B. RAPID API INJURIES
        RAPID_KEY = "55ee678671msh2dd4de4a390207bp10cd2bjsnf77bbbf65916"
        today = datetime.now().strftime('%Y-%m-%d')
        try:
            inj_res = requests.get(f"https://nba-injury-reports.p.rapidapi.com/injuries/{today}", 
                                   headers={"X-RapidAPI-Key": RAPID_KEY, "X-RapidAPI-Host": "nba-injury-reports.p.rapidapi.com"})
            if inj_res.status_code == 200:
                st.session_state.injuries = {i['player']: i['status'] for i in inj_res.json()}
        except: st.error("Injury API Connection Failed")

        # C. VEGAS ODDS & PROPS
        ODDS_KEY = "27970d14c8e8eb9f2a217c775db6571f"
        try:
            o_res = requests.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds", 
                               params={"api_key": ODDS_KEY, "regions": "us", "markets": "totals"}).json()
            st.session_state.results = o_res
            
            smart_list = []
            for game in o_res[:3]: # Limit to first 3 games for speed
                p_res = requests.get(f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{game['id']}/odds",
                                   params={"api_key": ODDS_KEY, "regions": "us", "markets": "player_points"}).json()
                try:
                    for o in p_res['bookmakers'][0]['markets'][0]['outcomes'][:5]:
                        if o['name'] == 'Over':
                            avg = get_prop_avg(o['description'])
                            if avg > 0:
                                smart_list.append({"name": o['description'], "line": o['point'], "avg": avg, "match": f"{game['away_team']} @ {game['home_team']}"})
                except: continue
            st.session_state.smart_props = smart_list
        except: st.error("Vegas API Down")

# --- 5. UI RENDER ---
st.title("🏀 NBA SHARP AI")
col1, col2, col3 = st.columns([1,1,1])
with col2: st.button("REFRESH ALL DATA", on_click=sync_all_data, use_container_width=True)

tab_games, tab_props = st.tabs(["🎮 GAME PROJECTIONS", "💎 SMART PLAYER PROPS"])

with tab_games:
    if st.session_state.results:
        for game in st.session_state.results:
            h, a = game['home_team'], game['away_team']
            try: line = game['bookmakers'][0]['markets'][0]['outcomes'][0]['point']
            except: continue
            call, proj, status, color = run_sharp_analysis(a, h, line)
            st.markdown(f'<div class="game-card"><b>{a} @ {h}</b><br>Vegas: {line} | AI: {proj:.1f}<br><span style="color:{color}">{call} ({status})</span></div>', unsafe_allow_html=True)

with tab_props:
    if st.session_state.smart_props:
        for prop in st.session_state.smart_props:
            status = st.session_state.injuries.get(prop['name'], "Active")
            is_out = status in ["Out", "Doubtful"]
            diff = prop['avg'] - prop['line']
            
            p_color = "#808080" if is_out else ("#2ecc71" if diff > 2.0 else "#e74c3c" if diff < -2.0 else "#3498db")
            p_call = status.upper() if is_out else ("VALUE OVER" if diff > 2.0 else "VALUE UNDER" if diff < -2.0 else "FAIR LINE")

            st.markdown(f"""
                <div class="prop-card" style="border-left-color: {p_color}; opacity: {'0.5' if is_out else '1'};">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <div style="font-size: 18px; font-weight: 800; color: #fff;">{prop['name']}</div>
                            <div style="color: #888; font-size: 12px;">{prop['match']} | Avg: {prop['avg']:.1f} PTS</div>
                            {f'<div class="injury-alert">⚠️ {status}</div>' if is_out else ''}
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 22px; font-weight: bold; color: #fff;">{prop['line']}</div>
                            <span class="value-badge" style="color: {p_color}; border-color: {p_color};">{p_call}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
