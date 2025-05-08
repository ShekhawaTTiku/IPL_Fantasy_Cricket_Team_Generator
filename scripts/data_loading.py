import logging
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = ".env"
load_dotenv(dotenv_path=env_path)

# Environment variables
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n")
GOOGLE_SHEET_ID_BAT = os.getenv("GOOGLE_SHEET_ID_BAT")  # Google Sheet ID for batting data
GOOGLE_SHEET_ID_BOWL = os.getenv("GOOGLE_SHEET_ID_BOWL")  # Google Sheet ID for bowling data
GOOGLE_SHEET_ID_IPL_DATA = os.getenv("GOOGLE_SHEET_ID_MAPPING")

# Authenticate Google Sheets API
def authenticate_google_sheets():
    """Authenticate and return a gspread client."""
    credentials_info = {
        "type": "service_account",
        "client_email": GOOGLE_SERVICE_ACCOUNT_EMAIL,
        "private_key": GOOGLE_PRIVATE_KEY,
        "token_uri": "https://oauth2.googleapis.com/token"
    }
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    return gspread.authorize(credentials)

def fetch_google_sheet_data(sheet_id, sheet_index=1):
    """
    Fetch data from the specified Google Sheet by index.
    
    Parameters:
        sheet_id (str): The ID of the Google Sheet.
        sheet_index (int): The index of the sheet to fetch (0-based).
        
    Returns:
        pd.DataFrame: Data from the specified sheet as a Pandas DataFrame.
    """
    client = authenticate_google_sheets()
    sheet = client.open_by_key(sheet_id).get_worksheet(sheet_index)  # Access sheet by index
    records = sheet.get_all_records()  # Fetch all rows as a list of dictionaries
    return pd.DataFrame(records)  # Convert to a Pandas DataFrame

def get_data():
    """
    Main function to generate test data for batting and bowling.
    """
    try:

        # Fetch Batting MBM Data
        mbm_bat_final = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_BAT, sheet_index=1)

        # Fetch Bowling MBM Data
        mbm_bowl_final = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_BOWL, sheet_index=1)

        # Fetch IPL perf metric data
        perf_metric_df = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_IPL_DATA, sheet_index=5)

        # Fetch IPL Squad Data
        squad_df = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_IPL_DATA, sheet_index=1)

        return mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df

    except Exception as e:
        logging.error(f"Error fetching data from Google Sheets: {e}")
        return None