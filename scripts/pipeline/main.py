import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
from datetime import datetime
import json
import match_scraper
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
    
    Args:
        match_number (int, optional): Specific match number to scrape.
                                     If None, will prompt for input.
    
    Returns:
        dict: A dictionary containing match details and file path information
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
            print(f"❌ Failed to scrape match data: {result['message']}")
        
        return result
    
    except ImportError:
        print("❌ Error: Could not import run_match_scrapper from match_scrapper module.")
        print("   Make sure match_scrapper.py is in the same directory as main.py.")
        return {"success": False, "message": "Import error with match_scrapper module"}
    
    except Exception as e:
        print(f"❌ Error while running match scrapper: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

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
    match_scrapping()