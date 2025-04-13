import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import sys
from datetime import datetime
import json
import pickle
import kagglehub  
import match_scraper
import batsman_data_generation as batsman_gen
import bowler_data_generation as bowler_gen
from pycaret.regression import load_model, predict_model
from sklearn.preprocessing import LabelEncoder
import pulp

def optimize_team(match_number, squad_data_path=r"D:\App\FIFS_IPL\data\register_data\squadData_ipl25.csv"):
    """
    Optimize fantasy cricket team selection based on merged fantasy points.
    
    Args:
        match_number: Match number to identify which merged file to use
        squad_data_path: Path to the squad data CSV containing player credits, roles, and teams
    """
    # Define file paths
    fp_file = fr"D:\App\FIFS_IPL\fp_predictor_merged\predicted_merged_{match_number}.csv"
    output_dir = r"D:\App\FIFS_IPL\team_selection"
    output_file = os.path.join(output_dir, f"team_{match_number}.csv")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    print(f"Starting team optimization for match {match_number}")
    
    try:
        # Read the merged fantasy points CSV
        print(f"Reading fantasy points from {fp_file}")
        fp_df = pd.read_csv(fp_file)
        
        # Read the squad data to get credits, roles, and teams
        print(f"Reading squad data from {squad_data_path}")
        squad_df = pd.read_csv(squad_data_path)
        
        # Convert player ID to string in fp_df to match with key_cricinfo in squad_df
        fp_df['player id'] = fp_df['player id'].astype(str)
        squad_df['key_cricinfo'] = squad_df['key_cricinfo'].astype(str)
        
        # Merge fantasy points with squad data
        print("Merging fantasy points with player information")
        df = pd.merge(
            fp_df,
            squad_df[['key_cricinfo', 'dream11_name', 'credits', 'role', 'team']],
            left_on='player id',
            right_on='key_cricinfo',
            how='inner'
        )
        
        # Check if we have enough players after merging
        if len(df) < 22:  # Need at least 22 players (11 per team) for meaningful selection
            print(f"WARNING: Only {len(df)} players found after merging. May not be enough for optimal team selection.")
        
        # Rename columns to match optimizer's expected format
        df = df.rename(columns={
            'dream11_name': 'player_name',
            'role': 'player_role',
            'team': 'player_team',
            'final_fp': 'final_fp'
        })
        
        # Reset index for PuLP variable creation
        df.reset_index(drop=True, inplace=True)
        
        print(f"Working with {len(df)} players from {df['player_team'].nunique()} teams")
        
        # Create the optimization problem (maximization)
        prob = pulp.LpProblem("Team_Selection", pulp.LpMaximize)
        
        # Create a binary decision variable for each player (1 if selected, 0 otherwise)
        players = df.index
        x = pulp.LpVariable.dicts("select", players, cat="Binary")
        
        # Objective: maximize the total final_fp of the selected players
        prob += pulp.lpSum([df.loc[i, "final_fp"] * x[i] for i in players]), "TotalFinalFP"
        
        # Constraint: exactly 11 players are selected
        prob += pulp.lpSum([x[i] for i in players]) == 11, "TotalPlayers"
        
        # Constraint: total credits must not exceed 100
        prob += pulp.lpSum([df.loc[i, "credits"] * x[i] for i in players]) <= 100, "TotalCredits"
        
        # Team Constraint: Choose between 2-9 players from each team
        teams = df["player_team"].unique()
        if len(teams) < 2:
            print("Warning: Less than two teams found in the data.")
            team_A = teams[0]
        else:
            team_A = teams[0]  # Choose the first team as Team A
            print(f"Team A selected as: {team_A}")
            
        team_A_indices = df[df["player_team"] == team_A].index
        prob += pulp.lpSum([x[i] for i in team_A_indices]) >= 2, "TeamA_Min"
        prob += pulp.lpSum([x[i] for i in team_A_indices]) <= 9, "TeamA_Max"
        
        # Role constraints: at least one player for each role WK, BAT, BOWL, ALL
        for role in ["WK", "BAT", "BOWL", "ALL"]:
            role_indices = df[df["player_role"] == role].index
            if len(role_indices) > 0:
                prob += pulp.lpSum([x[i] for i in role_indices]) >= 1, f"Min_{role}"
            else:
                print(f"Warning: No players found with role {role}")
        
        # Additional role constraints common in fantasy cricket
        # At least 3 batsmen
        bat_indices = df[df["player_role"] == "BAT"].index
        if len(bat_indices) >= 3:
            prob += pulp.lpSum([x[i] for i in bat_indices]) >= 3, "Min_3_BAT"
        
        # At least 3 bowlers
        bowl_indices = df[df["player_role"] == "BOWL"].index
        if len(bowl_indices) >= 3:
            prob += pulp.lpSum([x[i] for i in bowl_indices]) >= 3, "Min_3_BOWL"
        
        # At most 4 wicket-keepers
        wk_indices = df[df["player_role"] == "WK"].index
        if len(wk_indices) > 0:
            prob += pulp.lpSum([x[i] for i in wk_indices]) <= 4, "Max_4_WK"
        
        # Solve the optimization problem
        print("Solving optimization problem...")
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        print("Status:", pulp.LpStatus[prob.status])
        if pulp.LpStatus[prob.status] != "Optimal":
            print("No optimal solution found!")
            return
        
        # Extract selected players
        selected_indices = [i for i in players if pulp.value(x[i]) == 1]
        selected_df = df.loc[selected_indices].copy()
        
        # Sort selected players by final_fp in descending order
        selected_df.sort_values("final_fp", ascending=False, inplace=True)
        
        # Assign C/VC: highest final_fp gets "C", second highest gets "VC", others get "NA"
        selected_df["C/VC"] = "NA"
        if len(selected_df) >= 1:
            selected_df.iloc[0, selected_df.columns.get_loc("C/VC")] = "C"
        if len(selected_df) >= 2:
            selected_df.iloc[1, selected_df.columns.get_loc("C/VC")] = "VC"
        
        # Prepare final output: columns: Player Name, Team, Role, Credits, FP, C/VC
        output_df = selected_df[["player_name", "player_team", "player_role", "credits", "final_fp", "C/VC"]].copy()
        output_df = output_df.rename(columns={
            "player_name": "Player Name", 
            "player_team": "Team", 
            "player_role": "Role", 
            "credits": "Credits", 
            "final_fp": "Fantasy Points"
        })
        
        # Calculate total credits and expected fantasy points
        total_credits = output_df["Credits"].sum()
        captain_fp = output_df.loc[output_df["C/VC"] == "C", "Fantasy Points"].values[0] * 2
        vc_fp = output_df.loc[output_df["C/VC"] == "VC", "Fantasy Points"].values[0] * 1.5
        regular_fp = output_df.loc[output_df["C/VC"] == "NA", "Fantasy Points"].sum()
        total_expected_fp = captain_fp + vc_fp + regular_fp
        
        # Save the output CSV
        output_df.to_csv(output_file, index=False)
        print(f"Optimized team saved to {output_file}")
        print(f"Team summary:")
        print(f"  Total players: {len(output_df)}")
        print(f"  Total credits used: {total_credits}")
        print(f"  Expected fantasy points: {total_expected_fp:.2f}")
        print(f"  Team composition:")
        role_counts = output_df["Role"].value_counts()
        for role, count in role_counts.items():
            print(f"    {role}: {count}")
        team_counts = output_df["Team"].value_counts()
        for team, count in team_counts.items():
            print(f"    {team}: {count}")
        
    except FileNotFoundError as e:
        print(f"ERROR: File not found - {e}")
    except Exception as e:
        print(f"ERROR: Failed to optimize team: {str(e)}")
        import traceback
        traceback.print_exc()
