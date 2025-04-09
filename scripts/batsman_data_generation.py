import pandas as pd
import sys
import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

# ---------------- CONFIG ----------------
SHEET_NAME = 'Sheet1'
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# ---------------- LOAD GOOGLE SHEET ----------------
def load_google_sheet(sheet_url):
    load_dotenv(dotenv_path="cricket-ipl-api/.env")

    private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCfMj6CXlqkKilX\nywe8SocjseYIqRQ7OpnAQB7Ly/DPbQFF++0Bx+rk7xCg3RAApsxOG6OhsLTmUAdK\nlwn3Un+4WZC/W4A7fkl3dbxubiZMUocCXiIqpF4NEobbms+xYtiywWlyLIKVBXz3\npWPa3iODhKu8BmcV2YBg1r4dyJjdKmOXzqy7a1eNNm8//FlDa67oqSCEcpcGSDlQ\nm8ZL6kyHn9Bnu1qVDFxyVjlfFy70G6A7zYOx1lcgTl9W7SJPWXYF+s7kGuZY0lef\n2GPj7q6qlCFd6Q1qg0tb6shVtiKAYl8rYWn8aFE+TyAFR0UPP6IyAtJW9zmKKrQv\nBKdVO5CZAgMBAAECggEASj7fomOo+GllcLmS+QD1N/OPKjjY46q37E67TibmP4dC\nEcalya/YYD8SzUNsZDFmlYMUdKN6KvPmAqagkkVapbq35FcjXhvO3bT+Va5vlCbl\nKniGjMatyoD6fk8cUEmecPf9Wq9hk2jE2Ka9BGWXwI3OnlmKGEmhMwjUEAXvLS4M\nZuQ7XJephacqYguYxOfiZDmMa8BEnPo4kmIQW6oQrUi8L4kAdxI7nUBQM8O4gN0y\nLvrHJAWuL8O7C2vU9+qRWjUCM28fB68YhdEznTb+4Nc2AYXazOa+oHh6y5dSARy8\nHmYBtGlFoNEfxteyRcZNCUF5hd2b+PoKEffPO6NzdQKBgQDRmK/svjci6pqox6s5\n1Bp8ALs+mzEypRJT9QVIE7JYIzeDiZHnh6NQGRqAkEyjlt+V276VLwAiBLuIhnKF\n9fYW7xeh8+E9Wa40E1mvKyPFljD3zq6kFHLDeK8pwFRCtZCsCfDD51EvUQGyrhP2\naZ1zadVeaM7oB1nbbLGdE0wdMwKBgQDCcQXbBucVCjEroO4oiO7CDWTNVpOHS6c0\naPENWBFBreQ0cTxaZwPU8sZ32rogQJFA3610nUetoPbHPizU64eG0RUKV+3bbX82\nnMViS01AK6D+BFqHdxoKgvaCnehfcw2xMdrq2/gRLvPR7oj4yOxoqTeSik11Bug9\nRkZD/sHjAwKBgQCmRxOKJX1oXeZEb+MPBY3dQldJ26S0IPDhWkjOXZHnCklIOSNf\nIuQU71VvGQsz3MWUBbi0cY0Rb9+297JzRCXvG88L1IakPTlOZuuHZBoE7pn6fiVe\nVjqViHCuFr7CDXiwg1JWmHR3rTRDpIaBvlgC77suIsfCm9JVmW1ux5hisQKBgEAa\nTtnkrq5LC+bcSWfnrP8gt0jS8BQ8psUqi73geN/0WjXH1yPerm64EyJUY+RaJQkE\nNQUrDQR6+qC5KMKRW77gk1Uzo+Ehej0g9hnvxWoQeCUGfmoGo/kvL+Hj+UXugmcW\njpu7JU9U8WEWiOWsJ/RhRUb0fZDFVC9PSb8E8BrNAoGARf8Qmhemf55NFTRsFRdO\nKhDIRUdfmSZGkSjvdgZzMmRwYXiosJJpPUEB5VoDbdxV8mnJdlom4mM/9JuLhhJ8\ni5aOaHBlmXAYIC8Svhja4HVFH9iLrqG772BGH0xzowUPYzYITJedK7iPGptMEAk8\n0nP0fdL2zqDJRn41LTuBqCY=\n-----END PRIVATE KEY-----\n"
    client_email = "ipl-933@ipl-fifs.iam.gserviceaccount.com"
    project_id = "1dumS1w_IQ7pv448tm-RKVqAQTEgOMKw59wf914qLHs0"

    service_account_info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": "dummy_key_id",
        "private_key": private_key,
        "client_email": client_email,
        "client_id": "dummy_client_id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}"
    }

    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# ---------------- HELPERS ----------------
