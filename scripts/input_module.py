import logging
import pandas as pd
import random
from datetime import datetime

# from main import squad_df
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

def get_input_method():
    """Get the user's preferred input method."""
    while True:
        print("\nChoose Input Method:")
        print("1. MATCH NUMBER")
        print("2. CUSTOM INPUT")
        try:
            choice = int(input("Enter your choice (1 or 2): "))
            if choice in [1, 2]:
                return choice
            else:
                logging.warning("Invalid choice entered")
        except ValueError:
            logging.warning("Non-numeric input received")

def get_match_details_method_1():
    """Get match details using match number input method."""
    while True:
        try:
            match_number = int(input("Enter the match number: "))
            if match_number > 0:
                return match_number
            else:
                logging.warning("Invalid match number entered")
        except ValueError:
            logging.warning("Non-numeric match number entered")

def create_match_df(squad_df, team1, team2, venue, toss_info, team1_innings, team2_innings):
    """Create match DataFrame from input details."""
    try:
        # Filter squad_df for players from both teams
        team1_players = squad_df[squad_df['team'] == team1].copy()
        team2_players = squad_df[squad_df['team'] == team2].copy()

        if team1_players.empty or team2_players.empty:
            raise ValueError(f"No players found for {'team1' if team1_players.empty else 'team2'}")

        # Add toss information to players
        toss_info = f"{toss_info['toss_winner']} won the toss and chose to {toss_info['toss_decision']}"

        # Create dataframes for both teams with required columns
        team1_df = pd.DataFrame({
            'Player Name': team1_players['cricbuzz_name'],
            'Team': team1,
            'Opponent': team2,
            'Venue': venue,
            'Toss Info': toss_info,
            'Innings': team1_innings,
            'Cricinfo ID': team1_players['key_cricinfo']
        })

        team2_df = pd.DataFrame({
            'Player Name': team2_players['cricbuzz_name'],
            'Team': team2,
            'Opponent': team1,
            'Venue': venue,
            'Toss Info': toss_info,
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

def get_match_details_method_2():
    """Get match details using detailed information input method."""
    logging.info("Starting detailed match information input")
    print("\nEnter Match Details:")

    # Get team inputs
    print(f"\nAvailable teams: {', '.join(VALID_TEAMS)}")
    while True:
        team1 = input("Enter Team 1: ").upper()
        if team1 in VALID_TEAMS:
            break
        logging.warning(f"Invalid team name entered: {team1}")

    while True:
        team2 = input("Enter Team 2: ").upper()
        if team2 in VALID_TEAMS and team2 != team1:
            break
        logging.warning(f"Invalid team name entered: {team2}")

    # Get venue
    print("\nAvailable venues:")
    for idx, venue in enumerate(VALID_VENUES, 1):
        print(f"{idx}. {venue}")

    while True:
        venue = input("Enter venue (name or number): ")
        try:
            if venue.isdigit() and 1 <= int(venue) <= len(VALID_VENUES):
                venue = VALID_VENUES[int(venue)-1]
                break
            elif venue in VALID_VENUES:
                break
            logging.warning(f"Invalid venue entered: {venue}")
        except ValueError:
            logging.warning("Invalid venue input")

    # Get toss details
    while True:
        toss_winner = input(f"Enter toss winner ({team1}/{team2}): ").upper()
        if toss_winner in [team1, team2]:
            break
        logging.warning(f"Invalid toss winner entered: {toss_winner}")

    while True:
        toss_decision = input("Enter toss decision (bat/field): ").lower()
        if toss_decision in ['bat', 'field']:
            break
        logging.warning(f"Invalid toss decision entered: {toss_decision}")

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

    # Create match details dictionary to return
    match_details = {
        'team1': team1,
        'team2': team2,
        'venue': venue,
        'toss_winner': toss_winner,
        'toss_decision': toss_decision,
        'team1_innings': team1_innings,
        'team2_innings': team2_innings,
        'toss_info': toss_info
    }

    logging.info("Match details collected successfully")
    return match_details

def process_input(input_method, squad_df):
    """Main function to process user input and create match DataFrame."""
    try:
        # Method 1: Match number input
        if input_method == 1:
            match_number = get_match_details_method_1()
            logging.info(f"Processing match number: {match_number}")
            try:
                match_df = match_detail_scraper(match_number=match_number)
                if match_df is None or match_df.empty:
                    logging.warning("Primary match scraper failed, trying backup")
                    match_df = backup_match_details_scraper()
                return match_df, match_number
            except Exception as e:
                logging.error(f"Error in match scraping: {str(e)}")
                return pd.DataFrame(), None

        else:
            match_details = get_match_details_method_2()
            match_df = create_match_df(
                squad_df=squad_df,
                team1=match_details['team1'],
                team2=match_details['team2'],
                venue=match_details['venue'],
                toss_info=match_details['toss_info'],
                team1_innings=match_details['team1_innings'],
                team2_innings=match_details['team2_innings']
            )
            return match_df, generate_match_number()

    except Exception as e:
        logging.error(f"Error processing input: {str(e)}")
        return pd.DataFrame()