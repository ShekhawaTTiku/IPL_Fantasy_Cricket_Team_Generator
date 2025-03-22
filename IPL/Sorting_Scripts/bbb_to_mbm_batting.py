import pandas as pd
import csv
import os

# -------------------------------------------------------------------------
# Global: Load people mapping from people.csv
# -------------------------------------------------------------------------
PEOPLE_FILE = r"D:\ED\FIFS_IPL\data\people.csv"
try:
    df_people = pd.read_csv(PEOPLE_FILE)
    # Drop rows where key_cricinfo is NaN and convert key_cricinfo to numeric
    df_people_valid = df_people.dropna(subset=['key_cricinfo'])
    df_people_valid['key_cricinfo'] = pd.to_numeric(df_people_valid['key_cricinfo'], errors='coerce')
    # Create mapping dictionary: key (numeric) -> identifier (as is)
    people_mapping = df_people_valid.set_index('key_cricinfo')['identifier'].to_dict()
except Exception as e:
    print("Error loading people.csv:", e)
    people_mapping = {}

# -------------------------------------------------------------------------
# Process a single ball-by-ball file into a batting scorecard format.
# This function now also adds p_bat_hex and p_bowl_hex columns.
# -------------------------------------------------------------------------
def process_batting_scorecard(ball_by_ball_file, competition):
    """Process ball-by-ball data into batting scorecard format."""
    # Read ball-by-ball data
    df = pd.read_csv(ball_by_ball_file)

    # Filter by competition if needed (if user didn't input ".")
    if 'competition' in df.columns and competition and competition != '.':
        df = df[df['competition'].str.lower() == competition.lower()]

    # If no rows match after filtering, return an empty DataFrame
    if df.empty:
        return pd.DataFrame()

    # Determine the competition value for output.
    if competition == '.' and 'competition' in df.columns:
        output_competition = df['competition'].iloc[0]
    else:
        output_competition = competition

    # Capture the match date (assuming all rows share the same date)
    match_date = df['date'].iloc[0] if 'date' in df.columns else ""

    # Initialize batting statistics dictionary.
    # The key is a tuple: (match_id, batting_team, striker)
    batting_stats = {}

    # Process each ball in the DataFrame.
    for _, ball in df.iterrows():
        # Convert p_bat and p_bowl values to numeric for matching.
        striker = pd.to_numeric(ball['p_bat'], errors='coerce')
        # p_bowl might be NaN or missing in some rows, so convert it similarly.
        bowler_id = pd.to_numeric(ball['p_bowl'], errors='coerce') if 'p_bowl' in ball else None

        batsman_name = ball['bat']     # Batsman's name
        bowler_name = ball['bowl']       # Bowler's name
        batting_team = ball['team_bat']  # Batting team name
        match_id = ball['p_match']       # Match ID

        key = (match_id, batting_team, striker)
        if key not in batting_stats:
            # Initialize statistics with extra fields for mapping.
            batting_stats[key] = {
                'batsman_name': batsman_name,
                'bowler_name': bowler_name,
                'runs': 0,
                'balls': 0,
                'fours': 0,
                'sixes': 0,
                'isOut': False,
                'wicketType': '',
                'innings': ball['inns'],
                'p_bat_id': striker,  # store the raw striker id
                'p_bowl_id': bowler_id  # store the bowler id (will update if wicket falls)
            }
        stats = batting_stats[key]

        # Update runs and balls faced.
        runs = ball['batruns']
        stats['balls'] += 1
        stats['runs'] += runs

        # Count boundaries (using batruns field)
        score = ball['batruns']
        if score == 4:
            stats['fours'] += 1
        elif score == 6:
            stats['sixes'] += 1
        elif score == 5:
            stats['fours'] += 1  # Count a 5 as a four (with an extra wide)

        # Check if the batsman is dismissed on this ball.
        out_status = str(ball['out']).strip().upper()  # Normalize
        dismissed_player = str(ball['p_out']).strip()
        if out_status == 'TRUE' and dismissed_player == str(striker):
            stats['isOut'] = True
            stats['wicketType'] = str(ball['dismissal']).strip()
            stats['bowler_name'] = bowler_name
            # Update bowler id to the one who took the wicket.
            stats['p_bowl_id'] = bowler_id

        batting_stats[key] = stats

    # Create results DataFrame with the aggregated stats.
    results = []
    for (match_id, team, player), stats in batting_stats.items():
        strike_rate = (stats['runs'] / stats['balls'] * 100) if stats['balls'] > 0 else 0
        # Map the p_bat and p_bowl ids using the people_mapping dictionary.
        p_bat_hex = people_mapping.get(stats['p_bat_id'], '')
        p_bowl_hex = people_mapping.get(stats['p_bowl_id'], '')
        results.append({
            'MatchID': match_id,
            'date': match_date,
            'innings': stats['innings'],
            'team': team,
            'batsman': player,
            'batsman_name': stats['batsman_name'],
            'bowler_name': stats['bowler_name'],
            'runs': stats['runs'],
            'balls': stats['balls'],
            'fours': stats['fours'],
            'sixes': stats['sixes'],
            'strikeRate': round(strike_rate, 2),
            'isOut': stats['isOut'],
            'wicketType': stats['wicketType'] if stats['isOut'] else 'not out',
            'competition': output_competition,
            'p_bat_hex': p_bat_hex,
            'p_bowl_hex': p_bowl_hex
        })

    return pd.DataFrame(results)


