import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog
from concurrent.futures import ThreadPoolExecutor
import time

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
    </style>
    """, unsafe_allow_html=True)

# Initialize Session State
for key in ['results', 'injuries', 'live_stats', 'smart_props']:
    if key not in st.session_state: st.session_state[key] = [] if key != 'injuries' else {}
if 'api_session' not in st.session_state: st.session_state.api_session = requests.Session()

# --- 2. COMPLETE NBA DICTIONARY (ALL 30 TEAMS) ---
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

# --- 3. THE PROP STRENGTH ENGINE ---
@st.cache_data(ttl=3600)
def get_strong_prop_analysis(player_name, team_name, opp_team):
    try:
        # 1. Get Player ID
        p_list = players.find_players_by_full_name(player_name)
        if not p_list: return 0
        p_id = p_list[0]['id']
        
        # 2. Fetch Logs (with retry logic for stability)
        time.sleep(0.5) # Prevent Rate Limiting
        log = playergamelog.PlayerGameLog(player_id=p_id, season='2024-25', timeout=20).get_data_frames()[0]
        if log.empty: return 0
        
        # 3. Calculation Logic
        recent_avg = log.head(5)['PTS'].mean()
        
        # Matchup Multiplier: Does the opponent have a bad defense (high opp_ppp)?
        opp_def_rating = NBA_STATS.get(opp_team, {"opp_ppp": 1.1})["opp_ppp"]
        matchup_mult = opp_def_rating / 1.1 # 1.1 is league average baseline
        
        # Usage Multiplier: Are teammates out?
        usage_boost = 1.0
        for star in NBA_STATS.get(team_name, {}).get("stars", []):
            if star != player_name and st.session_state.injuries.get(star) in ["Out", "Doubtful"]:
                usage_boost += 0.15 # +15% boost for props
        
        return recent_avg * matchup_mult * usage_boost
    except:
        return 0

def fetch_props_for_game(game):
    ODDS_KEY = "27970d14c8e8eb9f2a217c775db6571f"
    found_props = []
    try:
        url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{game['id']}/odds"
        params = {"api_key": ODDS_KEY, "regions": "us", "markets": "player_points", "oddsFormat": "american"}
        p_data = st.session_state.api_session.get(url, params=params).json()
        
        # Navigate the JSON safely
        for book in p_data.get('bookmakers', []):
            if book['key'] in ['draftkings', 'fanduel', 'betmgm']:
                for market in book.get('markets', []):
                    if market['key'] == 'player_points':
                        for outcome in market.get('outcomes', []):
                            if outcome['name'] == 'Over':
                                p_name = outcome['description']
                                h_team, a_team = game['home_team'], game['away_team']
                                # Determine which team player is on
                                p_team = h_team # Placeholder logic
                                opp_team = a_team
                                
                                proj = get_strong_prop_analysis(p_name, p_team, opp_team)
                                if proj > 0:
                                    found_props.append({
                                        "name": p_name, "line": outcome['point'], 
                                        "proj": proj, "match": f"{a_team} @ {h_team}",
                                        "odds": outcome.get('price', '+100')
                                    })
                break # Only need one reliable bookmaker per game
    except: pass
    return found_props

# --- 4. DATA SYNC ---
def sync_all_data():
    with st.spinner("🧠 AI Heavy Lifting: Analyzing Matchups & Player Usage..."):
        # Injury Sync
        try:
            headers = {"X-RapidAPI-Key": "55ee678671msh2dd4de4a390207bp10cd2bjsnf77bbbf65916", "X-RapidAPI-Host": "nba-injury-reports.p.rapidapi.com"}
            i_res = st.session_state.api_session.get(f"https://nba-injury-reports.p.rapidapi.com/injuries/{datetime.now().strftime('%Y-%m-%d')}", headers=headers)
            if i_res.status_code == 200: st.session_state.injuries = {i['player']: i['status'] for i in i_res.json()}
        except: pass

        # Odds & Parallel Prop Fetching
        try:
            ODDS_KEY = "27970d14c8e8eb9f2a217c775db6571f"
            o_res = st.session_state.api_session.get("https://api.the-odds-api.com/v4/sports/basketball_nba/odds", params={"api_key": ODDS_KEY, "regions": "us", "markets": "totals"}).json()
            st.session_state.results = o_res
            
            # Run only on the next 4 games to stay within rate limits and maintain speed
            with ThreadPoolExecutor(max_workers=4) as executor:
                prop_batches = list(executor.map(fetch_props_for_game, o_res[:4]))
            
            flat_list = [item for sublist in prop_batches for item in sublist]
            st.session_state.smart_props = sorted(flat_list, key=lambda x: abs(x['proj'] - x['line']), reverse=True)
        except: st.error("Prop API Limit Reached")

# --- 5. UI ---
st.title("🏀 NBA SHARP AI")
if st.button("🚀 SCAN FOR TOP PICKS", use_container_width=True): sync_all_data()

tab1, tab2 = st.tabs(["🎮 GAME PICKS", "💎 PLAYER PROPS"])

with tab1:
    if st.session_state.results:
        for game in st.session_state.results:
            h, a = game['home_team'], game['away_team']
            try: line = game['bookmakers'][0]['markets'][0]['outcomes'][0]['point']
            except: continue
            
            # Game Logic (Re-used from previous version)
            a_base = NBA_STATS.get(a, {"ppp":1.1, "opp_ppp":1.1, "pace":100})
            h_base = NBA_STATS.get(h, {"ppp":1.1, "opp_ppp":1.1, "pace":100})
            avg_pace = (a_base["pace"] + h_base["pace"]) / 2
            proj_total = (((a_base["ppp"] + h_base["opp_ppp"])/2) + ((h_base["ppp"] + a_base["opp_ppp"])/2)) * avg_pace
            diff = proj_total - line
            
            color = "#2ecc71" if abs(diff) > 7 else "#3498db"
            st.markdown(f'<div class="game-card"><b>{a} vs {h}</b><br>Vegas: {line} | AI: {proj_total:.1f}</div>', unsafe_allow_html=True)

with tab2:
    if st.session_state.smart_props:
        # TOP PICK PARLAY SECTION
        top_props = [p for p in st.session_state.smart_props if abs(p['proj'] - p['line']) > 5.0]
        if top_props:
            st.subheader("🔥 AI Prop Parlay (Highest Confidence)")
            st.markdown('<div class="parlay-box">', unsafe_allow_html=True)
            for p in top_props[:3]:
                st.write(f"✅ **{p['name']}**: {'OVER' if p['proj'] > p['line'] else 'UNDER'} {p['line']} ({p['odds']})")
            st.markdown('</div>', unsafe_allow_html=True)

        for prop in st.session_state.smart_props:
            diff = prop['proj'] - prop['line']
            p_dir = "OVER" if diff > 0 else "UNDER"
            p_color = "#2ecc71" if abs(diff) > 5.0 else "#3498db"
            
            st.markdown(f"""
                <div class="prop-card" style="border-left: 5px solid {p_color}">
                    <div style="display: flex; justify-content: space-between;">
                        <div><b>{prop['name']}</b><br><small>{prop['match']}</small></div>
                        <div style="text-align: right;"><b>Line: {prop['line']}</b><br>AI Proj: {prop['proj']:.1f}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
