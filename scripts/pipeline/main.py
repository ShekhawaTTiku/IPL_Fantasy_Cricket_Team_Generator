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
import optimizer
import mergeFp
import predictor
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

    private_key = os.getenv('GOOGLE_PRIVATE_KEY')
    client_email = os.getenv('GOOGLE_CLIENT_EMAIL')
    project_id = os.getenv('GOOGLE_PROJECT_ID')

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
    """
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
    """Generate batting data for a specific match ID using batsman_data_generation.py"""

    output_path = batsman_gen.batting_test_gen(match_id)
    return output_path

def bowl_test_gen(match_id):
    '''Generate bowling data for a specific match ID using bowler_data_generation.py"""'''

    output_path = bowler_gen.bowling_test_gen(match_id)
    return output_path
    
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
    batting_data_path_wow =bat_test_gen(match_number)
    bowl_test_gen(match_number)

    
    batting_data_path = f"D:/App/FIFS_IPL/test_data_output/output_bat_{match_number}.csv"
    bowling_data_path = f"D:/App/FIFS_IPL/test_data_output/output_bowl_{match_number}.csv"
    #print(batting_data_path)
    predictor.predict_fantasy_points(batting_data_path, bowling_data_path, match_number)
    #merge fantasy points to generate final fantasy points
    mergeFp.merge_fantasy_predictions(match_number)
    #optimize team selection based on merged fantasy points
    optimizer.optimize_team(match_number)

