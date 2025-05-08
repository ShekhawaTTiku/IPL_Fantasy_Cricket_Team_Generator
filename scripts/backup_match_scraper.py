# python
import gspread
import logging
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os

# ---------------- CONFIG ----------------
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

"""
This module provides functions to update match details from a Google Sheet.
It handles tasks such as updating Cricinfo IDs, filling opponent teams, innings information,
venue and date information, and replacing team names as necessary.
"""


def debug_env_vars():
    """
    Debug function to check environment variables without exposing sensitive info.
    Loads the environment variables from the `.env` file and verifies that required variables
    are present and properly formatted.

    Returns:
        bool: True if all required environment variables are correctly set, False otherwise.
    """
    load_dotenv(dotenv_path=".env")

    required_vars = ["GOOGLE_PRIVATE_KEY", "GOOGLE_SERVICE_ACCOUNT_EMAIL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logging.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        return False

    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "")
    if not private_key.startswith("-----BEGIN PRIVATE KEY-----") or not private_key.endswith(
            "-----END PRIVATE KEY-----\n"
    ):
        logging.error(
            "Private key is not properly formatted. It should start with '-----BEGIN PRIVATE KEY-----'"
        )
        logging.error(f"Private key starts with: {private_key[:15]}...")
        logging.error("Private key ends with: ...{private_key[-15:]}")
        return False

    client_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "")
    if not client_email or "@" not in client_email or not client_email.endswith(
            ".iam.gserviceaccount.com"
    ):
        logging.warning(
            f"Client email '{client_email}' does not appear to be a valid service account email"
        )
    else:
        logging.info(f"Using service account: {client_email}")
    return True


def get_service_account_creds():
    """
    Get Google service account credentials from environment variables.

    Returns:
        google.oauth2.service_account.Credentials: Credentials for service account access.
    """
    load_dotenv(dotenv_path=".env")

    private_key = os.getenv("GOOGLE_PRIVATE_KEY")
    client_email = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")

    service_account_info = {
        "type": "service_account",
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID", "dummy_key_id"),
        "private_key": private_key,
        "client_email": client_email,
        "client_id": os.getenv("GOOGLE_CLIENT_ID", "dummy_client_id"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}",
    }

    return Credentials.from_service_account_info(service_account_info, scopes=SCOPES)


def update_cricinfo_ids():
    """
    Connect to the Google Sheet and update the 'Cricinfo ID' column in the
    'Backup_Scrapper' worksheet based on the mapping provided in 'SquadData_IPL25'.
    """
    debug_env_vars()
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)

    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)

    squad_data_sheet = spreadsheet.worksheet("SquadData_IPL25")
    squad_data = squad_data_sheet.get_all_records()

    name_to_cricinfo = {row["dream11_name"]: row["key_cricinfo"] for row in squad_data}

    backup_sheet = spreadsheet.worksheet("Backup_Scrapper")
    backup_data = backup_sheet.get_all_records()

    header_row = backup_sheet.row_values(1)
    name_col_idx = header_row.index("Player Name") + 1
    cricinfo_id_col_idx = header_row.index("Cricinfo ID") + 1

    updates_count = 0
    not_found_count = 0
    not_found_names = []

    for row_idx, row in enumerate(backup_data, start=2):
        player_name = row["Player Name"]
        if not player_name:
            continue

        if not row["Cricinfo ID"]:
            if player_name in name_to_cricinfo:
                cricinfo_id = name_to_cricinfo[player_name]
                backup_sheet.update_cell(row_idx, cricinfo_id_col_idx, cricinfo_id)
                logging.info(f"Updated Cricinfo ID for {player_name}: {cricinfo_id}")
                updates_count += 1
            else:
                logging.warning(f"No matching Cricinfo ID found for {player_name}")
                not_found_count += 1
                not_found_names.append(player_name)

    logging.info(
        f"Finished updating Cricinfo IDs. Updated: {updates_count}, Not found: {not_found_count}"
    )
    if not_found_names:
        logging.info("Players not found in mapping:")
        for name in not_found_names:
            logging.info(f"- {name}")


