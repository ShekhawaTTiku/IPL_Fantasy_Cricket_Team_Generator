import pandas as pd
import csv
import os


def process_batting_scorecard(ball_by_ball_file, competition):
    """Process ball-by-ball data into batting scorecard format."""
    # Read ball-by-ball data
    df = pd.read_csv(ball_by_ball_file)

    # Apply filtering only if the user did not input "." (which means no filtering)
    if 'competition' in df.columns and competition and competition != '.':
        df = df[df['competition'].str.lower() == competition.lower()]

    # If no rows match after filtering, return an empty DataFrame
    if df.empty:
        return pd.DataFrame()

    # Determine the competition value for output.
    # If the user input is "." and the CSV has a competition column, use its actual value.
    if competition == '.' and 'competition' in df.columns:
        output_competition = df['competition'].iloc[0]
    else:
        output_competition = competition

    # If the date column exists, capture the match date (assuming all rows share the same date)
    if 'date' in df.columns:
        match_date = df['date'].iloc[0]
    else:
        match_date = ""

    # Initialize batting statistics
    batting_stats = {}

    # Process each ball
    for _, ball in df.iterrows():
        striker = ball['p_bat']  # Player ID of the batsman
        batsman_name = ball['bat']  # Actual batsman name
        bowler_name = ball['bowl']  # Actual bowler name
        batting_team = ball['team_bat']
        match_id = ball['p_match']  # Get the match ID

        # Update statistics for the specific match and player
        stats = batting_stats.get((match_id, batting_team, striker), {
            'batsman_name': batsman_name,
            'bowler_name': bowler_name,
            'runs': 0,
            'balls': 0,
            'fours': 0,
            'sixes': 0,
            'isOut': False,
            'wicketType': '',
            'innings': ball['inns']
        })

        # Update runs and balls
        runs = ball['batruns']
        stats['balls'] += 1
        stats['runs'] += runs

        # Count boundaries based on the score column
        score = ball['batruns']
        if score == 4:
            stats['fours'] += 1
        elif score == 6:
            stats['sixes'] += 1
        elif score == 5:
            stats['fours'] += 1  # Count as a four with an extra wide

        # Check for wicket
        out_status = str(ball['out']).strip().upper()  # Normalize to uppercase
        dismissed_player = str(ball['p_out']).strip()  # Ensure it's treated as a string

        if out_status == 'TRUE' and dismissed_player == str(striker):
            stats['isOut'] = True
            stats['wicketType'] = str(ball['dismissal']).strip()  # Use the dismissal type directly
            stats['bowler_name'] = bowler_name  # Update the bowler who got the wicket

        # Save the updated stats back to the dictionary
        batting_stats[(match_id, batting_team, striker)] = stats

    # Create results DataFrame
    results = []
    for (match_id, team, player), stats in batting_stats.items():
        strike_rate = (stats['runs'] / stats['balls'] * 100) if stats['balls'] > 0 else 0
        results.append({
            'MatchID': match_id,
            'date': match_date,  # New date column added
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
            'competition': output_competition  # Use the appropriate competition value
        })

    return pd.DataFrame(results)


def process_all_matches(path, competition):
    """Process matches from a given folder or a single CSV file."""
    # If the provided path is a file, process it directly.
    if os.path.isfile(path):
        print(f"Processing single file: {os.path.basename(path)}")
        scorecard = process_batting_scorecard(path, competition)
        return scorecard

    # Otherwise, assume it's a folder and process all CSV files within it.
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
                # Only append if the scorecard has rows (i.e. the file contained relevant data)
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


def main():
    input_path = input("Enter the path to a CSV file or a folder containing match files: ").strip()
    competition = input("Enter the competition name (or enter '.' for all matches): ").strip()

    if not os.path.exists(input_path):
        print("Error: Path not found!")
        return

    print("Starting to process matches...")
    combined_scorecard = process_all_matches(input_path, competition)

    if combined_scorecard is not None and not combined_scorecard.empty:
        # Set output file name based on competition input.
        if competition == '.':
            output_filename = "all_mbm_scorecard.csv"
        else:
            output_filename = f"{competition}_mbm_scorecard.csv"
        # Determine output folder: if processing a file, use its directory; otherwise, use the folder path.
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
