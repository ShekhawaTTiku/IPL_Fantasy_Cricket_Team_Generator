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
GOOGLE_SHEET_ID_MBM = os.getenv("GOOGLE_SHEET_ID_BAT")  # Google Sheet ID for MBM data
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

def compute_stats(df: pd.DataFrame) -> dict:
    """
    Given a dataframe (group) of past matches,
    compute aggregated batting statistics:
      - avg: runs per dismissal
      - rpm: runs per match
      - sr: strike rate (runs*100 per ball)
      - bpm: boundaries per match
      - bfpm: balls faced per match
    Returns NaN for empty groups.
    """
    if df.empty:
        return {'avg': np.nan, 'rpm': np.nan, 'sr': np.nan, 'bpm': np.nan, 'bfpm': np.nan}
    
    df = df.copy()
    df['isOut'] = pd.to_numeric(df['isOut'], errors='coerce').fillna(0).astype(int)

    total_runs = df['runs'].sum()
    dismissals = df['isOut'].sum()
    matches = len(df)
    total_balls = df['balls'].sum()
    boundaries = df['fours'].sum() + df['sixes'].sum()

    avg = total_runs / (dismissals if dismissals > 0 else 1)
    rpm = total_runs / matches
    sr = (total_runs * 100) / (total_balls if total_balls > 0 else 1)
    bpm = boundaries / matches
    bfpm = total_balls / matches
    return {'avg': avg, 'rpm': rpm, 'sr': sr, 'bpm': bpm, 'bfpm': bfpm}

def compute_last5_stats(df: pd.DataFrame) -> dict:
    """
    Given up to 5 prior matches, compute rolling stats:
      - last5_avg, last5_sr, last5_rpm, last5_bfpm, last5_bpm
    Returns zeros for empty groups.
    """
    if df.empty:
        return {'last5_avg': 0, 'last5_sr': 0, 'last5_rpm': 0, 'last5_bfpm': 0, 'last5_bpm': 0}
    total_runs = df['runs'].sum()
    dismissals = df['isOut'].sum()
    total_balls = df['balls'].sum()
    boundaries = df['fours'].sum() + df['sixes'].sum()
    matches = len(df)

    last5_avg = total_runs / (dismissals if dismissals > 0 else 1)
    last5_sr = (total_runs * 100) / (total_balls if total_balls > 0 else 1)
    last5_rpm = total_runs / matches
    last5_bfpm = df['balls'].mean()
    last5_bpm = boundaries / matches
    return {'last5_avg': last5_avg, 'last5_sr': last5_sr,
            'last5_rpm': last5_rpm, 'last5_bfpm': last5_bfpm, 'last5_bpm': last5_bpm}