def fill_opponent_teams():
    """
    Fill the 'Opponent' column in the 'Backup_Scrapper' worksheet by determining the opponent
    team based on the unique teams present.
    """
    logging.info("Filling opponent teams in Backup_Scrapper worksheet")
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)

    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)
    backup_sheet = spreadsheet.worksheet("Backup_Scrapper")
    backup_data = backup_sheet.get_all_records()

    header_row = backup_sheet.row_values(1)
    team_col_idx = header_row.index("Team") + 1
    opponent_col_idx = header_row.index("Opponent") + 1

    teams = set()
    for row in backup_data:
        if row["Team"]:
            teams.add(row["Team"])

    teams = list(teams)
    if len(teams) != 2:
        logging.warning(
            f"Expected 2 unique teams, but found {len(teams)}: {teams}"
        )
        if len(teams) < 2:
            logging.info("Not enough teams to determine opponents. Aborting.")
            return

    logging.info(f"Found teams: {teams}")

    batch_updates = []
    updates_count = 0

    for row_idx, row in enumerate(backup_data, start=2):
        if row["Team"] and not row["Opponent"]:
            opponent = teams[1] if row["Team"] == teams[0] else teams[0]
            batch_updates.append(
                {
                    "range": f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, opponent_col_idx)}',
                    "values": [[opponent]],
                }
            )
            updates_count += 1

    if batch_updates:
        spreadsheet.values_batch_update(
            {"valueInputOption": "USER_ENTERED", "data": batch_updates}
        )
        logging.info(f"Updated {updates_count} opponent values")
    else:
        logging.info("No opponent values needed updating")


def fill_innings_info():
    """
    Fill the 'Innings' column in the 'Backup_Scrapper' worksheet based on
    the team names extracted from the 'match_info' worksheet.
    """
    logging.info("Filling innings information in Backup_Scrapper worksheet")
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)

    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        match_info_sheet = spreadsheet.worksheet("match_info")
        match_info_data = match_info_sheet.get_all_records()

        if not match_info_data:
            logging.warning("match_info worksheet is empty")
            return

        inn1_team = match_info_data[0].get("inn1", "")
        inn2_team = match_info_data[0].get("inn2", "")
        if not inn1_team:
            logging.warning("Missing innings 1 team information in match_info")
            return

        logging.info(f"Innings 1 team: {inn1_team}")
        logging.info(f"Innings 2 team: {inn2_team}")

        backup_sheet = spreadsheet.worksheet("Backup_Scrapper")
        backup_data = backup_sheet.get_all_records()
        header_row = backup_sheet.row_values(1)
        team_col_idx = header_row.index("Team") + 1
        innings_col_idx = header_row.index("Innings") + 1

        batch_updates = []
        updates_count_inn1 = 0
        updates_count_inn2 = 0

        for row_idx, row in enumerate(backup_data, start=2):
            team_name = row.get("Team", "")
            if not team_name or row.get("Innings"):
                continue

            if team_name == inn1_team:
                innings_value = 1
                updates_count_inn1 += 1
            else:
                innings_value = 2
                updates_count_inn2 += 1

            batch_updates.append(
                {
                    "range": f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, innings_col_idx)}',
                    "values": [[innings_value]],
                }
            )

        if batch_updates:
            spreadsheet.values_batch_update(
                {"valueInputOption": "USER_ENTERED", "data": batch_updates}
            )
            logging.info(
                f"Updated innings values for {updates_count_inn1} players with value 1"
            )
            logging.info(
                f"Updated innings values for {updates_count_inn2} players with value 2"
            )
            logging.info(
                f"Total updates: {updates_count_inn1 + updates_count_inn2}"
            )
        else:
            logging.info("No innings values needed updating")
    except gspread.exceptions.WorksheetNotFound:
        logging.error("match_info worksheet not found in spreadsheet")
    except Exception as e:
        logging.error(f"Error filling innings info: {str(e)}")


