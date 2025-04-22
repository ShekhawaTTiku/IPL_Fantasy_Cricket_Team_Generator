import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os

# ---------------- CONFIG ----------------
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# Sheet configurations
#BATTING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1dumS1w_IQ7pv448tm-RKVqAQTEgOMKw59wf914qLHs0/edit?usp=sharingt"
#BOWLING_SHEET_URL = "https://docs.google.com/spreadsheets/d/1-RxTFF7yXo8iB7Dl6JxdHQmub7Wr21aZZ2f_k18gwiU/edit?usp=sharing"
#SQUAD_SHEET_URL = "https://docs.google.com/spreadsheets/d/1CeJ3u_c7YoAKBENOhpzNjUCTglT5m3vivXbGRGqBFvY/edit?gid=0#gid=0"

#BATTING_SHEET_NAME = "Sheet1"
#BOWLING_SHEET_NAME = "Sheet1"
#SQUAD_SHEET_NAME = "Sheet1"

def debug_env_vars():
    """Debug function to check environment variables without exposing sensitive info"""
    load_dotenv(dotenv_path="../cricket-ipl-api/.env")

    # Check for existence of required env variables
    required_vars = ['GOOGLE_PRIVATE_KEY', 'GOOGLE_SERVICE_ACCOUNT_EMAIL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        return False
        
    # Check private key format (safely)
    private_key = os.getenv('GOOGLE_PRIVATE_KEY', '')
    if not private_key.startswith('-----BEGIN PRIVATE KEY-----') or not private_key.endswith('-----END PRIVATE KEY-----\n'):
        print("ERROR: Private key is not properly formatted. It should start with '-----BEGIN PRIVATE KEY-----'")
        print(f"Private key starts with: {private_key[:15]}...")
        print(f"Private key ends with: ...{private_key[-15:]}")
        return False
    
    # Check client email
    client_email = os.getenv('GOOGLE_SERVICE_ACCOUNT_EMAIL', '')
    if not client_email or '@' not in client_email or not client_email.endswith('.iam.gserviceaccount.com'):
        print(f"WARNING: Client email '{client_email}' does not appear to be a valid service account email")
    else:
        print(f"Using service account: {client_email}")
    return True

# ---------------- HELPER FUNCTIONS ----------------
def get_service_account_creds():
    """Get Google service account credentials from environment variables"""
    load_dotenv(dotenv_path="../cricket-ipl-api/.env")

    private_key = os.getenv('GOOGLE_PRIVATE_KEY')
    client_email = os.getenv('GOOGLE_SERVICE_ACCOUNT_EMAIL')
    #project_id = os.getenv('GOOGLE_PROJECT_ID')

    service_account_info = {
        "type": "service_account",
        #"project_id": project_id,
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

def update_cricinfo_ids():
    """
    Connect to Google Sheet, map player names from Backup_Scrapper with key_cricinfo from 
    SquadData_IPL25, and update the Cricinfo ID column in Backup_Scrapper.
    """
    debug_env_vars()
    # Get credentials using your environment variables approach
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)
    
    # Open the spreadsheet by its title or URL
    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"  # From your URL
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    # Access the SquadData_IPL25 worksheet to get player data and cricinfo IDs
    squad_data_sheet = spreadsheet.worksheet('SquadData_IPL25')
    squad_data = squad_data_sheet.get_all_records()
    
    # Create a mapping dictionary from dream11_name to key_cricinfo
    name_to_cricinfo = {row['dream11_name']: row['key_cricinfo'] for row in squad_data}
    
    # Access the Backup_Scrapper worksheet
    backup_sheet = spreadsheet.worksheet('Backup_Scrapper')
    backup_data = backup_sheet.get_all_records()
    
    # Get the column indices we need
    header_row = backup_sheet.row_values(1)
    name_col_idx = header_row.index('Player Name') + 1  # +1 because gspread is 1-indexed
    cricinfo_id_col_idx = header_row.index('Cricinfo ID') + 1
    
    # Count for statistics
    updates_count = 0
    not_found_count = 0
    not_found_names = []
    
    # Iterate through rows in Backup_Scrapper where Name is filled but Cricinfo ID is not
    for row_idx, row in enumerate(backup_data, start=2):  # start=2 to account for header row
        player_name = row['Player Name']
        
        # Skip empty rows
        if not player_name:
            continue
            
        # If Cricinfo ID is empty, look it up and update
        if not row['Cricinfo ID']:
            # Look up the cricinfo ID from our mapping
            if player_name in name_to_cricinfo:
                cricinfo_id = name_to_cricinfo[player_name]
                
                # Update the Cricinfo ID cell for this row
                backup_sheet.update_cell(row_idx, cricinfo_id_col_idx, cricinfo_id)
                print(f"Updated Cricinfo ID for {player_name}: {cricinfo_id}")
                updates_count += 1
            else:
                print(f"Warning: No matching cricinfo ID found for {player_name}")
                not_found_count += 1
                not_found_names.append(player_name)
    
    print(f"Finished updating Cricinfo IDs. Updated: {updates_count}, Not found: {not_found_count}")
    
    if not_found_names:
        print("Players not found in mapping:")
        for name in not_found_names:
            print(f"- {name}")

def fill_opponent_teams():
    print("Filling opponent teams in Backup_Scrapper worksheet")
    
    # Get credentials and connect to spreadsheet
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)
    
    # Open the spreadsheet
    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    # Access the Backup_Scrapper worksheet
    backup_sheet = spreadsheet.worksheet('Backup_Scrapper')
    backup_data = backup_sheet.get_all_records()
    
    # Get column indices
    header_row = backup_sheet.row_values(1)
    team_col_idx = header_row.index('Team') + 1  # +1 because gspread is 1-indexed
    opponent_col_idx = header_row.index('Opponent') + 1
    
    # Find all unique team values (should be 2)
    teams = set()
    for row in backup_data:
        if row['Team']:  # Only consider non-empty team values
            teams.add(row['Team'])
    
    teams = list(teams)
    
    if len(teams) != 2:
        print(f"Warning: Expected 2 unique teams, but found {len(teams)}: {teams}")
        if len(teams) < 2:
            print("Not enough teams to determine opponents. Aborting.")
            return
    
    print(f"Found teams: {teams}")
    
    # Prepare batch updates
    batch_updates = []
    updates_count = 0
    
    # For each row, if team is filled but opponent is empty, fill with the other team
    for row_idx, row in enumerate(backup_data, start=2):  # start=2 to account for header row
        if row['Team'] and not row['Opponent']:
            # If the team is the first one, opponent is the second; otherwise opponent is the first
            opponent = teams[1] if row['Team'] == teams[0] else teams[0]
            
            # Add to batch updates
            batch_updates.append({
                'range': f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, opponent_col_idx)}',
                'values': [[opponent]]
            })
            updates_count += 1
    
    # Perform batch update if there are any updates
    if batch_updates:
        spreadsheet.values_batch_update(
            {"valueInputOption": "USER_ENTERED", "data": batch_updates}
        )
        print(f"Updated {updates_count} opponent values")
    else:
        print("No opponent values needed updating")