# -------------------------------------------------------------------------
# Process all matches from a folder or a single file.
# -------------------------------------------------------------------------
def process_all_matches(path, competition):
    """Process matches from a given folder or a single CSV file."""
    if os.path.isfile(path):
        print(f"Processing single file: {os.path.basename(path)}")
        scorecard = process_batting_scorecard(path, competition)
        return scorecard

    elif os.path.isdir(path):
        all_files = os.listdir(path)
        match_files = [f for f in all_files if f.endswith('.csv')]
        all_scorecards = []
        total_matches = len(match_files)
        for idx, match_file in enumerate(match_files, 1):
            try:
                match_id = match_file.replace('.csv', '')
                match_path = os.path.join(path, match_file)
                print(f"Processing match {idx}/{total_matches}: {match_id}")
                scorecard = process_batting_scorecard(match_path, competition)
                if not scorecard.empty:
                    all_scorecards.append(scorecard)
            except Exception as e:
                print(f"Error processing match {match_id}: {str(e)}")
                continue

        if all_scorecards:
            combined_scorecard = pd.concat(all_scorecards, ignore_index=True)
            return combined_scorecard
        else:
            return None
    else:
        print("Provided path is neither a file nor a folder.")
        return None


# -------------------------------------------------------------------------
# Main function to run the processing.
# -------------------------------------------------------------------------
def main():
    input_path = input("Enter the path to a CSV file or a folder containing match files: ").strip()
    competition = input("Enter the competition name (or enter '.' for all matches): ").strip()

    if not os.path.exists(input_path):
        print("Error: Path not found!")
        return

    print("Starting to process matches...")
    combined_scorecard = process_all_matches(input_path, competition)

    if combined_scorecard is not None and not combined_scorecard.empty:
        if competition == '.':
            output_filename = "all_mbm_scorecard.csv"
        else:
            output_filename = f"{competition}_mbm_scorecard.csv"
        if os.path.isfile(input_path):
            output_file = os.path.join(os.path.dirname(input_path), output_filename)
        else:
            output_file = os.path.join(input_path, output_filename)
        combined_scorecard.to_csv(output_file, index=False)
        print("\nProcessing complete!")
        if 'MatchID' in combined_scorecard.columns:
            print(f"Total matches processed: {len(combined_scorecard['MatchID'].unique())}")
        else:
            print("Processed scorecard from a single file")
        print(f"Output saved to: {output_file}")
    else:
        print("No matches were processed successfully")


if __name__ == "__main__":
    main()
