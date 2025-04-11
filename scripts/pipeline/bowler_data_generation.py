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
    """Gets the last 5 unique matches regardless of whether the player bowled or not"""
    df_sorted = df.sort_values(by='date', ascending=False)
    unique_matches = df_sorted['match_id'].drop_duplicates()
    last_5_ids = unique_matches.head(5).tolist()
    return df[df['match_id'].isin(last_5_ids)]

def get_last_5_bowling_matches(df):
    """Gets the last 5 unique matches where the player actually bowled (excluding DNB - Did Not Bowl)"""
    # Filter out matches where player didn't bowl any balls
    bowled_df = df[df['balls'] > 0]
    bowled_df_sorted = bowled_df.sort_values(by='date', ascending=False)
    unique_bowling_matches = bowled_df_sorted['match_id'].drop_duplicates()
    last_5_bowling_ids = unique_bowling_matches.head(5).tolist()
    return df[df['match_id'].isin(last_5_bowling_ids)]

def calculate_stats(df):
    if df.empty:
        return {
            "average": 0.0,
            "strike_rate": 0.0,
            "economy": 0.0,
            "wickets_per_match": 0.0,
            "overs_per_match": 0.0
        }

    total_runs_conceded = df['runs'].sum()
    total_balls_bowled = df['balls'].sum()
    total_wickets = df['wickets'].sum()
    matches = df['match_id'].nunique()

    if total_balls_bowled > 0:
        economy = (total_runs_conceded / total_balls_bowled) * 6
    else:
        economy = 0.0

    average = total_runs_conceded / total_wickets if total_wickets > 0 else total_runs_conceded
    strike_rate = total_balls_bowled / total_wickets if total_wickets > 0 else total_balls_bowled
    wickets_per_match = total_wickets / matches if matches > 0 else 0
    overs_per_match = total_balls_bowled / 6 / matches if matches > 0 else 0

    return {
        "average": round(average, 4),
        "strike_rate": round(strike_rate, 4),
        "economy": round(economy, 4),
        "wickets_per_match": round(wickets_per_match, 4),
        "overs_per_match": round(overs_per_match, 4)
    }

def process_player_row(player_input, sheet_df):
    player_id = int(player_input['player_id'])  # Ensure player_id is an integer
    cutoff_date = pd.to_datetime(player_input['cutoff_date'])  # Parse cutoff_date
    player_name = player_input['player_name']
    bowl_team = player_input['bowl_team']
    bat_team = player_input['bat_team']
    innings = int(player_input['innings'])
    season = str(player_input['season'])
    venue = player_input['venue']

    print(f"Processing player: {player_name} with ID: {player_id}")  # Debug statement

    # Ensure key_cricinfo is treated as an integer
    sheet_df = sheet_df[pd.to_numeric(sheet_df['key_cricinfo'], errors='coerce').notnull()]
    sheet_df['key_cricinfo'] = sheet_df['key_cricinfo'].astype(int)
    player_df = sheet_df[(sheet_df['key_cricinfo'] == player_id) & (pd.to_datetime(sheet_df['date']) < cutoff_date)].copy()

    if player_df.empty:
        print(f"Player {player_name} with ID {player_id} not found in Google Sheet.")
        return {**player_input,
                **{f"{cat}_{stat}": 0.0 for cat in ['career', 'last5', 'innings', 'venue', 'season']
                                      for stat in ['average', 'strike_rate', 'economy', 'wickets_per_match', 'overs_per_match']}}
    else:
        print(f"Player {player_name} with ID {player_id} found in Google Sheet.")

    player_df['date'] = pd.to_datetime(player_df['date'])

    # Career stats
    career_stats = calculate_stats(player_df)

    # Last 5 matches for economy, wickets_per_match, overs_per_match
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
    
    # Last 5 bowling matches (excluding DNB) for average and strike_rate
    last5_bowling_df = player_df[player_df['date'].dt.year == int(season)]
    last5_bowling_df = get_last_5_bowling_matches(last5_bowling_df)
    
    # Check if fewer than 5 bowling matches in current season
    if len(last5_bowling_df['match_id'].unique()) < 5:
        # Get bowling matches from previous seasons
        additional_bowling_df = player_df[player_df['date'].dt.year < int(season)]
        additional_bowling_df = get_last_5_bowling_matches(additional_bowling_df)
        
        # Combine current and previous seasons bowling matches
        last5_bowling_df = pd.concat([last5_bowling_df, additional_bowling_df]).drop_duplicates(subset='match_id').head(5)

    # Calculate stats for regular and bowling-only last 5 matches
    last5_stats_regular = calculate_stats(last5_df)
    last5_stats_bowling = calculate_stats(last5_bowling_df)

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
    
    # Add career stats first
    for key, value in career_stats.items():
        result[f"career_{key}"] = value
    
    # Add last5 stats next (after career stats)
    # For average and strike_rate, use the bowling-only stats
    result['last5_average'] = last5_stats_bowling['average']
    result['last5_strike_rate'] = last5_stats_bowling['strike_rate']
    
    # For other metrics, use the regular last5 stats
    result['last5_economy'] = last5_stats_regular['economy']
    result['last5_wickets_per_match'] = last5_stats_regular['wickets_per_match']
    result['last5_overs_per_match'] = last5_stats_regular['overs_per_match']
    
    # Then add innings, venue, and season stats
    for prefix, stats in zip(['innings', 'venue', 'season'], 
                           [innings_stats, venue_stats, season_stats]):
        for key, value in stats.items():
            result[f"{prefix}_{key}"] = value
    
    return result

