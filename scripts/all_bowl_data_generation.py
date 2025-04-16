import pandas as pd
import os
import sys
from datetime import datetime

# ---------------- CONFIG ----------------
MATCH_DATA_PATH = 'data/mbm/all_league/all_league_bowl_final.csv'  # Update with your actual local match data CSV path
INPUT_CSV_PATH = 'Today_Match_Details/match_1.csv'             # Update with your actual input CSV path
OUTPUT_CSV_PATH = 'scripts/player_output_bowl.csv'                  # Update with your actual output CSV path

# ---------------- LOAD MATCH DATA ----------------
def load_match_data():
    if not os.path.exists(MATCH_DATA_PATH):
        print(f"Error: The match data file '{MATCH_DATA_PATH}' does not exist.")
        exit(1)
    match_df = pd.read_csv(MATCH_DATA_PATH)
    
    # Debug: print first few rows to verify match data
    print("Loaded match data (first few rows):")
    print(match_df.head())
    
    # Parse numeric columns
    for col in ['runs', 'balls', 'wickets']:
        match_df[col] = pd.to_numeric(match_df[col], errors='coerce').fillna(0)
    match_df['bowler_id'] = pd.to_numeric(match_df['bowler_id'], errors='coerce').fillna(0).astype(int)
    
    # Convert the date column and drop any rows where conversion fails
    match_df['date'] = pd.to_datetime(match_df['date'], errors='coerce')
    match_df = match_df.dropna(subset=['date'])
    
    return match_df

# ---------------- STAT CALCULATIONS ----------------
def calculate_bowling_stats(df):
    if df.empty:
        print("Warning: Empty dataframe passed to calculate_bowling_stats")
        return {
            "average": 0.0,
            "strike_rate": 0.0,
            "economy": 0.0,
            "wickets_per_match": 0.0,
            "overs_per_match": 0.0
        }

    runs = df['runs'].sum()
    balls = df['balls'].sum()
    wickets = df['wickets'].sum()
    match_count = df['match_id'].nunique()

    average = runs / wickets if wickets else runs
    strike_rate = balls / wickets if wickets else balls
    economy = (runs / balls * 6) if balls else 0.0
    wickets_per_match = wickets / match_count if match_count else 0.0
    overs_per_match = balls / 6 / match_count if match_count else 0.0

    return {
        "average": round(average, 2),
        "strike_rate": round(strike_rate, 2),
        "economy": round(economy, 2),
        "wickets_per_match": round(wickets_per_match, 2),
        "overs_per_match": round(overs_per_match, 2)
    }

# ---------------- GET LAST 5 MATCHES ----------------
def get_last_5_unique_matches(df):
    df_sorted = df.sort_values(by='date', ascending=False)
    return df_sorted.drop_duplicates(subset='match_id').head(5)

# ---------------- PROCESS BOWLER ----------------
def process_bowler_row(player_input, match_df):
    player_id = int(player_input['player_id'])
    cutoff_date = pd.to_datetime(player_input['cutoff_date'])
    innings = int(player_input['innings'])
    season = int(player_input['season'])
    venue = player_input['venue']
    
    # Check if bowler_id exists in match data
    if player_id not in match_df['bowler_id'].values:
        print(f"Warning: Bowler ID {player_id} for player {player_input['player_name']} not found in match data.")
        return {**player_input}

    bowler_df = match_df[(match_df['bowler_id'] == player_id) & (match_df['date'] < cutoff_date)]
    
    if bowler_df.empty:
        print(f"No records found for player ID: {player_id}")
        return {**player_input}

    # Make sure all dates in bowler_df are Timestamps
    bowler_df['date'] = pd.to_datetime(bowler_df['date'], errors='coerce')
    
    result = {**player_input}

    # CAREER BY LEAGUE
    for league, group in bowler_df.groupby('league'):
        stats = calculate_bowling_stats(group)
        league_clean = league.lower().replace(" ", "_")
        for key, value in stats.items():
            result[f"career_{league_clean}_{key}"] = value

    # INNINGS BY LEAGUE
    innings_df = bowler_df[bowler_df['inns'] == innings]
    for league, group in innings_df.groupby('league'):
        stats = calculate_bowling_stats(group)
        league_clean = league.lower().replace(" ", "_")
        for key, value in stats.items():
            result[f"innings_{league_clean}_{key}"] = value

    # SEASON BY LEAGUE
    season_df = bowler_df[bowler_df['date'].dt.year == season]
    for league, group in season_df.groupby('league'):
        stats = calculate_bowling_stats(group)
        league_clean = league.lower().replace(" ", "_")
        for key, value in stats.items():
            result[f"season_{league_clean}_{key}"] = value

    # VENUE
    venue_df = bowler_df[bowler_df['venue'] == venue]
    venue_stats = calculate_bowling_stats(venue_df)
    for key, value in venue_stats.items():
        result[f"venue_{key}"] = value

    # LAST 5 MATCHES
    last5_df = get_last_5_unique_matches(bowler_df)
    last5_stats = calculate_bowling_stats(last5_df)
    for key, value in last5_stats.items():
        result[f"last5_{key}"] = value

    return result

# ---------------- MAIN ----------------
def main():
    match_df = load_match_data()

    input_df = pd.read_csv(INPUT_CSV_PATH)

    try:
        input_df['Date'] = input_df['Date'] + ", 2025"  # Append year
        input_df['Date'] = pd.to_datetime(input_df['Date'], format="%d %b, %Y", errors='coerce')
    except Exception as e:
        print(f"❌ Error parsing Date column: {e}")
        sys.exit(1)

    if input_df['Date'].isnull().any():
        print("⚠️ Warning: Some rows have invalid dates and will be dropped.")
        input_df = input_df.dropna(subset=['Date'])

    input_df['Cricinfo ID'] = pd.to_numeric(input_df['Cricinfo ID'], errors='coerce').fillna(0).astype(int)

    output_rows = []
    print(f"Processing {len(input_df)} players...")

    for _, row in input_df.iterrows():
        player_input = {
            "player_id": row['Cricinfo ID'],
            "player_name": row['Player Name'],
            "bowl_team": row['Team'],
            "bat_team": row['Opponent'],
            "innings": row['Innings'],
            "season": 2025,
            "venue": row['Venue'],
            "cutoff_date": row['Date']
        }
        
        if player_input['player_id'] not in match_df['bowler_id'].values:
            print(f"Player ID {player_input['player_id']} not found in match data.")
            continue
        
        player_output = process_bowler_row(player_input, match_df)
        output_rows.append(player_output)

    if output_rows:
        output_df = pd.DataFrame(output_rows)

        file_exists = os.path.exists(OUTPUT_CSV_PATH)
        output_df.to_csv(OUTPUT_CSV_PATH, index=False, mode='a' if file_exists else 'w', header=not file_exists)
        print(f"✅ Bowler stats saved to {OUTPUT_CSV_PATH}")
    else:
        print("No valid player data found to save.")

if __name__ == "__main__":
    main()
