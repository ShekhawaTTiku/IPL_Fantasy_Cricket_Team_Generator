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


'''def load_batting_model(model_path=None):
    """
    Load the batting model from the specified path or download it if not provided.
    
    Args:
        model_path (str, optional): Path to the model file. If None, the model will be downloaded.
        
    Returns:
        The loaded model
    """
    # If path is not provided, download the model
    if model_path is None:
        model_path = kagglehub.model_download("avignyansarangi/batting.pkl/other/default")
    
    # Check if the path is a directory (kagglehub might return a directory)
    if os.path.isdir(model_path):
        # Look for .pkl files in the directory
        pkl_files = [f for f in os.listdir(model_path) if f.endswith('.pkl')]
        if not pkl_files:
            raise FileNotFoundError(f"No .pkl files found in {model_path}")
        # Use the first .pkl file found
        model_path = os.path.join(model_path, pkl_files[0])
    
    # Load and return the model
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    print(f"Model loaded successfully from {model_path}")
    return model


def load_bowling_model(model_path=None):
    """
    Load the bowling model from the specified path or download it if not provided.
    
    Args:
        model_path (str, optional): Path to the model file. If None, the model will be downloaded.
        
    Returns:
        The loaded model
    """
    # If path is not provided, download the model
    if model_path is None:
        model_path = kagglehub.model_download("avignyansarangi/bowling-model/other/default")
    
    # Check if the path is a directory (kagglehub might return a directory)
    if os.path.isdir(model_path):
        # Look for .pkl files in the directory
        pkl_files = [f for f in os.listdir(model_path) if f.endswith('.pkl')]
        if not pkl_files:
            raise FileNotFoundError(f"No .pkl files found in {model_path}")
        # Use the first .pkl file found
        model_path = os.path.join(model_path, pkl_files[0])
    
    # Load and return the model
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    print(f"Bowling model loaded successfully from {model_path}")
    return model

def prediction_fp(bat_test_path, bowl_test_path, batting_model, bowling_model, match_number):
    """
    Generate fantasy point predictions for batsmen and bowlers using PyCaret models.
    
    Args:
        bat_test_path (str): Path to batting test data CSV file
        bowl_test_path (str): Path to bowling test data CSV file
        batting_model: PyCaret trained model for batting FP prediction
        bowling_model: PyCaret trained model for bowling FP prediction
        match_number (str): Match number to use in output file names
    
    Returns:
        tuple: Paths to the generated prediction CSV files (batting_fp_path, bowling_fp_path)
    """
    import os
    import pandas as pd
    import numpy as np
    
    # Create output directory if it doesn't exist
    output_dir = "fp_prediction"
    os.makedirs(output_dir, exist_ok=True)
    
    # Define output file paths
    batting_fp_path = os.path.join(output_dir, f"match_{match_number}_bat_fp.csv")
    bowling_fp_path = os.path.join(output_dir, f"match_{match_number}_bowl_fp.csv")'''
    



import os
import sys
import pandas as pd
from pycaret.regression import load_model, predict_model

import os
import sys
import pandas as pd
from pycaret.regression import load_model, predict_model
from sklearn.preprocessing import LabelEncoder

import os
import sys
import pandas as pd
from pycaret.regression import load_model, predict_model
from sklearn.preprocessing import LabelEncoder

def predict_fantasy_points(batting_data, bowling_data, match_number):
    """
    Predict fantasy points using PyCaret models for batting and bowling data.
    
    Args:
        batting_data: DataFrame containing batting data or path to batting CSV
        bowling_data: DataFrame containing bowling data or path to bowling CSV
        match_number: Match number for naming the output files
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
        batting_model = load_model(r"D:\App\FIFS_IPL\models\batting_model_flag")
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
            'career_economy': 'career_econ',
            'career_wickets_per_match': 'career_wpm',
            'career_overs_per_match': 'career_opm',
            'last5_average': 'last5_avg',
            'last5_strike_rate': 'last5_sr',
            'last5_economy': 'last5_econ',
            'last5_wickets_per_match': 'last5_wpm',
            'last5_overs_per_match': 'last5_opm',
            'innings_average': 'inns_avg',
            'innings_strike_rate': 'inns_sr',
            'innings_economy': 'inns_econ',
            'innings_wickets_per_match': 'inns_wpm',
            'innings_overs_per_match': 'inns_opm',
            'venue_average': 'ven_avg',
            'venue_strike_rate': 'ven_sr',
            'venue_economy': 'ven_econ',
            'venue_wickets_per_match': 'ven_wpm',
            'venue_overs_per_match': 'ven_opm',
            'season_average': 'ssn_avg',
            'season_strike_rate': 'ssn_sr',
            'season_economy': 'ssn_econ',
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
            # We need to add batting model required columns too based on the error
            'batter_id',
            'career_avg', 'career_rpm', 'career_sr', 'career_bpm', 'career_bfpm', 
            'inns_avg', 'inns_rpm', 'inns_sr', 'inns_bpm', 'inns_bfpm', 
            'ven_avg', 'ven_rpm', 'ven_sr', 'ven_bpm', 'ven_bfpm', 
            'ssn_avg', 'ssn_rpm', 'ssn_sr', 'ssn_bpm', 'ssn_bfpm', 
            'last5_avg', 'last5_sr', 'last5_rpm', 'last5_bfpm', 'last5_bpm'
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
        bowling_model = load_model(r"D:\App\FIFS_IPL\models\bowling_model_flag")
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
