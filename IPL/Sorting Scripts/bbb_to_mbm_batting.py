import pandas as pd
import csv
import os


def process_batting_scorecard(ball_by_ball_file):
    """Process ball-by-ball data into batting scorecard format."""
    # Read ball-by-ball data
    df = pd.read_csv(ball_by_ball_file)

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

    # Process each player who batted
    for (match_id, team, player), stats in batting_stats.items():
        strike_rate = (stats['runs'] / stats['balls'] * 100) if stats['balls'] > 0 else 0

        results.append({
            'MatchID': match_id,
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
            'wicketType': stats['wicketType'] if stats['isOut'] else 'not out'
        })

    return pd.DataFrame(results)


def process_all_matches(folder_path):
    """Process all matches in the specified folder."""
    # Get all CSV files in the folder
    all_files = os.listdir(folder_path)

    # Find match files (excluding _info files)
    match_files = [f for f in all_files if f.endswith('.csv')]

    # Initialize list to store all scorecards
    all_scorecards = []

    # Process each match
    total_matches = len(match_files)
    for idx, match_file in enumerate(match_files, 1):
        try:
            # Extract match ID from filename
            match_id = match_file.replace('.csv', '')

            # Construct file path
            match_path = os.path.join(folder_path, match_file)

            # Process match
            print(f"Processing match {idx}/{total_matches}: {match_id}")
            scorecard = process_batting_scorecard(match_path)
            all_scorecards.append(scorecard)

        except Exception as e:
            print(f"Error processing match {match_id}: {str(e)}")
            continue

    # Combine all scorecards
    if all_scorecards:
        combined_scorecard = pd.concat(all_scorecards, ignore_index=True)
        return combined_scorecard
    else:
        return None


def main():
    # Get folder path from user
    folder_path = input("Enter the path to the folder containing match files: ").strip()

    # Verify folder exists
    if not os.path.exists(folder_path):
        print("Error: Folder not found!")
        return

    print("Starting to process matches...")
    combined_scorecard = process_all_matches(folder_path)

    if combined_scorecard is not None:
        # Save to CSV
        output_file = os.path.join(folder_path, "all_matches_scorecard.csv")
        combined_scorecard.to_csv(output_file, index=False)
        print(f"\nProcessing complete!")
        print(f"Total matches processed: {len(combined_scorecard['MatchID'].unique())}")
        print(f"Output saved to: {output_file}")
    else:
        print("No matches were processed successfully")


if __name__ == "__main__":
    main()
