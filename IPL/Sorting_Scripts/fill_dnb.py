import pandas as pd
import os


def read_info_file(info_file_path):
    """
    Reads an info CSV file and extracts player information.
    Returns a DataFrame with columns: 'team' and 'player' based on lines like:
    info,player,{team},{player name}
    """
    players = []
    with open(info_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            parts = line.split(',')
            # Check for player lines
            if len(parts) >= 4 and parts[0].strip() == 'info' and parts[1].strip() == 'player':
                team = parts[2].strip()
                player = parts[3].strip()
                players.append({'team': team, 'player': player})
    return pd.DataFrame(players)


def get_registry_mapping(info_file_path):
    """
    Reads the info file and builds a mapping from player name to hex code
    based on registry lines:
    info,registry,people,{player name},{hex code}
    Umpire lines (starting with "info,umpire") are skipped.
    """
    mapping = {}
    with open(info_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            parts = line.split(',')
            # Consider only registry lines for people
            if len(parts) >= 5 and parts[0].strip() == 'info' and parts[1].strip() == 'registry' and parts[
                2].strip() == 'people':
                player_name = parts[3].strip()
                hex_code = parts[4].strip()
                mapping[player_name] = hex_code
    return mapping


def fill_dnb_for_match(match_id, df_match, info_folder):
    """
    For a given match (match_id), using the subset of the batting card (df_match)
    and the corresponding info file from info_folder, this function appends rows
    for players who did not bat (DNB).

    It uses the info file to:
      - Retrieve the full list of players (from info,player lines).
      - Build a registry mapping (from info,registry,people lines) to get hex codes.

    For each team and innings in the match, any player from the info file who did not bat
    is added with batting stats set to zero, isOut and wicketType marked as "DNB", and:
      - p_bat_hex is filled using the registry mapping (if available),
      - p_bowl_hex remains blank.

    **New Logic:** Before adding a DNB row for a candidate, the script checks if the candidate’s
    hex code (from the registry mapping) already appears in the batting card (in p_bat_hex).
    If it does, that candidate is skipped.
    """
    # Build the expected info file path for the match
    info_file_path = os.path.join(info_folder, f"{match_id}_info.csv")
    if not os.path.exists(info_file_path):
        print(f"Warning: Info file for match {match_id} not found. Skipping DNB processing for this match.")
        return pd.DataFrame()  # Return empty DataFrame if no info file

    # Read player list and registry mapping from the info file
    df_info = read_info_file(info_file_path)
    registry_mapping = get_registry_mapping(info_file_path)

    if df_info.empty:
        print(f"Warning: No player info found in file {info_file_path}.")
        return pd.DataFrame()

    dnb_rows = []

    # Process each group in the match, grouped by innings and team.
    groups = df_match.groupby(['innings', 'team'])
    for (innings, team), group in groups:
        # Get the set of hex codes for players who have batted in this group.
        played_hex = set(group['p_bat_hex'].dropna().unique())

        # Get all candidate players for this team (case-insensitive match on team).
        team_players = df_info[df_info['team'].str.lower() == team.lower()]['player'].unique()
        team_players = set(team_players)

        # Determine the players who did not bat.
        # Instead of comparing names, we use the registry hex code.
        for candidate in team_players:
            candidate_hex = registry_mapping.get(candidate, None)
            # If a candidate has a hex code and that hex is already in the played set, skip.
            if candidate_hex and candidate_hex in played_hex:
                continue  # Candidate already played.

            # Otherwise, add a DNB row.
            date_val = group['date'].iloc[0] if 'date' in group.columns else ""
            competition_val = group['competition'].iloc[0] if 'competition' in group.columns else ""
            row = {
                'MatchID': match_id,
                'date': date_val,
                'innings': innings,
                'team': team,
                'batsman': candidate,  # Use candidate name as provided in the info file
                'batsman_name': candidate,  # Keep the name as is
                'bowler_name': "",  # No bowler for a DNB entry
                'runs': 0,
                'balls': 0,
                'fours': 0,
                'sixes': 0,
                'strikeRate': 0,
                'isOut': "DNB",
                'wicketType': "DNB",
                'competition': competition_val,
                'p_bat_hex': candidate_hex if candidate_hex else "",  # Use hex code if available
                'p_bowl_hex': ""  # Remains blank
            }
            dnb_rows.append(row)

    return pd.DataFrame(dnb_rows)


def fill_dnb_all(batting_card_path, info_folder, output_path):
    """
    Processes the combined MBM scorecard CSV and the folder containing info files.
    For each match in the batting card, appends rows for players who did not bat.
    Saves the final DataFrame to output_path.
    """
    # Read the combined MBM scorecard CSV.
    df_batting = pd.read_csv(batting_card_path)
    df_batting.columns = [col.strip() for col in df_batting.columns]  # Clean column names

    if 'MatchID' not in df_batting.columns:
        print("Error: 'MatchID' column not found. Columns found:", df_batting.columns)
        return

    all_dnb_rows = []

    # Process each match by unique MatchID.
    for match_id in df_batting['MatchID'].unique():
        df_match = df_batting[df_batting['MatchID'] == match_id]
        df_dnb = fill_dnb_for_match(match_id, df_match, info_folder)
        if not df_dnb.empty:
            all_dnb_rows.append(df_dnb)

    if all_dnb_rows:
        df_dnb_all = pd.concat(all_dnb_rows, ignore_index=True)
    else:
        df_dnb_all = pd.DataFrame()

    # Append the DNB rows to the original batting card.
    df_final = pd.concat([df_batting, df_dnb_all], ignore_index=True)
    df_final = df_final.sort_values(by=['MatchID', 'innings', 'team'])
    df_final.to_csv(output_path, index=False)
    print(f"Output saved to: {output_path}")


def main():
    batting_card_path = input("Enter the path to the combined MBM scorecard CSV file: ").strip()
    info_folder = input("Enter the path to the folder containing info files: ").strip()
    output_path = input("Enter the desired output CSV file path (or output folder to auto-append filename): ").strip()

    if not os.path.exists(batting_card_path):
        print("Batting card file not found.")
        return
    if not os.path.exists(info_folder):
        print("Info folder not found.")
        return

    # If output_path is a directory, append a default filename.
    if os.path.isdir(output_path):
        output_path = os.path.join(output_path, "all_mbm_scorecard.csv")

    fill_dnb_all(batting_card_path, info_folder, output_path)


if __name__ == "__main__":
    main()