def fill_innings_info():
    """
    Fill the Innings column in Backup_Scrapper worksheet based on match_info.
    
    Reads the match_info worksheet to get team names for innings 1 and 2.
    Then updates the Innings column with:
    - 1 for players from the first innings team (inn1)
    - 2 for all other players (including inn2 team)
    """
    print("Filling innings information in Backup_Scrapper worksheet")
    
    # Get credentials and connect to spreadsheet
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)
    
    # Open the spreadsheet
    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    # Access the match_info worksheet
    try:
        match_info_sheet = spreadsheet.worksheet('match_info')
        match_info_data = match_info_sheet.get_all_records()
        
        if not match_info_data:
            print("Warning: match_info worksheet is empty")
            return
        
        # Get the team name for innings 1
        inn1_team = match_info_data[0].get('inn1', '')
        inn2_team = match_info_data[0].get('inn2', '')  # Still get inn2 for logging
        
        if not inn1_team:
            print("Warning: Missing innings 1 team information in match_info")
            return
            
        print(f"Innings 1 team: {inn1_team}")
        print(f"Innings 2 team: {inn2_team}")
        
        # Access the Backup_Scrapper worksheet
        backup_sheet = spreadsheet.worksheet('Backup_Scrapper')
        backup_data = backup_sheet.get_all_records()
        
        # Get column indices
        header_row = backup_sheet.row_values(1)
        team_col_idx = header_row.index('Team') + 1  # +1 because gspread is 1-indexed
        innings_col_idx = header_row.index('Innings') + 1
        
        # Prepare batch updates
        batch_updates = []
        updates_count_inn1 = 0
        updates_count_inn2 = 0
        
        # Update innings values based on team names
        for row_idx, row in enumerate(backup_data, start=2):  # start=2 to account for header row
            team_name = row.get('Team', '')
            
            # Skip rows with no team or already filled innings
            if not team_name or row.get('Innings'):
                continue
                
            # Set innings value based on team
            if team_name == inn1_team:
                innings_value = 1
                updates_count_inn1 += 1
            else:
                # All other teams (including inn2_team) get innings value 2
                innings_value = 2
                updates_count_inn2 += 1
            
            batch_updates.append({
                'range': f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, innings_col_idx)}',
                'values': [[innings_value]]
            })
        
        # Perform batch update if there are any updates
        if batch_updates:
            spreadsheet.values_batch_update(
                {"valueInputOption": "USER_ENTERED", "data": batch_updates}
            )
            print(f"Updated innings values for {updates_count_inn1} players with value 1")
            print(f"Updated innings values for {updates_count_inn2} players with value 2")
            print(f"Total updates: {updates_count_inn1 + updates_count_inn2}")
        else:
            print("No innings values needed updating")
    
    except gspread.exceptions.WorksheetNotFound:
        print("Error: match_info worksheet not found in spreadsheet")
    except Exception as e:
        print(f"Error filling innings info: {str(e)}")

