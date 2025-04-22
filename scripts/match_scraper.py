import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Cricbuzz Fixtures URL for IPL 2025
FIXTURES_URL = "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/matches"
headers = {"User-Agent": "Mozilla/5.0"}

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname("cricket-ipl-api\.env"), "../cricket-ipl-api/.env")
load_dotenv(dotenv_path=env_path)

# Environment variables
GOOGLE_SHEET_ID_MAPPING = os.getenv("GOOGLE_SHEET_ID_MAPPING")
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY").replace("\\n", "\n")  # Replace escaped newlines


def create_id_mapping():
    """Fetch player ID mapping from Google Sheet."""
    try:
        credentials_info = {
            "type": "service_account",
            "client_email": GOOGLE_SERVICE_ACCOUNT_EMAIL,
            "private_key": GOOGLE_PRIVATE_KEY,
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)

        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(GOOGLE_SHEET_ID_MAPPING).sheet1  # Access the first sheet
        records = sheet.get_all_records()

        df = pd.DataFrame(records)

        id_mapping = {}
        for _, row in df.iterrows():
            if pd.isna(row['key_cricbuzz']) or pd.isna(row['key_cricinfo']):
                continue

            cricbuzz_id = str(int(row['key_cricbuzz'])) if not pd.isna(row['key_cricbuzz']) else None
            cricinfo_id = str(int(row['key_cricinfo'])) if not pd.isna(row['key_cricinfo']) else None

            if cricbuzz_id and cricinfo_id:
                id_mapping[cricbuzz_id] = cricinfo_id

        return id_mapping
    except Exception as e:
        print(f"Error creating ID mapping: {e}")
        return {}


# Global variable for id mapping
player_id_mapping = create_id_mapping()


