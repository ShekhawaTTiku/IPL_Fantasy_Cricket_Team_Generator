import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname("cricket-ipl-api\.env"), "../cricket-ipl-api/.env")
load_dotenv(dotenv_path=env_path)

# Environment variables
GOOGLE_SHEET_ID_MBM = os.getenv("GOOGLE_SHEET_ID_BOWL")  # Google Sheet ID for MBM data
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n")  # Replace escaped newlines

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

def compute_test_data_bowl(df_mbm: pd.DataFrame, df_match_detail: pd.DataFrame) -> pd.DataFrame:
    """
    Compute bowling stats for each player-match in df_match_detail using historical data from df_mbm.
    
    Parameters:
        df_mbm (pd.DataFrame): Match-by-match dataset containing bowling scorecard data.
        df_match_detail (pd.DataFrame): Dataset containing match and player details.
    
    Returns:
        pd.DataFrame: A DataFrame containing test data for bowlers with required statistics.
    """
    # Copy & preprocess
    df_mbm = df_mbm.copy()
    df_match_detail = df_match_detail.copy()

    # Convert numeric columns to appropriate types and fill missing values
    numeric_columns = ['runs', 'balls', 'wickets', 'maiden', 'eco']
    for col in numeric_columns:
        df_mbm[col] = pd.to_numeric(df_mbm[col], errors='coerce').fillna(0).astype(int)

    df_mbm['date'] = pd.to_datetime(df_mbm['date'])
    df_match_detail['Date'] = pd.to_datetime(df_match_detail['Date'] + ' 2025', format='%d %b %Y')
    df_mbm['key_cricinfo'] = df_mbm['key_cricinfo'].astype(str)
    df_match_detail['Cricinfo ID'] = df_match_detail['Cricinfo ID'].astype(str)

    # Rename columns for consistency
    df_match_detail['league'] = 'IPL'
    df_match_detail['season'] = df_match_detail['Date'].dt.year
    df_match_detail.rename(columns={
        'Team': 'bowler_team',
        'Opponent': 'bat_team',
        'Venue': 'venue',
        'Innings': 'inns',
        'Cricinfo ID': 'bowler_id'
    }, inplace=True)

    output_records = []

    for _, row in df_match_detail.iterrows():
        # Extract direct fields
        bowler_id = row['bowler_id']
        inns = row['inns']
        bowler_team = row['bowler_team']
        bat_team = row['bat_team']
        venue = row['venue']
        league = row.get('league', 'Unknown League')  # Default to 'Unknown League' if not present
        season = row['Date'].year
        match_date = row['Date']

        # Filter historical data for the bowler
        hist_df = df_mbm[(df_mbm['date'] < match_date) & (df_mbm['key_cricinfo'] == bowler_id)]

        # A) Career statistics
        hist_career = hist_df[hist_df['league'] == league]
        career_stats = compute_bowling_stats(hist_career)
        if np.isnan(career_stats['career_avg']):
            career_stats = compute_bowling_stats(hist_df)

        # B) Innings statistics
        hist_innings = hist_career[hist_career['innings'] == inns]
        inns_stats = compute_bowling_stats(hist_innings)
        if np.isnan(inns_stats['inns_avg']):
            hist_global_inns = hist_df[hist_df['innings'] == inns]
            inns_stats = compute_bowling_stats(hist_global_inns)

        # C) Venue statistics
        hist_venue = hist_career[hist_career['venue'] == venue]
        venue_stats = compute_bowling_stats(hist_venue)
        if np.isnan(venue_stats['ven_avg']):
            venue_stats = compute_bowling_stats(hist_df)

        # D) Season statistics
        season_stats = compute_season_stats(hist_df, league, season)

        # E) Last 5 matches
        last5_stats = compute_last5_bowling_stats(hist_df.sort_values('date').tail(5))

        # F) Career debut flag
        career_debut = 1 if hist_df.empty else 0

        # Build the final record
        record = {
            'inns': inns,
            'bowler_id': bowler_id,
            'bowler_team': bowler_team,
            'bat_team': bat_team,
            'venue': venue,
            'league': league,
            'career_avg': career_stats['career_avg'],
            'career_eco': career_stats['career_eco'],
            'career_sr': career_stats['career_sr'],
            'career_wpm': career_stats['career_wpm'],
            'career_opm': career_stats['career_opm'],
            'inns_avg': inns_stats['inns_avg'],
            'inns_eco': inns_stats['inns_eco'],
            'inns_sr': inns_stats['inns_sr'],
            'inns_wpm': inns_stats['inns_wpm'],
            'inns_opm': inns_stats['inns_opm'],
            'ven_avg': venue_stats['ven_avg'],
            'ven_eco': venue_stats['ven_eco'],
            'ven_sr': venue_stats['ven_sr'],
            'ven_wpm': venue_stats['ven_wpm'],
            'ven_opm': venue_stats['ven_opm'],
            'season': season,
            'ssn_avg': season_stats['ssn_avg'],
            'ssn_eco': season_stats['ssn_eco'],
            'ssn_sr': season_stats['ssn_sr'],
            'ssn_wpm': season_stats['ssn_wpm'],
            'ssn_opm': season_stats['ssn_opm'],
            'last5_avg': last5_stats['last5_avg'],
            'last5_sr': last5_stats['last5_sr'],
            'last5_eco': last5_stats['last5_eco'],
            'last5_wpm': last5_stats['last5_wpm'],
            'last5_opm': last5_stats['last5_opm'],
            'career_debut': career_debut
        }

        # Replace NaN values with 0
        record = {k: (0 if isinstance(v, float) and np.isnan(v) else v) for k, v in record.items()}
        output_records.append(record)

    return pd.DataFrame(output_records)

