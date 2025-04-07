#import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timezone
import os
import requests
import pandas as pd

# Cricbuzz Fixtures URL for IPL 2025
FIXTURES_URL = "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/matches"
headers = {"User-Agent": "Mozilla/5.0"}

def get_match_urls():
    """Fetch all match URLs from the IPL 2025 fixtures page and list them by number."""
    response = requests.get(FIXTURES_URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    match_links = []
    seen_links = set()

    # Find all <a> tags with the specific class name
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

    print(f"🔗 Found {len(match_links)} unique Match Facts URLs\n")
    for idx, url in enumerate(match_links, start=1):
        print(f"[{idx}] {url}")

    return match_links

get_match_urls()


from datetime import datetime

def extract_match_date(soup):
    """Extracts match date from the match facts page."""
    try:
        print("📅 Extracting match date...")

        # Find all spans with the class "schedule-date"
        date_tags = soup.find_all("span", class_="schedule-date")
        print(f"📝 Number of date tags found: {len(date_tags)}")

        for tag in date_tags:
            # Print the complete tag for debugging
            print(f"🔍 Found tag: {tag}")

            # Get the timestamp attribute
            timestamp = tag.get("timestamp")
            if timestamp:
                try:
                    # Convert the timestamp to a readable date format
                    match_date_obj = datetime.fromtimestamp(int(timestamp) / 1000)
                    formatted_date = match_date_obj.strftime("%d %b")
                    print(f"📅 Formatted date from timestamp: {formatted_date}")
                    return formatted_date
                except Exception as e:
                    print(f"⚠ Error parsing timestamp: {e}")

        print("⚠ Date not found.")
        return "Unknown"

    except Exception as e:
        print(f"⚠ Error extracting match date: {e}")
        return "Unknown"



def extract_player_id(url):
    """Extract player ID from URL."""
    try:
        # URL format: https://www.cricbuzz.com/profiles/12627/kl-rahul
        # or: /profiles/12627/kl-rahul
        parts = url.split('/')
        for i, part in enumerate(parts):
            if part == "profiles" and i+1 < len(parts):
                return parts[i+1]
        return "Unknown"
    except Exception as e:
        print(f"⚠ Error extracting player ID: {e}")
        return "Unknown"

def extract_playing_xi(soup):
    """Extracts Playing XI and Bench players from the match page."""
    print("🏏 Extracting Playing XI and Bench players...")

    match_info_sections = soup.select("div.cb-col.cb-col-100")

    team1_players, team2_players = [], []
    bench1_players, bench2_players = [], []
    
    # Lists for URLs
    team1_urls, team2_urls = [], []
    bench1_urls, bench2_urls = [], []
    
    # New lists for player IDs
    team1_ids, team2_ids = [], []
    bench1_ids, bench2_ids = [], []

    # Function to extract player ID from URL
    def extract_player_id(url):
        try:
            # URL format is typically /profiles/12345/player-name
            parts = url.split('/')
            for i, part in enumerate(parts):
                if part == "profiles" and i+1 < len(parts):
                    return parts[i+1]
            return "Unknown"
        except Exception as e:
            print(f"⚠ Error extracting player ID: {e}")
            return "Unknown"

    for section in match_info_sections:
        title_div = section.find("div", class_="cb-col cb-col-27 cb-mat-fct-itm text-bold")
        if not title_div:
            continue

        title_text = title_div.get_text(strip=True)

        player_names = []
        player_urls = []
        player_ids = []  # Store extracted IDs
        player_links = section.select("div.cb-col.cb-col-73.cb-mat-fct-itm a.text-hvr-underline")

        for player in player_links:
            player_name = player.get_text(strip=True)
            player_url = player.get("href")
            player_id = extract_player_id(player_url)  # Extract ID from URL
            
            player_names.append(player_name)
            player_urls.append(player_url)
            player_ids.append(player_id)
            
            print(f"👤 Player: {player_name}, URL: {player_url}, ID: {player_id}")

        if "Playing" in title_text:
            if not team1_players:
                team1_players = player_names[:11]
                team1_urls = player_urls[:11]
                team1_ids = player_ids[:11]  # Store team1 player IDs
                print(f"✅ Team 1 Playing XI: {team1_players}")
            else:
                team2_players = player_names[:11]
                team2_urls = player_urls[:11]
                team2_ids = player_ids[:11]  # Store team2 player IDs
                print(f"✅ Team 2 Playing XI: {team2_players}")
        elif "Bench" in title_text:
            if not bench1_players:
                bench1_players = player_names[:5]
                bench1_urls = player_urls[:5]
                bench1_ids = player_ids[:5]  # Store bench1 player IDs
                print(f"🪑 Team 1 Bench: {bench1_players}")
            else:
                bench2_players = player_names[:5]
                bench2_urls = player_urls[:5]
                bench2_ids = player_ids[:5]  # Store bench2 player IDs
                print(f"🪑 Team 2 Bench: {bench2_players}")

    # Construct full URLs
    base_url = "https://www.cricbuzz.com"
    team1_full_urls = [f"{base_url}{url}" for url in team1_urls]
    team2_full_urls = [f"{base_url}{url}" for url in team2_urls]
    bench1_full_urls = [f"{base_url}{url}" for url in bench1_urls]
    bench2_full_urls = [f"{base_url}{url}" for url in bench2_urls]
    
    # Display player info including IDs
    print("\n📋 All Player URLs and IDs:")
    for name, url, pid in zip(team1_players, team1_full_urls, team1_ids):
        print(f"  - {name}: {url} (ID: {pid})")
    
    # Combine playing XI and bench
    team1_players.extend(bench1_players)
    team2_players.extend(bench2_players)
    
    # Combine IDs as well
    team1_ids.extend(bench1_ids)
    team2_ids.extend(bench2_ids)

    # Return player names, URLs, and IDs
    return (team1_players, team2_players), (team1_full_urls + bench1_full_urls, team2_full_urls + bench2_full_urls), (team1_ids, team2_ids)


def load_player_mapping(file_path):
    """Load player mappings from the CSV file."""
    player_mapping = {}
    try:
        df = pd.read_csv(file_path)
        for index, row in df.iterrows():
            # Convert key_cricbuzz to string to match the extracted player IDs
            key_cricbuzz = str(int(row['key_cricbuzz'])) if pd.notna(row['key_cricbuzz']) else ""
            player_mapping[key_cricbuzz] = row['key_cricinfo']
    except Exception as e:
        print(f"Error loading player mapping: {e}")
    return player_mapping


def extract_match_details(match_url, player_mapping):
    """Extracts match details including date, playing XI, teams, venue, toss, innings, and player IDs."""
    print(f"🌐 Fetching match details from: {match_url}")
    response = requests.get(match_url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Error fetching match page: {response.status_code}")
        return None, []

    soup = BeautifulSoup(response.text, "html.parser")
    match_date = extract_match_date(soup)
    fact_sections = soup.select("div.cb-col.cb-col-73.cb-mat-fct-itm")
    venue = fact_sections[4].get_text(strip=True) if len(fact_sections) > 4 else "Unknown"
    toss_info = fact_sections[2].get_text(strip=True) if len(fact_sections) > 2 else "Unknown"
    print(f"📍 Venue: {venue}, 🪙 Toss Info: {toss_info}")

    teams = fact_sections[0].get_text(strip=True).split(",")[0].split(" vs ") if len(fact_sections) > 0 else []
    if len(teams) < 2:
        print(f"⚠ Error extracting team names for {match_url}")
        return match_date, []
    team1_name, team2_name = teams
    print(f"✅ Teams found: {team1_name} vs {team2_name}")

    # Updated to unpack three return values including player IDs
    (team1_players, team2_players), (team1_urls, team2_urls), (team1_ids, team2_ids) = extract_playing_xi(soup)
    
    if not team1_players or not team2_players:
        print(f"⚠ Error extracting playing XI for {match_url}")
        return match_date, []

    # Mapping full team names to abbreviations
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

    # Fixing innings logic
    toss_winner = toss_info.split(" won the toss and opt to ")
    if len(toss_winner) == 2:
        toss_team_full, decision = toss_winner[0], toss_winner[1]
        toss_team = team_name_map.get(toss_team_full, toss_team_full)  # Convert to abbreviation if needed

        # Determine the batting first team based on toss decision
        if decision == "bat":
            bat_first_team = toss_team
        else:
            bat_first_team = team2_name if toss_team == team1_name else team1_name

        # Determine innings based on the batting team
        team1_innings = 1 if bat_first_team == team1_name else 2
        team2_innings = 1 if bat_first_team == team2_name else 2
    else:
        # Default innings assignment if toss info is not available
        team1_innings, team2_innings = 1, 2

    print(f"Team 1 Innings: {team1_innings}, Team 2 Innings: {team2_innings}")

    # Updated to include player IDs in match data
    # Using full team names from the mapping dictionary keys
    match_data = []
    
    # Get the full team names from the dictionary or use the extracted names
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
    
    for player, player_id in zip(team1_players, team1_ids):
        cricinfo_id = player_mapping.get(player_id, "Unknown")
        match_data.append([player, team1_full, team2_full, venue, toss_info, team1_innings, player_id, cricinfo_id])
    for player, player_id in zip(team2_players, team2_ids):
        cricinfo_id = player_mapping.get(player_id, "Unknown")
        match_data.append([player, team2_full, team1_full, venue, toss_info, team2_innings, player_id, cricinfo_id])

    print(f"✅ Successfully extracted match details for {match_url}")
    return match_date, match_data


def save_to_csv(data, match_number):
    download_folder = "Today_Match_Details"
    os.makedirs(download_folder, exist_ok=True)
    filename = f"match_{match_number}.csv"
    file_path = os.path.join(download_folder, filename)

    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Player Name", "Team", "Opponent", "Venue", "Toss Info", "Innings", "Player ID", "Cricinfo ID"])
        writer.writerows(data)

    print(f"✅ CSV file saved successfully: {file_path}")


def fetch_match_details_by_number():
    """Asks for a match number, fetches match details, and saves to CSV."""
    match_urls = get_match_urls()
    try:
        match_number = int(input("Enter the match number: "))
        if 1 <= match_number <= len(match_urls):
            selected_url = match_urls[match_number - 1]
            player_mapping = load_player_mapping('data/register_data/squadData_ipl25_updated.csv')
            match_date, match_data = extract_match_details(selected_url, player_mapping)
            if match_data:
                save_to_csv(match_data)
                print(f"✅ Match details saved for {selected_url}")
            else:
                print(f"❌ No Playing XI data found for match number {match_number}")
        else:
            print("❌ Invalid match number. Please try again.")
    except ValueError:
        print("❌ Invalid input. Please enter a number.")


if __name__ == "__main__":
    match_urls = get_match_urls()
    match_number = int(input("Enter the match number from the list: "))
    if 1 <= match_number <= len(match_urls):
        selected_url = match_urls[match_number - 1]
        print(f"✅ Selected Match URL: {selected_url}")
        player_mapping = load_player_mapping('data/register_data/squadData_ipl25_updated.csv')
        match_date, match_data = extract_match_details(selected_url, player_mapping)
        if match_data:
            save_to_csv(match_data, match_number)
        else:
            print("❌ No match data found!")
    else:
        print("❌ Invalid match number!")