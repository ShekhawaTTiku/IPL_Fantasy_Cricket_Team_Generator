import logging
import pandas as pd
import random
from datetime import datetime

from scripts.match_scraper import match_detail_scraper
from scripts.backup_match_scraper import backup_match_details_scraper

# Constants
VALID_TEAMS = ['CSK', 'DC', 'GT', 'KKR', 'LSG', 'MI', 'PBKS', 'RCB', 'RR', 'SRH']
VALID_VENUES = [
    'MA Chidambaram Stadium',
    'Arun Jaitley Stadium',
    'Narendra Modi Stadium',
    'Eden Gardens',
    'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium',
    'Wankhede Stadium',
    'Punjab Cricket Association IS Bindra Stadium',
    'M.Chinnaswamy Stadium',
    'Sawai Mansingh Stadium',
    'Rajiv Gandhi International Stadium',
    'Himachal Pradesh Cricket Association Stadium',
    'Maharaja Yadavindra Singh International Cricket Stadium',
    'Barsapara Cricket Stadium',
    'Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium'
]

def get_formatted_date():
    """Return current date in the required DD MMM format."""
    return datetime.now().strftime("%d %b")

def generate_match_number():
    """Generate a unique match number based on current time."""
    base = int(datetime.now().strftime("%d%m%y"))
    return base * 100 + random.randint(0, 99)

def create_match_df(squad_df, team1, team2, venue, toss_info, team1_innings, team2_innings):
    """Create match DataFrame from input details."""
    try:
        # Filter squad_df for players from both teams
        team1_players = squad_df[squad_df['team'] == team1].copy()
        team2_players = squad_df[squad_df['team'] == team2].copy()

        if team1_players.empty or team2_players.empty:
            raise ValueError(f"No players found for {'team1' if team1_players.empty else 'team2'}")

        # Add toss information to players
        toss_string = f"{toss_info['toss_winner']} won the toss and chose to {toss_info['toss_decision']}"

        # Create dataframes for both teams with required columns
        team1_df = pd.DataFrame({
            'Player Name': team1_players['cricbuzz_name'],
            'Team': team1,
            'Opponent': team2,
            'Venue': venue,
            'Toss Info': toss_string,
            'Innings': team1_innings,
            'Cricinfo ID': team1_players['key_cricinfo']
        })

        team2_df = pd.DataFrame({
            'Player Name': team2_players['cricbuzz_name'],
            'Team': team2,
            'Opponent': team1,
            'Venue': venue,
            'Toss Info': toss_string,
            'Innings': team2_innings,
            'Cricinfo ID': team2_players['key_cricinfo']
        })

        # Combine both dataframes
        match_df = pd.concat([team1_df, team2_df], ignore_index=True)

        # Add current date in DD MMM format
        match_df['Date'] = get_formatted_date()

        return match_df

    except Exception as e:
        logging.error(f"Error creating match DataFrame: {str(e)}")
        raise

def process_input_scraper(match_number):
    """Process match details using the scraper method."""
    logging.info(f"Processing match number: {match_number}")
    try:
        match_df = match_detail_scraper(match_number=match_number)
        if match_df is None or match_df.empty:
            logging.warning("Primary match scraper failed, trying backup")
            match_df = backup_match_details_scraper()

        # FIX: Ensure the final DataFrame from either scraper has string IDs to prevent merge errors.
        if match_df is not None and not match_df.empty and 'Cricinfo ID' in match_df.columns:
            match_df['Cricinfo ID'] = match_df['Cricinfo ID'].astype(str)

        return match_df
    except Exception as e:
        logging.error(f"Error in match scraping: {str(e)}")
        return pd.DataFrame()

def process_input_custom(squad_df, match_details):
    """Process match details from custom user input."""
    try:
        # FIX: Ensure the squad_df passed in has string IDs. This will also affect the
        # global DataFrame in app.py for this request, fixing downstream merges.
        squad_df['key_cricinfo'] = squad_df['key_cricinfo'].astype(str)

        team1 = match_details['team1'].upper()
        team2 = match_details['team2'].upper()
        venue = match_details['venue']
        toss_winner = match_details['toss_winner'].upper()
        toss_decision = match_details['toss_decision'].lower()

        toss_info = {
            'toss_winner': toss_winner,
            'toss_decision': toss_decision
        }

        # Determine innings for each team
        if (toss_winner == team1 and toss_decision == 'bat') or (toss_winner == team2 and toss_decision == 'field'):
            team1_innings = 1
            team2_innings = 2
        else:
            team1_innings = 2
            team2_innings = 1

        match_df = create_match_df(
            squad_df=squad_df,
            team1=team1,
            team2=team2,
            venue=venue,
            toss_info=toss_info,
            team1_innings=team1_innings,
            team2_innings=team2_innings
        )
        return match_df
    except Exception as e:
        logging.error(f"Error processing custom input: {str(e)}")
        return pd.DataFrame()