def get_match_urls():
    """Fetch all match URLs from the IPL 2025 fixtures page and list them by number."""
    response = requests.get(FIXTURES_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    match_links = []
    seen_links = set()

    for link in soup.find_all("a", class_="text-hvr-underline", href=True):
        if "/cricket-scores/" in link["href"]:
            match_id = link["href"].split("/")[-2]
            match_name = link["href"].split("/")[-1]
            match_url = f"https://www.cricbuzz.com/cricket-match-facts/{match_id}/{match_name}"

            if match_url not in seen_links:
                match_links.append(match_url)
                seen_links.add(match_url)
        elif "/live-cricket-scores/" in link["href"]:
            match_id = link["href"].split("/")[-2]
            match_name = link["href"].split("/")[-1]
            match_url = f"https://www.cricbuzz.com/cricket-match-facts/{match_id}/{match_name}"

            if match_url not in seen_links:
                match_links.append(match_url)
                seen_links.add(match_url)

    return match_links


def extract_match_date(soup):
    """Extracts match date from the match facts page."""
    try:
        date_tags = soup.find_all("span", class_="schedule-date")

        for tag in date_tags:
            timestamp = tag.get("timestamp")
            if timestamp:
                try:
                    match_date_obj = datetime.fromtimestamp(int(timestamp) / 1000)
                    formatted_date = match_date_obj.strftime("%d %b")
                    return formatted_date
                except Exception as e:
                    print(f"Error parsing timestamp: {e}")

        print("Error: Date not found.")
        return "Unknown"

    except Exception as e:
        print(f"Error extracting match date: {e}")
        return "Unknown"


def extract_player_id(url):
    """Extract player ID from URL."""
    try:
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == "profiles" and i + 1 < len(parts):
                return parts[i + 1]
        return "Unknown"
    except Exception as e:
        print(f"Error extracting player ID: {e}")
        return "Unknown"


def extract_playing_xi(soup):
    """Extracts Playing XI and Bench players from the match page."""
    match_info_sections = soup.select("div.cb-col.cb-col-100")

    team1_players, team2_players = [], []
    bench1_players, bench2_players = [], []

    team1_urls, team2_urls = [], []
    bench1_urls, bench2_urls = [], []

    team1_ids, team2_ids = [], []
    bench1_ids, bench2_ids = [], []

    for section in match_info_sections:
        title_div = section.find("div", class_="cb-col cb-col-27 cb-mat-fct-itm text-bold")
        if not title_div:
            continue

        title_text = title_div.get_text(strip=True)

        player_names = []
        player_urls = []
        player_ids = []
        player_links = section.select("div.cb-col.cb-col-73.cb-mat-fct-itm a.text-hvr-underline")

        for player in player_links:
            player_name = player.get_text(strip=True)
            player_url = player.get("href")
            player_id = extract_player_id(player_url)

            player_names.append(player_name)
            player_urls.append(player_url)
            player_ids.append(player_id)

        if "Playing" in title_text:
            if not team1_players:
                team1_players = player_names[:11]
                team1_urls = player_urls[:11]
                team1_ids = player_ids[:11]
            else:
                team2_players = player_names[:11]
                team2_urls = player_urls[:11]
                team2_ids = player_ids[:11]
        elif "Bench" in title_text:
            if not bench1_players:
                bench1_players = player_names[:5]
                bench1_urls = player_urls[:5]
                bench1_ids = player_ids[:5]
            else:
                bench2_players = player_names[:5]
                bench2_urls = player_urls[:5]
                bench2_ids = player_ids[:5]

    base_url = "https://www.cricbuzz.com"
    team1_full_urls = [f"{base_url}{url}" for url in team1_urls]
    team2_full_urls = [f"{base_url}{url}" for url in team2_urls]
    bench1_full_urls = [f"{base_url}{url}" for url in bench1_urls]
    bench2_full_urls = [f"{base_url}{url}" for url in bench2_urls]

    team1_players.extend(bench1_players)
    team2_players.extend(bench2_players)
    team1_ids.extend(bench1_ids)
    team2_ids.extend(bench2_ids)

    return (team1_players, team2_players), (team1_full_urls + bench1_full_urls, team2_full_urls + bench2_full_urls), (
        team1_ids, team2_ids)


def extract_match_details(match_url):
    """Extracts match details including date, playing XI, teams, venue, toss, innings, and player IDs."""
    response = requests.get(match_url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching match page: {response.status_code}")
        return None, []

    soup = BeautifulSoup(response.text, "html.parser")
    match_date = extract_match_date(soup)
    fact_sections = soup.select("div.cb-col.cb-col-73.cb-mat-fct-itm")

    venue = "Unknown"
    if len(fact_sections) > 4:
        full_venue = fact_sections[4].get_text(strip=True)
        venue = full_venue.split(',')[0].strip()

    venue = str(venue)

    toss_info = fact_sections[2].get_text(strip=True) if len(fact_sections) > 2 else "Unknown"

    teams = fact_sections[0].get_text(strip=True).split(",")[0].split(" vs ") if len(fact_sections) > 0 else []
    if len(teams) < 2:
        print(f"Error extracting team names for {match_url}")
        return match_date, []
    team1_name, team2_name = teams

    (team1_players, team2_players), (_, _), (team1_ids, team2_ids) = extract_playing_xi(soup)

    if not team1_players or not team2_players:
        print(f"Error extracting playing XI for {match_url}")
        return match_date, []

    team_name_map = {
        "Rajasthan Royals": "RR",
        "Sunrisers Hyderabad": "SRH",
        "Chennai Super Kings": "CSK",
        "Mumbai Indians": "MI",
        "Royal Challengers Bangalore": "RCB",
        "Kolkata Knight Riders": "KKR",
        "Delhi Capitals": "DC",
        "Punjab Kings": "PBKS",
        "Lucknow Super Giants": "LSG",
        "Gujarat Titans": "GT"
    }

    toss_winner = toss_info.split(" won the toss and opt to ")
    if len(toss_winner) == 2:
        toss_team_full, decision = toss_winner[0], toss_winner[1]
        toss_team = team_name_map.get(toss_team_full, toss_team_full)

        if decision == "bat":
            bat_first_team = toss_team
        else:
            bat_first_team = team2_name if toss_team == team1_name else team1_name

        team1_innings = 1 if bat_first_team == team1_name else 2
        team2_innings = 1 if bat_first_team == team2_name else 2
    else:
        team1_innings, team2_innings = 1, 2

    for team_full_name in team_name_map.keys():
        if team_name_map[team_full_name] == team1_name or team_full_name == team1_name:
            team1_full = team_full_name
            break
    else:
        team1_full = team1_name

    for team_full_name in team_name_map.keys():
        if team_name_map[team_full_name] == team2_name or team_full_name == team2_name:
            team2_full = team_full_name
            break
    else:
        team2_full = team2_name

    match_data = []

    for player, player_id in zip(team1_players, team1_ids):
        cricinfo_id = player_id_mapping.get(player_id, "Unknown")
        match_data.append(
            [player, team1_full, team2_full, venue, toss_info, team1_innings, player_id, cricinfo_id, match_date])

    for player, player_id in zip(team2_players, team2_ids):
        cricinfo_id = player_id_mapping.get(player_id, "Unknown")
        match_data.append(
            [player, team2_full, team1_full, venue, toss_info, team2_innings, player_id, cricinfo_id, match_date])

    return match_date, match_data


def save_to_csv(data, match_number):
    download_folder = "Today_Match_Details"
    os.makedirs(download_folder, exist_ok=True)
    filename = f"match_{match_number}.csv"
    file_path = os.path.join(download_folder, filename)

    df = pd.DataFrame(data, columns=["Player Name", "Team", "Opponent", "Venue", "Toss Info", "Innings", "Player ID",
                                     "Cricinfo ID", "Date"])

    try:
        df['Venue'] = df['Venue'].astype('string')
    except:
        df['Venue'] = df['Venue'].astype(str)

    df.to_csv(file_path, index=False)

    print(f"CSV file saved successfully: {file_path}")


def check_venue_dtype(match_number):
    filename = f"Today_Match_Details/match_{match_number}.csv"
    df = pd.read_csv(filename, dtype={'Venue': 'string'})
    if df['Venue'].dtype != 'string':
        try:
            df['Venue'] = df['Venue'].astype('string')
        except:
            df['Venue'] = df['Venue'].astype(str)
        df.to_csv(filename, index=False)
        print("CSV file updated with venue explicitly as string type")


def fetch_match_details_by_number():
    """Asks for a match number, fetches match details, and saves to CSV."""
    match_urls = get_match_urls()
    try:
        match_number = int(input("Enter the match number: "))
        if 1 <= match_number <= len(match_urls):
            selected_url = match_urls[match_number - 1]
            match_date, match_data = extract_match_details(selected_url)
            if match_data:
                save_to_csv(match_data, match_number)
                print(f"Match details saved for {selected_url}")
            else:
                print(f"No Playing XI data found for match number {match_number}")
        else:
            print("Invalid match number. Please try again.")
    except ValueError:
        print("Invalid input. Please enter a number.")


def get_today_details(match_number):
    """
    Fetches details for a specific match by its number and returns as DataFrame.

    Args:
        match_number (int): The number of the match to fetch details for

    Returns:
        pd.DataFrame: DataFrame containing match details or None if unsuccessful
    """
    match_urls = get_match_urls()

    if 1 <= match_number <= len(match_urls):
        selected_url = match_urls[match_number - 1]
        match_date, match_data = extract_match_details(selected_url)

        if match_data:
            df = pd.DataFrame(match_data, columns=[
                "Player Name", "Team", "Opponent", "Venue",
                "Toss Info", "Innings", "Player ID", "Cricinfo ID", "Date"
            ])

            df['Player ID'] = df['Player ID'].astype(int)
            df['Cricinfo ID'] = df['Cricinfo ID'].astype(int)

            try:
                df['Venue'] = df['Venue'].astype('string')
            except:
                df['Venue'] = df['Venue'].astype(str)

            return df
        else:
            print("No match data found!")
            return None
    else:
        print("Invalid match number!")
        return None

# Uncomment the following line to run the script standalone:
# if __name__ == "__main__":
#     get_today_details(1)