def get_last_5_unique_matches(df):
    df_sorted = df.sort_values(by='date', ascending=False)
    unique_matches = df_sorted['match_id'].drop_duplicates()
    last_5_ids = unique_matches.head(5).tolist()
    return df[df['match_id'].isin(last_5_ids)]

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
    times_out = df['isOut'].apply(lambda x: str(x).lower() == 'true').sum()
    matches = df['match_id'].nunique()

    batting_average = total_runs / times_out if times_out > 0 else total_runs
    strike_rate = (total_runs / total_balls) * 100 if total_balls > 0 else 0
    boundaries_per_match = (total_fours + total_sixes) / matches if matches > 0 else 0
    runs_per_match = total_runs / matches if matches > 0 else 0
    balls_faced_per_match = total_balls / matches if matches > 0 else 0

    return {
        "batting_average": round(batting_average, 4),
        "strike_rate": round(strike_rate, 42),
        "boundaries_per_match": round(boundaries_per_match, 4),
        "runs_per_match": round(runs_per_match, 4),
        "balls_faced_per_match": round(balls_faced_per_match, 4)
    }

def process_player_row(player_input, sheet_df):
    player_id = player_input['player_id']
    player_name = player_input['player_name']
    bat_team = player_input['bat_team']
    bowl_team = player_input['bowl_team']
    innings = int(player_input['innings'])
    season = str(player_input['season'])
    venue = player_input['venue']

    player_df = sheet_df[sheet_df['batter_cricinfo_id'] == player_id].copy()

    if player_df.empty:
        return {**player_input,
                **{f"{cat}_{stat}": 0.0 for cat in ['career', 'last5', 'innings', 'venue', 'season'] 
                                      for stat in ['batting_average', 'strike_rate', 'boundaries_per_match', 'runs_per_match', 'balls_faced_per_match']}}

    player_df['date'] = pd.to_datetime(player_df['date'])

    # Career stats
    career_stats = calculate_stats(player_df)

    # Last 5 matches (consider across seasons if fewer than 5 matches in the current season)
    last5_df = player_df[player_df['date'].dt.year == int(season)]
    last5_df = get_last_5_unique_matches(last5_df)

    # Check if fewer than 5 matches are present in the current season
    if len(last5_df['match_id'].unique()) < 5:
        remaining_matches = 5 - len(last5_df['match_id'].unique())
    
        # Get matches from previous seasons
        additional_df = player_df[player_df['date'].dt.year < int(season)]
        additional_df = get_last_5_unique_matches(additional_df)
    
        # Combine current season and previous seasons matches
        last5_df = pd.concat([last5_df, additional_df]).drop_duplicates(subset='match_id').head(5)

    last5_stats = calculate_stats(last5_df)

    # Innings stats
    innings_df = player_df[player_df['innings'] == innings]
    innings_stats = calculate_stats(innings_df)

    # Venue stats
    venue_df = player_df[player_df['venue'] == venue]
    venue_stats = calculate_stats(venue_df)

    # Season stats
    season_df = player_df[player_df['date'].dt.year == int(season)]
    season_stats = calculate_stats(season_df)

    # Combine all stats
    result = {**player_input}
    for prefix, stats in zip(['career', 'last5', 'innings', 'venue', 'season'], [career_stats, last5_stats, innings_stats, venue_stats, season_stats]):
        for key, value in stats.items():
            result[f"{prefix}_{key}"] = value

    return result

# ---------------- MAIN ----------------
def main():
    if len(sys.argv) != 3:
        print("Usage: python analyze_players.py <input_csv_path> <output_csv_path>")
        sys.exit(1)

    input_csv_path = sys.argv[1]
    output_csv_path = sys.argv[2]

    # Put your sheet URL here
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1dumS1w_IQ7pv448tm-RKVqAQTEgOMKw59wf914qLHs0/edit?usp=sharing"  # Replace this!

    # Load Google Sheet
    sheet_df = load_google_sheet(SHEET_URL)

    # Ensure numeric columns are parsed properly
    for col in ['runs', 'balls', 'fours', 'sixes', 'innings']:
        sheet_df[col] = pd.to_numeric(sheet_df[col], errors='coerce').fillna(0).astype(int)

    # Read input CSV
    input_df = pd.read_csv(input_csv_path)
    # Convert Cricinfo ID column to integer type
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
            "venue": row['Venue']
        }
        result_row = process_player_row(player_input, sheet_df)
        output_rows.append(result_row)

    output_df = pd.DataFrame(output_rows)

    file_exists = os.path.exists(output_csv_path)
    output_df.to_csv(output_csv_path, index=False, mode='a' if file_exists else 'w', header=not file_exists)
    print("✅ Player stats updated in:", output_csv_path)

if __name__ == "__main__":
    main()