def compute_test_data_bat(df_mbm: pd.DataFrame, df_match_detail: pd.DataFrame) -> pd.DataFrame:
    """
    Compute pre-match batting stats for each player-match in df_match_detail
    using historical df_mbm. Applies:
      A) Career stats by league with overall fallback
      B) Innings stats by innings with league + global fallback
      C) Venue stats by venue with overall fallback
      D) Season stats per updated hierarchy
      E) Last-5 matches rolling stats
      F) Debut flag & fill nulls with zeros
    """
    # Copy & preprocess
    df_mbm = df_mbm.copy()
    df_match_detail = df_match_detail.copy()

    numeric_columns = ['runs', 'balls', 'fours', 'sixes', 'isOut']
    for col in numeric_columns:
        df_mbm[col] = pd.to_numeric(df_mbm[col], errors='coerce').fillna(0).astype(int)

    df_mbm['date'] = pd.to_datetime(df_mbm['date'])
    df_match_detail['Date'] = pd.to_datetime(df_match_detail['Date'] + ' 2025', format='%d %b %Y')
    df_mbm['batter_cricinfo_id'] = df_mbm['batter_cricinfo_id'].astype(str)
    df_match_detail['Cricinfo ID'] = df_match_detail['Cricinfo ID'].astype(str)

    # Static assignment
    df_match_detail['league'] = 'IPL'
    df_match_detail['season'] = df_match_detail['Date'].dt.year
    df_match_detail.rename(columns={
        'Team': 'bat_team', 'Opponent': 'bowl_team',
        'Venue': 'venue', 'Innings': 'inns'
    }, inplace=True)

    output_records = []
    for _, row in df_match_detail.iterrows():
        # Direct fields
        batter_id = row['Cricinfo ID']
        inns = row['inns']
        bat_team = row['bat_team']
        bowl_team = row['bowl_team']
        venue = row['venue']
        league = row['league']
        season = row['season']
        match_date = row['Date']
        # Historical matches before today
        hist_df = df_mbm[(df_mbm['date'] < match_date) & (df_mbm['batter_cricinfo_id'] == batter_id)]

        # A) Career stats
        hist_career = hist_df[hist_df['league'] == league]
        career_stats = compute_stats(hist_career)
        if np.isnan(career_stats['avg']):
            career_stats = compute_stats(hist_df)

        # B) Innings stats: league innings, fallback to global innings
        hist_innings_league = hist_career[hist_career['innings'] == inns]
        inns_stats = compute_stats(hist_innings_league)
        if np.isnan(inns_stats['avg']):
            hist_global_inns = hist_df[hist_df['innings'] == inns]
            inns_stats = compute_stats(hist_global_inns)

        # C) Venue stats
        hist_venue = hist_career[hist_career['venue'] == venue]
        venue_stats = compute_stats(hist_venue)
        if np.isnan(venue_stats['avg']):
            venue_stats = compute_stats(hist_df)

        # D) Season stats per updated hierarchy
        # 1) Prior IPL seasons
        prev_years = sorted(hist_df[hist_df['league'] == league]['date'].dt.year.unique())
        if prev_years:
            last_year = prev_years[-1]
            season_group = hist_df[(hist_df['league'] == league) &
                                   (hist_df['date'].dt.year == last_year)]
            ssn_stats = compute_stats(season_group)
        else:
            # 2) Other leagues by recency
            other = hist_df.copy()
            groups = []
            for (lg, yr), grp in other.groupby(['league', other['date'].dt.year]):
                groups.append((grp['date'].max(), grp))
            # sort descending by date
            groups.sort(key=lambda x: x[0], reverse=True)
            ssn_stats = None
            for _, grp in groups:
                if len(grp) >= 3:
                    ssn_stats = compute_stats(grp)
                    break
            if ssn_stats is None:
                # 3) fallback: same calendar year
                curr_same = other[other['date'].dt.year == season]
                ssn_stats = compute_stats(curr_same)

        # E) Last 5 matches
        last5 = hist_df.sort_values('date').tail(5)
        last5_stats = compute_last5_stats(last5)

        # F) Debut flag
        career_debut = 1 if hist_df.empty else 0

        # Build record & fill null stats with zeros
        record = {
            'inns': inns,
            'batter_id': batter_id,
            'bat_team': bat_team,
            'bowl_team': bowl_team,
            'venue': venue,
            'league': league,
            'career_avg': career_stats['avg'],
            'career_rpm': career_stats['rpm'],
            'career_sr': career_stats['sr'],
            'career_bpm': career_stats['bpm'],
            'career_bfpm': career_stats['bfpm'],
            'inns_avg': inns_stats['avg'],
            'inns_rpm': inns_stats['rpm'],
            'inns_sr': inns_stats['sr'],
            'inns_bpm': inns_stats['bpm'],
            'inns_bfpm': inns_stats['bfpm'],
            'ven_avg': venue_stats['avg'],
            'ven_rpm': venue_stats['rpm'],
            'ven_sr': venue_stats['sr'],
            'ven_bpm': venue_stats['bpm'],
            'ven_bfpm': venue_stats['bfpm'],
            'season': season,
            'ssn_avg': ssn_stats['avg'],
            'ssn_rpm': ssn_stats['rpm'],
            'ssn_sr': ssn_stats['sr'],
            'ssn_bpm': ssn_stats['bpm'],
            'ssn_bfpm': ssn_stats['bfpm'],
            'last5_avg': last5_stats['last5_avg'],
            'last5_sr': last5_stats['last5_sr'],
            'last5_rpm': last5_stats['last5_rpm'],
            'last5_bfpm': last5_stats['last5_bfpm'],
            'last5_bpm': last5_stats['last5_bpm'],
            'career_debut': career_debut
        }
        # replace any NaN numeric values with 0
        for k, v in record.items():
            if isinstance(v, float) and np.isnan(v):
                record[k] = 0

        output_records.append(record)

    test_data_bat = pd.DataFrame(output_records)
    return test_data_bat

def get_test_bat(mbm_bat_final, match_df):
    """
    Example function to demonstrate how to use the compute_test_data_bat function.
    This is a placeholder and should be replaced with actual data fetching and processing.
    """
    # Compute Test Data for Batting
    test_data_bat = compute_test_data_bat(mbm_bat_final, match_df)

    return test_data_bat

if __name__ == "__main__":
    # Fetch Match Details Data
    df_match_detail = pd.read_csv(r"Today_Match_Details\match_15.csv")
    # Fetch MBM Data
    df_mbm = fetch_google_sheet_data(sheet_id=GOOGLE_SHEET_ID_MBM, sheet_index=1)
    get_test_bat(df_mbm, df_match_detail)