# ---------------- CONFIG ----------------
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Sheet configurations
BATTING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1dumS1w_IQ7pv448tm-RKVqAQTEgOMKw59wf914qLHs0/edit?usp=sharingt"
BOWLING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-RxTFF7yXo8iB7Dl6JxdHQmub7Wr21aZZ2f_k18gwiU/edit?usp=sharing"
SQUAD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CeJ3u_c7YoAKBENOhpzNjUCTglT5m3vivXbGRGqBFvY/edit?gid=0#gid=0"

BATTING_SHEET_NAME = "Sheet1"
BOWLING_SHEET_NAME = "Sheet1"
SQUAD_SHEET_NAME = "Sheet1"

# ---------------- HELPER FUNCTIONS ----------------
def get_service_account_creds():
    """Get Google service account credentials from environment variables"""
    load_dotenv(dotenv_path="cricket-ipl-api/.env")

    private_key = os.getenv('GOOGLE_PRIVATE_KEY', "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCfMj6CXlqkKilX\nywe8SocjseYIqRQ7OpnAQB7Ly/DPbQFF++0Bx+rk7xCg3RAApsxOG6OhsLTmUAdK\nlwn3Un+4WZC/W4A7fkl3dbxubiZMUocCXiIqpF4NEobbms+xYtiywWlyLIKVBXz3\npWPa3iODhKu8BmcV2YBg1r4dyJjdKmOXzqy7a1eNNm8//FlDa67oqSCEcpcGSDlQ\nm8ZL6kyHn9Bnu1qVDFxyVjlfFy70G6A7zYOx1lcgTl9W7SJPWXYF+s7kGuZY0lef\n2GPj7q6qlCFd6Q1qg0tb6shVtiKAYl8rYWn8aFE+TyAFR0UPP6IyAtJW9zmKKrQv\nBKdVO5CZAgMBAAECggEASj7fomOo+GllcLmS+QD1N/OPKjjY46q37E67TibmP4dC\nEcalya/YYD8SzUNsZDFmlYMUdKN6KvPmAqagkkVapbq35FcjXhvO3bT+Va5vlCbl\nKniGjMatyoD6fk8cUEmecPf9Wq9hk2jE2Ka9BGWXwI3OnlmKGEmhMwjUEAXvLS4M\nZuQ7XJephacqYguYxOfiZDmMa8BEnPo4kmIQW6oQrUi8L4kAdxI7nUBQM8O4gN0y\nLvrHJAWuL8O7C2vU9+qRWjUCM28fB68YhdEznTb+4Nc2AYXazOa+oHh6y5dSARy8\nHmYBtGlFoNEfxteyRcZNCUF5hd2b+PoKEffPO6NzdQKBgQDRmK/svjci6pqox6s5\n1Bp8ALs+mzEypRJT9QVIE7JYIzeDiZHnh6NQGRqAkEyjlt+V276VLwAiBLuIhnKF\n9fYW7xeh8+E9Wa40E1mvKyPFljD3zq6kFHLDeK8pwFRCtZCsCfDD51EvUQGyrhP2\naZ1zadVeaM7oB1nbbLGdE0wdMwKBgQDCcQXbBucVCjEroO4oiO7CDWTNVpOHS6c0\naPENWBFBreQ0cTxaZwPU8sZ32rogQJFA3610nUetoPbHPizU64eG0RUKV+3bbX82\nnMViS01AK6D+BFqHdxoKgvaCnehfcw2xMdrq2/gRLvPR7oj4yOxoqTeSik11Bug9\nRkZD/sHjAwKBgQCmRxOKJX1oXeZEb+MPBY3dQldJ26S0IPDhWkjOXZHnCklIOSNf\nIuQU71VvGQsz3MWUBbi0cY0Rb9+297JzRCXvG88L1IakPTlOZuuHZBoE7pn6fiVe\nVjqViHCuFr7CDXiwg1JWmHR3rTRDpIaBvlgC77suIsfCm9JVmW1ux5hisQKBgEAa\nTtnkrq5LC+bcSWfnrP8gt0jS8BQ8psUqi73geN/0WjXH1yPerm64EyJUY+RaJQkE\nNQUrDQR6+qC5KMKRW77gk1Uzo+Ehej0g9hnvxWoQeCUGfmoGo/kvL+Hj+UXugmcW\njpu7JU9U8WEWiOWsJ/RhRUb0fZDFVC9PSb8E8BrNAoGARf8Qmhemf55NFTRsFRdO\nKhDIRUdfmSZGkSjvdgZzMmRwYXiosJJpPUEB5VoDbdxV8mnJdlom4mM/9JuLhhJ8\ni5aOaHBlmXAYIC8Svhja4HVFH9iLrqG772BGH0xzowUPYzYITJedK7iPGptMEAk8\n0nP0fdL2zqDJRn41LTuBqCY=\n-----END PRIVATE KEY-----\n")
    client_email = os.getenv('GOOGLE_CLIENT_EMAIL', "ipl-933@ipl-fifs.iam.gserviceaccount.com")
    project_id = os.getenv('GOOGLE_PROJECT_ID', "1dumS1w_IQ7pv448tm-RKVqAQTEgOMKw59wf914qLHs0")

    service_account_info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": os.getenv('GOOGLE_PRIVATE_KEY_ID', "dummy_key_id"),
        "private_key": private_key,
        "client_email": client_email,
        "client_id": os.getenv('GOOGLE_CLIENT_ID', "dummy_client_id"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}"
    }
    
    return Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