# ---------------- BOWLING GENERATOR FUNCTION ----------------
def bowling_test_gen(match_number):
    """
    Process bowling statistics for a specific match number.
    
    Args:
        match_number: The match number to process
        
    Returns:
        None. Writes the processed data to an output CSV file.
    """
    try:
        # Base directories
        base_app_dir = "D:\\Daily\\FIFS_Git\\FIFS_IPL"
        
        # Input and output directories with proper path formatting
        today_match_dir = os.path.join(base_app_dir, "Today_Match_Details")
        output_dir = os.path.join(base_app_dir, "test_data_output")
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            print(f"📁 Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)
        
        # Construct input and output file paths
        input_csv_path = os.path.join(today_match_dir, f"match_{match_number}.csv")
        output_csv_path = os.path.join(output_dir, f"output_bowl_{match_number}.csv")
        
        # Google Sheet URL for bowling data
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1-RxTFF7yXo8iB7Dl6JxdHQmub7Wr21aZZ2f_k18gwiU/edit?usp=sharing"
        
        # Load Google Sheet
        print(f"⏳ Loading Google Sheet data...")
        sheet_df = load_google_sheet(SHEET_URL)
        
        # Ensure numeric columns are parsed properly
        for col in ['runs', 'balls', 'overs', 'wickets']:
            sheet_df[col] = pd.to_numeric(sheet_df[col], errors='coerce').fillna(0)
        sheet_df['overs'] = sheet_df['overs'].astype(float)
        sheet_df['wickets'] = sheet_df['wickets'].astype(int)
        sheet_df['key_cricinfo'] = pd.to_numeric(sheet_df['key_cricinfo'], errors='coerce').fillna(0).astype(int)
        
        # Check if input file exists
        if not os.path.exists(input_csv_path):
            print(f"❌ Input file not found: {input_csv_path}")
            return False
            
        # Read input CSV
        print(f"⏳ Reading match data from: {input_csv_path}")
        input_df = pd.read_csv(input_csv_path)

        # Add year to dates in the 'Date' column and parse them
        try:
            input_df['Date'] = input_df['Date'] + ", 2025"  # Append the year
            input_df['Date'] = pd.to_datetime(input_df['Date'], format="%d %b, %Y", errors='coerce')
        except Exception as e:
            print(f"Error parsing Date column: {e}")
            sys.exit(1)

        # Drop rows with invalid or missing dates
        if input_df['Date'].isnull().any():
            print("⚠️ Warning: Some rows have invalid dates and will be dropped.")
            input_df = input_df.dropna(subset=['Date'])
        
        # Convert Cricinfo ID column to integer type
        input_df['Cricinfo ID'] = pd.to_numeric(input_df['Cricinfo ID'], errors='coerce').fillna(0).astype(int)
        
        print(f"🔄 Processing bowling stats for match #{match_number}...")
        output_rows = []
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
            result_row = process_player_row(player_input, sheet_df)
            output_rows.append(result_row)
        
        # Create output DataFrame and save to CSV
        output_df = pd.DataFrame(output_rows)
        output_df.to_csv(output_csv_path, index=False)
        print(f"✅ Bowling stats saved to: {output_csv_path}")
        return True
    
    except Exception as e:
        print(f"❌ Error processing match #{match_number}: {str(e)}")
        return False

# ---------------- MAIN ----------------
def main():
    if len(sys.argv) != 3:
        print("Usage: python analyze_players.py <input_csv_path> <output_csv_path>")
        sys.exit(1)

    input_csv_path = sys.argv[1]
    output_csv_path = sys.argv[2]

    # Put your sheet URL here
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1-RxTFF7yXo8iB7Dl6JxdHQmub7Wr21aZZ2f_k18gwiU/edit?usp=sharing"

    # Load Google Sheet
    sheet_df = load_google_sheet(SHEET_URL)

    # Ensure numeric columns are parsed properly
    for col in ['runs', 'balls', 'overs', 'wickets']:
        sheet_df[col] = pd.to_numeric(sheet_df[col], errors='coerce').fillna(0)
    sheet_df['overs'] = sheet_df['overs'].astype(float)
    sheet_df['wickets'] = sheet_df['wickets'].astype(int)
    sheet_df['key_cricinfo'] = pd.to_numeric(sheet_df['key_cricinfo'], errors='coerce').fillna(0).astype(int)

    # Print out the Google Sheet data for debugging
    print("Google Sheet data:")
    print(sheet_df[['key_cricinfo']].head())

    # Read input CSV
    input_df = pd.read_csv(input_csv_path)

    # Add year to dates in the 'Date' column and parse them
    try:
        input_df['Date'] = input_df['Date'] + ", 2025"  # Append the year
        input_df['Date'] = pd.to_datetime(input_df['Date'], format="%d %b, %Y", errors='coerce')
    except Exception as e:
        print(f"Error parsing Date column: {e}")
        sys.exit(1)

    # Drop rows with invalid or missing dates
    if input_df['Date'].isnull().any():
        print("⚠️ Warning: Some rows have invalid dates and will be dropped.")
        input_df = input_df.dropna(subset=['Date'])

    # Convert Cricinfo ID column to integer type
    input_df['Cricinfo ID'] = pd.to_numeric(input_df['Cricinfo ID'], errors='coerce').fillna(0).astype(int)

    # Print out the input data for debugging
    print("Input CSV data:")
    print(input_df[['Cricinfo ID']].head())

    output_rows = []
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
        result_row = process_player_row(player_input, sheet_df)
        output_rows.append(result_row)

    output_df = pd.DataFrame(output_rows)

    file_exists = os.path.exists(output_csv_path)
    output_df.to_csv(output_csv_path, index=False, mode='a' if file_exists else 'w', header=not file_exists)
    print("✅ Player stats updated in:", output_csv_path)

if __name__ == "__main__":
    main()