import pandas as pd
import sys
import os
from datetime import datetime

# ---------------- LOAD LOCAL CSV ----------------
def load_local_csv(file_path):
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Normalize isOut values
    if 'isOut' in df.columns:
        df['isOut'] = df['isOut'].astype(str).str.lower().isin(['true', '1'])
    else:
        print("❌ Column 'isOut' not found in match data.")
        sys.exit(1)

    return df

# ---------------- HELPERS ----------------
def get_last_5_unique_matches(df):
    df_sorted = df.sort_values(by='date', ascending=False)
    unique_matches = df_sorted['match_id'].drop_duplicates()
    last_5_ids = unique_matches.head(5).tolist()
    return df[df['match_id'].isin(last_5_ids)]

def get_last_5_batting_matches(df):
    batted_df = df[df['balls'] > 0]
    batted_df_sorted = batted_df.sort_values(by='date', ascending=False)
    unique_batting_matches = batted_df_sorted['match_id'].drop_duplicates()
    last_5_batting_ids = unique_batting_matches.head(5).tolist()
    return df[df['match_id'].isin(last_5_batting_ids)]

def calculate_stats(df):
    if df.empty:
        return {
            "batting_average": 0.0,
            "strike_rate": 0.0,
            "boundaries_per_match": 0.0,
            "runs_per_match": 0.0,
            "balls_faced_per_match": 0.0
        }

    total_runs = df['runs'].sum()
    total_balls = df['balls'].sum()
    total_fours = df['fours'].sum()
    total_sixes = df['sixes'].sum()
    times_out = df['isOut'].sum()
    matches = df['match_id'].nunique()

    batting_average = total_runs / times_out if times_out > 0 else total_runs
    strike_rate = (total_runs / total_balls) * 100 if total_balls > 0 else 0
    boundaries_per_match = (total_fours + total_sixes) / matches if matches > 0 else 0
    runs_per_match = total_runs / matches if matches > 0 else 0
    balls_faced_per_match = total_balls / matches if matches > 0 else 0

    return {
        "batting_average": round(batting_average, 4),
        "strike_rate": round(strike_rate, 2),
        "boundaries_per_match": round(boundaries_per_match, 4),
        "runs_per_match": round(runs_per_match, 4),
        "balls_faced_per_match": round(balls_faced_per_match, 4)
    }

def process_player_row(player_input, sheet_df):
    player_id = player_input['player_id']
    cutoff_date = pd.to_datetime(player_input['cutoff_date'])
    player_name = player_input['player_name']
    bat_team = player_input['bat_team']
    bowl_team = player_input['bowl_team']
    innings = int(player_input['innings'])
    season = str(player_input['season'])
    venue = player_input['venue']

    print(f"\n📊 Processing player: {player_name} (ID: {player_id})")

    player_df = sheet_df[
        (sheet_df['batter_id'] == player_id) &
        (sheet_df['date'] < cutoff_date)
    ].copy()

    result = {**player_input}

    if player_df.empty:
        print(f"⚠️ No match data found for player {player_name} before {cutoff_date.date()}")
        return result  # If no data, just return input

    # ------- Grouped by league -------
    leagues = player_df['league'].dropna().unique()
    for league in leagues:
        league_df = player_df[player_df['league'] == league]

        # Career by league
        league_career = calculate_stats(league_df)
        for key, value in league_career.items():
            result[f"career_{league}_{key}"] = value

        # Season by league
        league_season_df = league_df[league_df['date'].dt.year == int(season)]
        league_season = calculate_stats(league_season_df)
        for key, value in league_season.items():
            result[f"season_{league}_{key}"] = value

        # Innings by league
        league_innings_df = league_df[league_df['inns'] == innings]
        league_innings = calculate_stats(league_innings_df)
        for key, value in league_innings.items():
            result[f"innings_{league}_{key}"] = value

    # ------- Last 5 matches (not league specific) -------
    last5_df = get_last_5_unique_matches(player_df[player_df['date'].dt.year == int(season)])
    if len(last5_df['match_id'].unique()) < 5:
        additional_df = get_last_5_unique_matches(player_df[player_df['date'].dt.year < int(season)])
        last5_df = pd.concat([last5_df, additional_df]).drop_duplicates(subset='match_id').head(5)

    last5_batting_df = get_last_5_batting_matches(player_df[player_df['date'].dt.year == int(season)])
    if len(last5_batting_df['match_id'].unique()) < 5:
        additional_batting_df = get_last_5_batting_matches(player_df[player_df['date'].dt.year < int(season)])
        last5_batting_df = pd.concat([last5_batting_df, additional_batting_df]).drop_duplicates(subset='match_id').head(5)

    last5_stats_regular = calculate_stats(last5_df)
    last5_stats_batting = calculate_stats(last5_batting_df)

    result['last5_batting_average'] = last5_stats_batting['batting_average']
    result['last5_strike_rate'] = last5_stats_batting['strike_rate']
    result['last5_boundaries_per_match'] = last5_stats_regular['boundaries_per_match']
    result['last5_runs_per_match'] = last5_stats_regular['runs_per_match']
    result['last5_balls_faced_per_match'] = last5_stats_regular['balls_faced_per_match']

    # ------- Venue stats (still overall) -------
    venue_df = player_df[player_df['venue'] == venue]
    venue_stats = calculate_stats(venue_df)
    for key, value in venue_stats.items():
        result[f"venue_{key}"] = value

    return result


# ---------------- MAIN ----------------
def main():
    input_csv_path = "Today_Match_Details/match_1.csv"  # 🔁 Update if needed
    output_csv_path = "scripts/player_output_bat.csv"               # 🔁 Update if needed
    MATCH_DATA_PATH = "data/mbm/all_league/all_league_bat_final.csv"

    print(f"📂 Loading match data from: {MATCH_DATA_PATH}")
    sheet_df = load_local_csv(MATCH_DATA_PATH)

    for col in ['runs', 'balls', 'fours', 'sixes', 'inns']:
        sheet_df[col] = pd.to_numeric(sheet_df[col], errors='coerce').fillna(0).astype(int)

    input_df = pd.read_csv(input_csv_path)

    try:
        input_df['Date'] = input_df['Date'] + ", 2025"
        input_df['Date'] = pd.to_datetime(input_df['Date'], format="%d %b, %Y", errors='coerce')
    except Exception as e:
        print(f"❌ Error parsing Date column: {e}")
        sys.exit(1)

    if input_df['Date'].isnull().any():
        print("⚠️ Warning: Some rows have invalid dates and will be dropped.")
        input_df = input_df.dropna(subset=['Date'])

    input_df['Cricinfo ID'] = pd.to_numeric(input_df['Cricinfo ID'], errors='coerce')

    output_rows = []
    for _, row in input_df.iterrows():
        player_input = {
            "player_id": row['Cricinfo ID'],
            "player_name": row['Player Name'],
            "bat_team": row['Team'],
            "bowl_team": row['Opponent'],
            "innings": row['Innings'],
            "season": 2025,
            "venue": row['Venue'],
            "cutoff_date": row['Date']
        }
        result_row = process_player_row(player_input, sheet_df)
        output_rows.append(result_row)

    output_df = pd.DataFrame(output_rows)

    file_exists = os.path.exists(output_csv_path)
    output_df.to_csv(output_csv_path, index=False, mode='a' if file_exists else 'w', header=not file_exists)
    print(f"\n✅ Player stats written to: {output_csv_path}")

# ---------------- RUN ----------------
if __name__ == "__main__":
    main()