def load_google_sheet(sheet_url, sheet_name):
    """General function to load a Google Sheet"""
    try:
        creds = get_service_account_creds()
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error loading sheet ({sheet_name}): {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error

# ---------------- REQUESTED DATA LOADING METHODS ----------------
def load_bat_mbm():
    """
    Load batting data from Google Sheet
    
    Returns:
        DataFrame containing batting match-by-match data
    """
    df = load_google_sheet(BATTING_SHEET_URL, BATTING_SHEET_NAME)
    return df

def load_bowl_mbm():
    """
    Load bowling data from Google Sheet
    
    Returns:
        DataFrame containing bowling match-by-match data
    """
    df = load_google_sheet(BOWLING_SHEET_URL, BOWLING_SHEET_NAME)
    return df

def load_squadData25():
    """
    Load squad data from Google Sheet
    
    Returns:
        DataFrame containing squad data for 2025
    """
    df = load_google_sheet(SQUAD_SHEET_URL, SQUAD_SHEET_NAME)
    return df

def match_scrapping(match_number=None):
    """
    Function to execute match scraping functionality from match_scrapper.py
    
    This method imports and calls the run_match_scrapper function from the 
    match_scrapper module to scrape cricket match data.

    """
    #match_number = match_number or input("Enter match number to scrape (or 'all' for all matches): ").strip()
    try:
        print("Starting match scrapper...")
        
        # Call the run_match_scrapper function with optional match_number
        result = match_scraper.run_match_scrapper()
        # Print summary
        if result['success']:
            print(f"✅ Successfully scraped match data!")
            print(f"📅 Match date: {result['match_date']}")
            print(f"📊 Data saved to: {result['csv_path']}")
            print(f"👥 Players found: {len(result['match_data'])}")
        else:
            #scope for error handling if scrapper fails any time later
            print(f"❌ Failed to scrape match data: {result['message']}")
        
        return result
    except ImportError:
        print("❌ Error: Could not import run_match_scrapper from match_scrapper module.")
        print("   Make sure match_scrapper.py is in the same directory as main.py.")
        return {"success": False, "message": "Import error with match_scrapper module"}
    
    except Exception as e:
        print(f"❌ Error while running match scrapper: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}
    
def bat_test_gen(match_id):
    output_path = batsman_gen.batting_test_gen(match_id)
    return output_path

def bowl_test_gen(match_id):
    output_path = bowler_gen.bowling_test_gen(match_id)
    return output_path
    

def predict_fantasy_points(batting_data, bowling_data, match_number):
    """
    Predict fantasy points using PyCaret models for batting and bowling data.
    """
    print(f"Starting prediction process for match {match_number}")
    
    # Create fp_predictor folder if it doesn't exist
    fp_predictor_dir = r"D:\App\FIFS_IPL\fp_predictor"
    if not os.path.exists(fp_predictor_dir):
        os.makedirs(fp_predictor_dir)
        print(f"Created directory: {fp_predictor_dir}")
    else:
        print(f"Directory already exists: {fp_predictor_dir}")
    
    # Process batting data
    try:
        # Check if batting_data is a file path or DataFrame
        if isinstance(batting_data, str):
            print(f"Reading batting data from file: {batting_data}")
            batting_df = pd.read_csv(batting_data)
        else:
            print("Using provided batting DataFrame")
            batting_df = batting_data.copy()
            
        print(f"Batting data shape: {batting_df.shape[0]} rows, {batting_df.shape[1]} columns")
        print(f"Original column names: {batting_df.columns.tolist()}")
        
        # Store player IDs for later use
        player_ids = batting_df['player_id'].copy()
        
        # Keep a copy of the venue if it exists
        if 'venue' in batting_df.columns:
            venue_values = batting_df['venue'].copy()
        else:
            venue_values = None

        # Keep a copy of the 'season' column if it exists
        if 'season' in batting_df.columns:
            season_values = batting_df['season'].copy()
        else:
            season_values = None
        
        # Create column mapping for batting data
        batting_column_mapping = {
            'player_id': 'batter_id',
            'innings': 'inns',
            'career_batting_average': 'career_avg',
            'career_strike_rate': 'career_sr',
            'career_boundaries_per_match': 'career_bpm',
            'career_runs_per_match': 'career_rpm',
            'career_balls_faced_per_match': 'career_bfpm',
            'last5_batting_average': 'last5_avg',
            'last5_strike_rate': 'last5_sr',
            'last5_boundaries_per_match': 'last5_bpm',
            'last5_runs_per_match': 'last5_rpm',
            'last5_balls_faced_per_match': 'last5_bfpm',
            'innings_batting_average': 'inns_avg',
            'innings_strike_rate': 'inns_sr',
            'innings_boundaries_per_match': 'inns_bpm',
            'innings_runs_per_match': 'inns_rpm',
            'innings_balls_faced_per_match': 'inns_bfpm',
            'venue_batting_average': 'ven_avg',
            'venue_strike_rate': 'ven_sr',
            'venue_boundaries_per_match': 'ven_bpm',
            'venue_runs_per_match': 'ven_rpm',
            'venue_balls_faced_per_match': 'ven_bfpm',
            'season_batting_average': 'ssn_avg',
            'season_strike_rate': 'ssn_sr',
            'season_boundaries_per_match': 'ssn_bpm',
            'season_runs_per_match': 'ssn_rpm',
            'season_balls_faced_per_match': 'ssn_bfpm'
        }
        
        # Rename columns to match what the model expects
        columns_to_rename = {col: mapping for col, mapping in batting_column_mapping.items() 
                           if col in batting_df.columns}
        batting_df = batting_df.rename(columns=columns_to_rename)
        
        # Label encode 'bat_team' and 'bowl_team'
        categorical_columns = ['bat_team', 'bowl_team']
        label_encoder = LabelEncoder()
        
        for col in categorical_columns:
            if col in batting_df.columns:
                print(f"Label encoding column: {col}")
                batting_df[col] = label_encoder.fit_transform(batting_df[col])
                print(f"Unique values in {col} mapped to: {dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))}")
        
        # Remove non-numeric columns that could cause issues (but keep venue)
        columns_to_drop = ['player_name', 'cutoff_date']
        for col in columns_to_drop:
            if col in batting_df.columns:
                batting_df = batting_df.drop(col, axis=1)
                print(f"Dropped column: {col}")
        
        # Add required columns that were used during training
        required_columns = ['career_debut', 'season_debut', 'venue_debut', 'innings_debut']
        for col in required_columns:
            print(f"Adding required column: {col}")
            batting_df[col] = 0  # Set default value to 0
        
        # Re-add 'season' column if it was dropped
        if 'season' not in batting_df.columns and season_values is not None:
            batting_df['season'] = season_values
            print(f"Re-added column: season")
        elif 'season' not in batting_df.columns:
            batting_df['season'] = 0  # Add with default value
            print(f"Added missing column: season")
        
        # Re-add 'venue' column if it was somehow dropped
        if 'venue' not in batting_df.columns and venue_values is not None:
            batting_df['venue'] = venue_values
            print(f"Re-added column: venue")
        
        # Ensure all remaining columns are numeric
        for col in batting_df.columns:
            if batting_df[col].dtype == 'object':
                print(f"Converting column {col} to numeric")
                batting_df[col] = pd.to_numeric(batting_df[col], errors='coerce')
        
        # Fill missing values with 0
        batting_df = batting_df.fillna(0)
        
        print(f"Processed batting data shape: {batting_df.shape[0]} rows, {batting_df.shape[1]} columns")
        print(f"Processed column names: {batting_df.columns.tolist()}")
        
        # Load model - REMOVED .pkl extension
        print("Loading batting model...")
        batting_model = load_model("D:/App/FIFS_IPL/models/batting_model_flag")
        print("Batting model loaded successfully")
        
        # Make predictions
        print("Making batting predictions...")
        batting_predictions = predict_model(batting_model, data=batting_df)
        print(f"Predictions completed. Result shape: {batting_predictions.shape[0]} rows, {batting_predictions.shape[1]} columns")
        print(f"Prediction columns: {batting_predictions.columns.tolist()}")
        
        # Find prediction column (name can vary by PyCaret version)
        pred_cols = [col for col in batting_predictions.columns 
                   if col.startswith('prediction_') or col == 'Label' or col == 'Score']
        
        print(f"Identified prediction columns: {pred_cols}")
        
        if pred_cols:
            # Create result dataframe with required columns
            batting_results = pd.DataFrame()
            
            # Add player id (using stored original player IDs)
            batting_results['player id'] = player_ids
            print("Added player IDs from original data")
            
            # Add prediction
            batting_results['generated_fp'] = batting_predictions[pred_cols[0]]
            print(f"Added generated_fp column from {pred_cols[0]}")
            
            # Save to CSV
            batting_output_path = os.path.join(fp_predictor_dir, f"predicted_bat_{match_number}.csv")
            print(f"Saving batting predictions to {batting_output_path}")
            
            # Print a preview of what we're saving
            print("Preview of batting results:")
            print(batting_results.head())
            
            batting_results.to_csv(batting_output_path, index=False)
            
            # Verify file was created
            if os.path.exists(batting_output_path):
                print(f"SUCCESS: Batting predictions saved to {batting_output_path}")
            else:
                print(f"ERROR: Failed to create {batting_output_path}")
        else:
            print("ERROR: Could not identify prediction column in batting results")
            
    except Exception as e:
        print(f"ERROR processing batting data: {str(e)}")
        import traceback
        traceback.print_exc(file=sys.stdout)
    
    # Process bowling data with similar approach
    try:
        # Check if bowling_data is a file path or DataFrame
        if isinstance(bowling_data, str):
            print(f"Reading bowling data from file: {bowling_data}")
            bowling_df = pd.read_csv(bowling_data)
        else:
            print("Using provided bowling DataFrame")
            bowling_df = bowling_data.copy()
            
        # Store original player IDs
        player_ids = bowling_df['player_id'].copy()
        
        # Keep a copy of the venue if it exists
        if 'venue' in bowling_df.columns:
            venue_values = bowling_df['venue'].copy()
        else:
            venue_values = None

        # Keep a copy of the 'season' column if it exists
        if 'season' in bowling_df.columns:
            season_values = bowling_df['season'].copy()
        else:
            season_values = None
        
        print(f"Bowling data shape: {bowling_df.shape[0]} rows, {bowling_df.shape[1]} columns")
        print(f"Original column names: {bowling_df.columns.tolist()}")
        
        # Create column mapping for bowling data based on your provided column names
        bowling_column_mapping = {
            'player_id': 'bowler_id',
            'innings': 'inns',
            'career_average': 'career_avg',
            'career_strike_rate': 'career_sr',
            'career_economy': 'career_eco',
            'career_wickets_per_match': 'career_wpm',
            'career_overs_per_match': 'career_opm',
            'last5_average': 'last5_avg',
            'last5_strike_rate': 'last5_sr',
            'last5_economy': 'last5_eco',
            'last5_wickets_per_match': 'last5_wpm',
            'last5_overs_per_match': 'last5_opm',
            'innings_average': 'inns_avg',
            'innings_strike_rate': 'inns_sr',
            'innings_economy': 'inns_eco',
            'innings_wickets_per_match': 'inns_wpm',
            'innings_overs_per_match': 'inns_opm',
            'venue_average': 'venue_avg',
            'venue_strike_rate': 'venue_sr',
            'venue_economy': 'venue_eco',
            'venue_wickets_per_match': 'venue_wpm',
            'venue_overs_per_match': 'venue_opm',
            'season_average': 'ssn_avg',
            'season_strike_rate': 'ssn_sr',
            'season_economy': 'ssn_eco',
            'season_wickets_per_match': 'ssn_wpm',
            'season_overs_per_match': 'ssn_opm'
        }
        
        # Rename columns to match what the model expects
        columns_to_rename = {col: mapping for col, mapping in bowling_column_mapping.items() 
                           if col in bowling_df.columns}
        bowling_df = bowling_df.rename(columns=columns_to_rename)
        
        # Label encode 'bat_team' and 'bowl_team'
        categorical_columns = ['bat_team', 'bowl_team']
        label_encoder = LabelEncoder()
        
        for col in categorical_columns:
            if col in bowling_df.columns:
                print(f"Label encoding column: {col}")
                bowling_df[col] = label_encoder.fit_transform(bowling_df[col])
                print(f"Unique values in {col} mapped to: {dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))}")
        
        # Remove non-numeric columns that could cause issues (but keep venue)
        columns_to_drop = ['player_name', 'cutoff_date']
        for col in columns_to_drop:
            if col in bowling_df.columns:
                bowling_df = bowling_df.drop(col, axis=1)
                print(f"Dropped column: {col}")
        
        # Add required columns that were used during training
        required_columns = [
            'career_debut', 'season_debut', 'venue_debut', 'innings_debut', 
        ]
        


        for col in required_columns:
            if col not in bowling_df.columns:
                print(f"Adding required column: {col}")
                bowling_df[col] = 0  # Set default value to 0
        
        # Re-add 'season' column if it was dropped
        if 'season' not in bowling_df.columns and season_values is not None:
            bowling_df['season'] = season_values
            print(f"Re-added column: season")
        elif 'season' not in bowling_df.columns:
            bowling_df['season'] = 0  # Add with default value
            print(f"Added missing column: season")
        
        # Re-add 'venue' column if it was somehow dropped
        if 'venue' not in bowling_df.columns and venue_values is not None:
            bowling_df['venue'] = venue_values
            print(f"Re-added column: venue")
        
        # Ensure all remaining columns are numeric
        for col in bowling_df.columns:
            if bowling_df[col].dtype == 'object':
                print(f"Converting column {col} to numeric")
                bowling_df[col] = pd.to_numeric(bowling_df[col], errors='coerce')
        
        # Fill missing values with 0
        bowling_df = bowling_df.fillna(0)
        
        print(f"Processed bowling data shape: {bowling_df.shape[0]} rows, {bowling_df.shape[1]} columns")
        print(f"Processed column names: {bowling_df.columns.tolist()}")
        
        # Load model
        print("Loading bowling model...")
        bowling_model = load_model(r"D:/App/FIFS_IPL/models/bowling_model_flag")
        print("Bowling model loaded successfully")
        
        # Make predictions
        print("Making bowling predictions...")
        bowling_predictions = predict_model(bowling_model, data=bowling_df)
        print(f"Predictions completed. Result shape: {bowling_predictions.shape[0]} rows, {bowling_predictions.shape[1]} columns")
        
        # Find prediction column
        pred_cols = [col for col in bowling_predictions.columns 
                   if col.startswith('prediction_') or col == 'Label' or col == 'Score']
        
        if pred_cols:
            # Create result dataframe with required columns
            bowling_results = pd.DataFrame()
            
            # Add player id (using stored original player IDs)
            bowling_results['player id'] = player_ids
            print("Added player IDs from original data")
            
            # Add prediction
            bowling_results['generated_fp'] = bowling_predictions[pred_cols[0]]
            print(f"Added generated_fp column from {pred_cols[0]}")
            
            # Save to CSV
            bowling_output_path = os.path.join(fp_predictor_dir, f"predicted_bowl_{match_number}.csv")
            bowling_results.to_csv(bowling_output_path, index=False)
            print(f"SUCCESS: Bowling predictions saved to {bowling_output_path}")
            
        else:
            print("ERROR: Could not identify prediction column in bowling results")
            
    except Exception as e:
        print(f"ERROR processing bowling data: {str(e)}")
        import traceback
        traceback.print_exc(file=sys.stdout)

    print("Prediction process completed.")


def merge_fantasy_predictions(match_number):
    """
    Merge batting and bowling fantasy point predictions for a specific match.
    
    This function:
    1. Reads the batting and bowling prediction CSVs for a given match number
    2. Merges them based on player_id
    3. Creates a final_fp column that sums the generated_fp from both sources
    4. Maps player names from squadData_ipl25.csv using key_cricinfo as player_id
    5. Saves the merged result to a new CSV in fp_predictor_merged folder
    """
    
    # Define directories
    source_dir = r"D:\App\FIFS_IPL\fp_predictor"
    target_dir = r"D:\App\FIFS_IPL\fp_predictor_merged"
    squad_data_path=r"D:\App\FIFS_IPL\data\register_data\squadData_ipl25.csv"
    
    # Create target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")
    else:
        print(f"Target directory already exists: {target_dir}")
    
    # Define file paths
    batting_file = os.path.join(source_dir, f"predicted_bat_{match_number}.csv")
    bowling_file = os.path.join(source_dir, f"predicted_bowl_{match_number}.csv")
    output_file = os.path.join(target_dir, f"predicted_merged_{match_number}.csv")
    
    # Check if source files exist
    if not os.path.exists(batting_file):
        print(f"ERROR: Batting predictions file not found: {batting_file}")
        return
    
    if not os.path.exists(bowling_file):
        print(f"ERROR: Bowling predictions file not found: {bowling_file}")
        return
    
    try:
        # Read the CSV files
        print(f"Reading batting predictions from {batting_file}")
        batting_df = pd.read_csv(batting_file)
        
        print(f"Reading bowling predictions from {bowling_file}")
        bowling_df = pd.read_csv(bowling_file)
        
        # Read squad data file to get player names
        print(f"Reading squad data from {squad_data_path}")
        squad_df = pd.read_csv(squad_data_path)
        
        # Create a mapping from key_cricinfo (player_id) to dream11_name (player name)
        # Convert key_cricinfo to string to match the player_id datatype in prediction files
        squad_df['key_cricinfo'] = squad_df['key_cricinfo'].astype(str)
        player_name_map = dict(zip(squad_df['key_cricinfo'], squad_df['dream11_name']))
        
        print(f"Created player name mapping for {len(player_name_map)} players")
        
        # Check for expected columns
        if 'player id' not in batting_df.columns or 'generated_fp' not in batting_df.columns:
            print(f"ERROR: Batting file is missing required columns. Found: {batting_df.columns.tolist()}")
            return
            
        if 'player id' not in bowling_df.columns or 'generated_fp' not in bowling_df.columns:
            print(f"ERROR: Bowling file is missing required columns. Found: {bowling_df.columns.tolist()}")
            return
        
        # Create a merged dataframe
        print("Merging batting and bowling data")
        
        # Initialize the merged dataframe with all player IDs
        all_players = pd.concat([
            batting_df[['player id']],
            bowling_df[['player id']]
        ]).drop_duplicates()
        
        # Convert player id to string to match with key_cricinfo
        all_players['player id'] = all_players['player id'].astype(str)
        
        # Add player name column based on mapping
        all_players['player name'] = all_players['player id'].map(player_name_map)
        
        # For any players not found in the mapping, set name to "Unknown"
        all_players['player name'] = all_players['player name'].fillna("Unknown")
        
        # Rename columns for clarity in the merge
        batting_df = batting_df.rename(columns={'generated_fp': 'batting_fp'})
        bowling_df = bowling_df.rename(columns={'generated_fp': 'bowling_fp'})
        
        # Convert player id to string in batting and bowling dataframes
        batting_df['player id'] = batting_df['player id'].astype(str)
        bowling_df['player id'] = bowling_df['player id'].astype(str)
        
        # Merge batting data
        merged_df = pd.merge(
            all_players,
            batting_df[['player id', 'batting_fp']],
            on='player id',
            how='left'
        )
        
        # Merge bowling data
        merged_df = pd.merge(
            merged_df,
            bowling_df[['player id', 'bowling_fp']],
            on='player id',
            how='left'
        )
        
        # Fill NaN values with 0 (players who are only batters or only bowlers)
        merged_df['batting_fp'] = merged_df['batting_fp'].fillna(0)
        merged_df['bowling_fp'] = merged_df['bowling_fp'].fillna(0)
        
        # Calculate final fantasy points
        merged_df['final_fp'] = merged_df['batting_fp'] + merged_df['bowling_fp']
        
        # Reorder columns to have player name first, then id, then fantasy points
        merged_df = merged_df[['player name', 'player id', 'batting_fp', 'bowling_fp', 'final_fp']]
        
        # Save to CSV
        print(f"Saving merged predictions to {output_file}")
        merged_df.to_csv(output_file, index=False)
        
        # Print summary
        print(f"Successfully merged predictions for match {match_number}")
        print(f"Total players: {len(merged_df)}")
        print(f"Players with batting points: {(merged_df['batting_fp'] > 0).sum()}")
        print(f"Players with bowling points: {(merged_df['bowling_fp'] > 0).sum()}")
        print(f"Players with both batting and bowling points: {((merged_df['batting_fp'] > 0) & (merged_df['bowling_fp'] > 0)).sum()}")
        print(f"Players with mapped names: {(merged_df['player name'] != 'Unknown').sum()}")
        
    except Exception as e:
        print(f"ERROR: Failed to merge predictions: {str(e)}")
        import traceback
        traceback.print_exc()


import os
import pandas as pd
import pulp

def optimize_team(match_number):
    """
    Optimize fantasy cricket team selection based on merged fantasy points.
    
    Args:
        match_number: Match number to identify which merged file to use
        squad_data_path: Path to the squad data CSV containing player credits, roles, and teams
    """
    # Define file paths
    fp_file = fr"D:\App\FIFS_IPL\fp_predictor_merged\predicted_merged_{match_number}.csv"
    output_dir = r"D:\App\FIFS_IPL\team_selection"
    squad_data_path=r"D:\App\FIFS_IPL\data\register_data\squadData_ipl25.csv"
    output_file = os.path.join(output_dir, f"team_{match_number}.csv")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    print(f"Starting team optimization for match {match_number}")
    
    try:
        # Read the merged fantasy points CSV
        print(f"Reading fantasy points from {fp_file}")
        fp_df = pd.read_csv(fp_file)
        
        # Read the squad data to get credits, roles, and teams
        print(f"Reading squad data from {squad_data_path}")
        squad_df = pd.read_csv(squad_data_path)
        
        # Convert player ID to string in fp_df to match with key_cricinfo in squad_df
        fp_df['player id'] = fp_df['player id'].astype(str)
        squad_df['key_cricinfo'] = squad_df['key_cricinfo'].astype(str)
        
        # Merge fantasy points with squad data
        print("Merging fantasy points with player information")
        df = pd.merge(
            fp_df,
            squad_df[['key_cricinfo', 'dream11_name', 'credits', 'role', 'team']],
            left_on='player id',
            right_on='key_cricinfo',
            how='inner'
        )
        
        # Check if we have enough players after merging
        if len(df) < 22:  # Need at least 22 players (11 per team) for meaningful selection
            print(f"WARNING: Only {len(df)} players found after merging. May not be enough for optimal team selection.")
        
        # Rename columns to match optimizer's expected format
        df = df.rename(columns={
            'dream11_name': 'player_name',
            'role': 'player_role',
            'team': 'player_team',
            'final_fp': 'final_fp'
        })
        
        # Reset index for PuLP variable creation
        df.reset_index(drop=True, inplace=True)
        
        print(f"Working with {len(df)} players from {df['player_team'].nunique()} teams")
        
        # Create the optimization problem (maximization)
        prob = pulp.LpProblem("Team_Selection", pulp.LpMaximize)
        
        # Create a binary decision variable for each player (1 if selected, 0 otherwise)
        players = df.index
        x = pulp.LpVariable.dicts("select", players, cat="Binary")
        
        # Objective: maximize the total final_fp of the selected players
        prob += pulp.lpSum([df.loc[i, "final_fp"] * x[i] for i in players]), "TotalFinalFP"
        
        # Constraint: exactly 11 players are selected
        prob += pulp.lpSum([x[i] for i in players]) == 11, "TotalPlayers"
        
        # Constraint: total credits must not exceed 100
        prob += pulp.lpSum([df.loc[i, "credits"] * x[i] for i in players]) <= 100, "TotalCredits"
        
        # Team Constraint: Choose between 2-9 players from each team
        teams = df["player_team"].unique()
        if len(teams) < 2:
            print("Warning: Less than two teams found in the data.")
            team_A = teams[0]
        else:
            team_A = teams[0]  # Choose the first team as Team A
            print(f"Team A selected as: {team_A}")
            
        team_A_indices = df[df["player_team"] == team_A].index
        prob += pulp.lpSum([x[i] for i in team_A_indices]) >= 1, "TeamA_Min"
        prob += pulp.lpSum([x[i] for i in team_A_indices]) <= 10, "TeamA_Max"
        
        # Role constraints: at least one player for each role WK, BAT, BOWL, ALL
        for role in ["WK", "BAT", "BOWL", "ALL"]:
            role_indices = df[df["player_role"] == role].index
            if len(role_indices) > 0:
                prob += pulp.lpSum([x[i] for i in role_indices]) >= 1, f"Min_{role}"
            else:
                print(f"Warning: No players found with role {role}")
        
        # Solve the optimization problem
        print("Solving optimization problem...")
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        print("Status:", pulp.LpStatus[prob.status])
        if pulp.LpStatus[prob.status] != "Optimal":
            print("No optimal solution found!")
            return
        
        # Extract selected players
        selected_indices = [i for i in players if pulp.value(x[i]) == 1]
        selected_df = df.loc[selected_indices].copy()
        
        # Sort selected players by final_fp in descending order
        selected_df.sort_values("final_fp", ascending=False, inplace=True)
        
        # Assign C/VC: highest final_fp gets "captain", second highest gets "vice captain", others get "player"
        # Initialize all as "player" first
        selected_df["C/VC"] = "player"
        
        # Set captain and vice-captain
        if len(selected_df) >= 1:
            selected_df.iloc[0, selected_df.columns.get_loc("C/VC")] = "captain"
        if len(selected_df) >= 2:
            selected_df.iloc[1, selected_df.columns.get_loc("C/VC")] = "vice captain"
        
        # Prepare output: columns: Player Name, Role, Team, C/VC
        output_df = selected_df[["player_name", "player_role", "player_team", "C/VC"]].copy()
        output_df = output_df.rename(columns={
            "player_name": "Player Name", 
            "player_role": "Role",
            "player_team": "Team"
        })
        
        # Calculate total credits and expected fantasy points (for console output only)
        total_credits = selected_df["credits"].sum()
        captain_fp = selected_df.iloc[0]["final_fp"] * 2  # Captain gets 2x points
        vc_fp = selected_df.iloc[1]["final_fp"] * 1.5     # Vice Captain gets 1.5x points
        regular_fp = selected_df.iloc[2:]["final_fp"].sum()
        total_fp = captain_fp + vc_fp + regular_fp
        
        
        # Save the output CSV with 4 columns as requested
        output_df.to_csv(output_file, index=False)
        print(f"Optimized team saved to {output_file}")
        print(f"Team summary:")
        print(f"  Total players: {len(output_df)}")
        print(f"  Total credits used: {total_credits}")
        print(f"  Expected fantasy points: {total_fp:.2f}")
        print(f"  Captain: {output_df.iloc[0]['Player Name']} ({selected_df.iloc[0]['final_fp']:.2f} points)")
        print(f"  Vice Captain: {output_df.iloc[1]['Player Name']} ({selected_df.iloc[1]['final_fp']:.2f} points)")
        print(f"  Team composition:")
        role_counts = output_df["Role"].value_counts()
        for role, count in role_counts.items():
            print(f"    {role}: {count}")
        team_counts = output_df["Team"].value_counts()
        for team, count in team_counts.items():
            print(f"    {team}: {count}")

        print("\nSelected Team:")
        print(output_df)
        
    except FileNotFoundError as e:
        print(f"ERROR: File not found - {e}")
    except Exception as e:
        print(f"ERROR: Failed to optimize team: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__": 

    # Load all datasets
    batting_data = load_bat_mbm()
    bowling_data = load_bowl_mbm()
    squad_data = load_squadData25()

    # Display data heads
    print("\nBatting Data:")
    print(batting_data.shape)
    print("\nBowling Data:")
    print(bowling_data.shape)
    print("\nSquad Data:")
    print(squad_data.shape)

    #match_scrapping
    result=match_scrapping()
    match_number = result['match_number']

    #match stats calculations
    bat_test_gen(match_number)
    bowl_test_gen(match_number)

    
    batting_data_path = f"D:/App/FIFS_IPL/test_data_output/output_bat_{match_number}.csv"
    bowling_data_path = f"D:/App/FIFS_IPL/test_data_output/output_bowl_{match_number}.csv"
    #print(batting_data_path)
    predict_fantasy_points(batting_data_path, bowling_data_path, match_number)
    merge_fantasy_predictions(match_number)
    optimize_team(match_number)