def fill_venue_and_date_info():
    """
    Fill the venue and date columns in Backup_Scrapper worksheet based on match_info.
    
    Reads the venue and date values from match_info worksheet and fills them
    for all players in the Backup_Scrapper worksheet.
    """
    print("Filling venue and date information in Backup_Scrapper worksheet")
    
    # Get credentials and connect to spreadsheet
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)
    
    # Open the spreadsheet
    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    try:
        # Access the match_info worksheet
        match_info_sheet = spreadsheet.worksheet('match_info')
        match_info_data = match_info_sheet.get_all_records()
        
        if not match_info_data:
            print("Warning: match_info worksheet is empty")
            return
        
        # Get the venue and date from match_info
        venue = match_info_data[0].get('venue', '')
        match_date = match_info_data[0].get('Date', '')
        
        if not venue:
            print("Warning: Missing venue information in match_info")
            return
            
        if not match_date:
            print("Warning: Missing date information in match_info")
            return
            
        print(f"Venue: {venue}")
        print(f"Date: {match_date}")
        
        # Access the Backup_Scrapper worksheet
        backup_sheet = spreadsheet.worksheet('Backup_Scrapper')
        backup_data = backup_sheet.get_all_records()
        
        # Get column indices
        header_row = backup_sheet.row_values(1)
        venue_col_idx = header_row.index('venue') + 1  # +1 because gspread is 1-indexed
        date_col_idx = header_row.index('Date') + 1
        
        # Prepare batch updates
        batch_updates = []
        venue_updates_count = 0
        date_updates_count = 0
        
        # Update venue and date values for all rows with players
        for row_idx, row in enumerate(backup_data, start=2):  # start=2 to account for header row
            # Only process rows that have a player name
            if row.get('Player Name'):
                # Update venue if empty
                if not row.get('venue'):
                    batch_updates.append({
                        'range': f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, venue_col_idx)}',
                        'values': [[venue]]
                    })
                    venue_updates_count += 1
                
                # Update date if empty
                if not row.get('Date'):
                    batch_updates.append({
                        'range': f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, date_col_idx)}',
                        'values': [[match_date]]
                    })
                    date_updates_count += 1
        
        # Perform batch update if there are any updates
        if batch_updates:
            spreadsheet.values_batch_update(
                {"valueInputOption": "USER_ENTERED", "data": batch_updates}
            )
            print(f"Updated venue for {venue_updates_count} players to '{venue}'")
            print(f"Updated date for {date_updates_count} players to '{match_date}'")
            print(f"Total updates: {len(batch_updates)}")
        else:
            print("No venue or date values needed updating")
    
    except gspread.exceptions.WorksheetNotFound:
        print("Error: match_info worksheet not found in spreadsheet")
    except ValueError as e:
        print(f"Error: Could not find column in worksheet: {str(e)}")
    except Exception as e:
        print(f"Error filling venue and date info: {str(e)}")