def fill_venue_and_date_info():
    """
    Fill the 'venue' and 'Date' columns in the 'Backup_Scrapper' worksheet based on data
    from the 'match_info' worksheet.
    """
    logging.info("Filling venue and date information in Backup_Scrapper worksheet")
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)

    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        match_info_sheet = spreadsheet.worksheet("match_info")
        match_info_data = match_info_sheet.get_all_records()

        if not match_info_data:
            logging.warning("match_info worksheet is empty")
            return

        venue = match_info_data[0].get("venue", "")
        match_date = match_info_data[0].get("Date", "")
        if not venue:
            logging.warning("Missing venue information in match_info")
            return
        if not match_date:
            logging.warning("Missing date information in match_info")
            return

        logging.info(f"Venue: {venue}")
        logging.info(f"Date: {match_date}")

        backup_sheet = spreadsheet.worksheet("Backup_Scrapper")
        backup_data = backup_sheet.get_all_records()
        header_row = backup_sheet.row_values(1)
        venue_col_idx = header_row.index("venue") + 1
        date_col_idx = header_row.index("Date") + 1

        batch_updates = []
        venue_updates_count = 0
        date_updates_count = 0

        for row_idx, row in enumerate(backup_data, start=2):
            if row.get("Player Name"):
                if not row.get("venue"):
                    batch_updates.append(
                        {
                            "range": f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, venue_col_idx)}',
                            "values": [[venue]],
                        }
                    )
                    venue_updates_count += 1

                if not row.get("Date"):
                    batch_updates.append(
                        {
                            "range": f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, date_col_idx)}',
                            "values": [[match_date]],
                        }
                    )
                    date_updates_count += 1

        if batch_updates:
            spreadsheet.values_batch_update(
                {"valueInputOption": "USER_ENTERED", "data": batch_updates}
            )
            logging.info(
                f"Updated venue for {venue_updates_count} players to '{venue}'"
            )
            logging.info(
                f"Updated date for {date_updates_count} players to '{match_date}'"
            )
            logging.info(f"Total updates: {len(batch_updates)}")
        else:
            logging.info("No venue or date values needed updating")
    except gspread.exceptions.WorksheetNotFound:
        logging.error("match_info worksheet not found in spreadsheet")
    except ValueError as e:
        logging.error(f"Could not find column in worksheet: {str(e)}")
    except Exception as e:
        logging.error(f"Error filling venue and date info: {str(e)}")


def team_checker():
    """
    Check if one of the unique team names is 'CHE' in the 'Backup_Scrapper' worksheet.
    Replaces 'CHE' with 'CSK' in both the 'Team' and 'Opponent' columns.
    """
    logging.info("Running team_checker to replace CHE with CSK")
    credentials = get_service_account_creds()
    client = gspread.authorize(credentials)

    spreadsheet_id = "176vt00qiSQ0oJmXG9AXzoT1N9b1lBMqhggjIQCjlMWE"
    spreadsheet = client.open_by_key(spreadsheet_id)

    try:
        backup_sheet = spreadsheet.worksheet("Backup_Scrapper")
        backup_data = backup_sheet.get_all_records()

        if not backup_data:
            logging.warning("Backup_Scrapper worksheet is empty")
            return

        header_row = backup_sheet.row_values(1)
        team_col_idx = header_row.index("Team") + 1
        opponent_col_idx = header_row.index("Opponent") + 1

        batch_updates = []
        team_updates_count = 0
        opponent_updates_count = 0

        for row_idx, row in enumerate(backup_data, start=2):
            if row.get("Team") == "CHE":
                batch_updates.append(
                    {
                        "range": f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, team_col_idx)}',
                        "values": [["CSK"]],
                    }
                )
                team_updates_count += 1

            if row.get("Opponent") == "CHE":
                batch_updates.append(
                    {
                        "range": f'Backup_Scrapper!{gspread.utils.rowcol_to_a1(row_idx, opponent_col_idx)}',
                        "values": [["CSK"]],
                    }
                )
                opponent_updates_count += 1

        if batch_updates:
            spreadsheet.values_batch_update(
                {"valueInputOption": "USER_ENTERED", "data": batch_updates}
            )
            logging.info(
                f"Updated {team_updates_count} occurrences of CHE to CSK in Team column"
            )
            logging.info(
                f"Updated {opponent_updates_count} occurrences of CHE to CSK in Opponent column"
            )
            logging.info(f"Total updates: {len(batch_updates)}")
        else:
            logging.info("No occurrences of CHE found in Team or Opponent columns")
    except gspread.exceptions.WorksheetNotFound:
        logging.error("Backup_Scrapper worksheet not found in spreadsheet")
    except ValueError as e:
        logging.error(f"Could not find column in worksheet: {str(e)}")
    except Exception as e:
        logging.error(f"Error in team_checker: {str(e)}")


def backup_match_details_scraper(match_number=None):
    """
    Runs the backup match details scraper process.
    This includes updating Cricinfo IDs, filling opponent teams, innings info,
    venue and date info, and running the team checker.
    """
    logging.info("Running backup scrapper")
    update_cricinfo_ids()
    fill_opponent_teams()
    fill_innings_info()
    fill_venue_and_date_info()
    team_checker()