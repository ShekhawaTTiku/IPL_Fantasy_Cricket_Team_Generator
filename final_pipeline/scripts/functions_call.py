import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from test_data_gen_bat import get_bat_test
from test_data_gen_bowl import get_bowl_test
from test_data_gen_matchup import get_matchup_score

# Load environment variables from .env file
env_path = "cricket-ipl-api/.env"
load_dotenv(dotenv_path=env_path)

# Environment variables
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n")  # Replace escaped newlines
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

def main():
    """
    Main function to generate test data for batting and bowling.
    """
    try:
        # Take the match number as input from the user
        match_number = int(input("Enter the match number: "))

        # Construct the file path dynamically based on user input
        file_path = f"Today_Match_Details/match_{match_number}.csv"

        # Load the match details into a DataFrame
        try:
            match_df = pd.read_csv(file_path)
            print(f"Successfully loaded match details from '{file_path}'.")
        except FileNotFoundError:
            print(f"Error: The file '{file_path}' does not exist. Please check the match number and try again.")

        # Fetch Batting MBM Data
        mbm_bat_final = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_BAT, sheet_index=1)
        print(mbm_bat_final.head())

        # Fetch Bowling MBM Data
        mbm_bowl_final = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_BOWL, sheet_index=1)
        print(mbm_bowl_final.head())

        # Fetch IPL perf metric data
        perf_metric_df = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_IPL_DATA, sheet_index=5)
        print(perf_metric_df.head())

        # Fetch IPL Squad Data
        squad_df = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_IPL_DATA, sheet_index=1)
        print(squad_df.head())

        # Generate Test Data for Batting
        test_data_bat = get_bat_test(mbm_bat_final, match_df)

        # Generate Test Data for Bowling
        test_data_bowl = get_bowl_test(mbm_bowl_final, match_df)

        # Generate Test Data for Matchup
        test_data_matchup = get_matchup_score(perf_metric_df, mbm_bowl_final, match_df, squad_df)

        # Save the generated test data to CSV files
        os.makedirs("output", exist_ok=True)  # Ensure the output directory exists
        test_data_bat.to_csv(f"final_pipeline/output/test_data_bat{match_number}.csv", index=False)
        test_data_bowl.to_csv(f"final_pipeline/output/test_data_bowl{match_number}.csv", index=False)
        test_data_matchup.to_csv(f"final_pipeline/output/test_data_matchup{match_number}.csv", index=False)

        print(f"Test data for batting saved to 'output/test_data_bat{match_number}.csv'")
        print(f"Test data for bowling saved to 'output/test_data_bowl{match_number}.csv'")
        print(f"Test data for matchup saved to 'output/test_data_matchup{match_number}.csv'")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()