def compute_bowling_stats(df: pd.DataFrame) -> dict:
    """
    Compute bowling statistics from a DataFrame.
    """
    if df.empty:
        # Return all necessary keys with NaN if the DataFrame is empty
        return {
            'career_avg': np.nan, 'career_eco': np.nan, 'career_sr': np.nan,
            'career_wpm': np.nan, 'career_opm': np.nan,
            'inns_avg': np.nan, 'inns_eco': np.nan, 'inns_sr': np.nan,
            'inns_wpm': np.nan, 'inns_opm': np.nan,
            'ven_avg': np.nan, 'ven_eco': np.nan, 'ven_sr': np.nan,
            'ven_wpm': np.nan, 'ven_opm': np.nan
        }

    runs = df['runs'].sum()
    balls = df['balls'].sum()
    wickets = df['wickets'].sum()
    matches = len(df)

    avg = runs / (wickets if wickets > 0 else 1)
    eco = (runs / balls * 6) if balls > 0 else 0
    sr = balls / (wickets if wickets > 0 else 1)
    wpm = wickets / matches
    opm = balls / 6 / matches

    # Return all necessary statistics with appropriate keys
    return {
        'career_avg': avg, 'career_eco': eco, 'career_sr': sr,
        'career_wpm': wpm, 'career_opm': opm,
        'inns_avg': avg, 'inns_eco': eco, 'inns_sr': sr,
        'inns_wpm': wpm, 'inns_opm': opm,
        'ven_avg': avg, 'ven_eco': eco, 'ven_sr': sr,
        'ven_wpm': wpm, 'ven_opm': opm
    }

def compute_season_stats(hist_df: pd.DataFrame, league: str, season: int) -> dict:
    """
    Compute season-based statistics for the given league and season.

    Parameters:
        hist_df (pd.DataFrame): Historical match data for the bowler.
        league (str): The league to filter.
        season (int): The season year to compute statistics for.

    Returns:
        dict: A dictionary with season statistics (e.g., ssn_avg, ssn_eco, etc.).
    """
    # Filter historical data for the specified league and season
    season_df = hist_df[(hist_df['league'] == league) & (hist_df['date'].dt.year == season)]

    # If no season data exists, provide fallback keys with NaN values
    if season_df.empty:
        return {
            'ssn_avg': np.nan, 'ssn_eco': np.nan, 'ssn_sr': np.nan,
            'ssn_wpm': np.nan, 'ssn_opm': np.nan
        }

    # Use compute_bowling_stats to calculate statistics for the season
    stats = compute_bowling_stats(season_df)

    return {
        'ssn_avg': stats['career_avg'],  # Use 'career_avg' for season average
        'ssn_eco': stats['career_eco'],  # Use 'career_eco' for season economy
        'ssn_sr': stats['career_sr'],    # Use 'career_sr' for season strike rate
        'ssn_wpm': stats['career_wpm'],  # Use 'career_wpm' for season wickets per match
        'ssn_opm': stats['career_opm']   # Use 'career_opm' for season overs per match
    }

def compute_last5_bowling_stats(df: pd.DataFrame) -> dict:
    """
    Compute rolling last-5 match statistics for bowling.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing the last 5 matches for a bowler.
    
    Returns:
        dict: A dictionary containing the last 5 match statistics (e.g., last5_avg, last5_eco, etc.).
    """
    if df.empty:
        # If no data exists, return all required keys with 0 as default values
        return {
            'last5_avg': 0, 'last5_sr': 0, 'last5_eco': 0,
            'last5_wpm': 0, 'last5_opm': 0
        }

    # Compute statistics for the last 5 matches
    runs = df['runs'].sum()
    balls = df['balls'].sum()
    wickets = df['wickets'].sum()
    matches = len(df)

    # Ensure no division-by-zero errors
    avg = runs / (wickets if wickets > 0 else 1)
    sr = balls / (wickets if wickets > 0 else 1)
    eco = (runs / balls * 6) if balls > 0 else 0
    wpm = wickets / matches
    opm = balls / 6 / matches

    return {
        'last5_avg': avg,
        'last5_sr': sr,
        'last5_eco': eco,
        'last5_wpm': wpm,
        'last5_opm': opm
    }

if __name__ == "__main__":
    # Fetch Match Details Data
    df_match_detail = pd.read_csv(r"Today_Match_Details\match_15.csv")

    # Fetch MBM Data
    df_mbm = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_MBM, sheet_index=0)

    # Compute Test Data for Batting
    test_data_bat = compute_test_data_bowl(df_mbm, df_match_detail)

    # Print the resulting DataFrame
    with pd.option_context('display.max_columns', None):
        print(test_data_bat)