def team_checker():
    """
    Check if one of the unique team names is CHE in Backup_Scrapper worksheet.
    Replace CHE with CSK in both Team and Opponent columns.
    """
    print("Running team_checker to replace CHE with CSK")
    
    # Get credentials and connect to spreadsheet
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)
    
    # Open the spreadsheet
    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)
    
    try:
        # Access the Backup_Scrapper worksheet
        backup_sheet = spreadsheet.worksheet('Backup_Scrapper')
        backup_data = backup_sheet.get_all_records()
        
        if not backup_data:
            print("Warning: Backup_Scrapper worksheet is empty")
            return
        
        # Get column indices
        header_row = backup_sheet.row_values(1)
        team_col_idx = header_row.index('Team') + 1  # +1 because gspread is 1-indexed
        opponent_col_idx = header_row.index('Opponent') + 1
        
        # Prepare batch updates
        batch_updates = []
        team_updates_count = 0
        opponent_updates_count = 0
        
        # Check each row to find and replace CHE with CSK
        for row_idx, row in enumerate(backup_data, start=2):  # start=2 to account for header row
            # Check Team column
            if row.get('Team') == 'CHE':
                batch_updates.append({
                    'range': f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, team_col_idx)}',
                    'values': [['CSK']]
                })
                team_updates_count += 1
            
            # Check Opponent column
            if row.get('Opponent') == 'CHE':
                batch_updates.append({
                    'range': f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, opponent_col_idx)}',
                    'values': [['CSK']]
                })
                opponent_updates_count += 1
        
        # Perform batch update if there are any updates
        if batch_updates:
            spreadsheet.values_batch_update(
                {"valueInputOption": "USER_ENTERED", "data": batch_updates}
            )
            print(f"Updated {team_updates_count} occurrences of CHE to CSK in Team column")
            print(f"Updated {opponent_updates_count} occurrences of CHE to CSK in Opponent column")
            print(f"Total updates: {len(batch_updates)}")
        else:
            print("No occurrences of CHE found in Team or Opponent columns")
    
    except gspread.exceptions.WorksheetNotFound:
        print("Error: Backup_Scrapper worksheet not found in spreadsheet")
    except ValueError as e:
        print(f"Error: Could not find column in worksheet: {str(e)}")
    except Exception as e:
        print(f"Error in team_checker: {str(e)}")

def backup_match_scrapping(match_number=None):
     print(f"Running backup scrapper")
     update_cricinfo_ids()
     fill_opponent_teams()
     fill_innings_info()
     fill_venue_and_date_info()
     team_checker()

if __name__ == "__main__":
   backup_match_scrapping()