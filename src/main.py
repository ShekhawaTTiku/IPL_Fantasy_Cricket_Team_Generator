#!/usr/bin/env python3
import pandas as pd
import os


def process_batting_scorecard(ball_by_ball_file):
    """
    Process the ball-by-ball CSV file and aggregate batting data
    to create a match-by-match batting card.
    """
    df = pd.read_csv(ball_by_ball_file)
    batting_stats = {}

    # Iterate through each ball record
    for _, ball in df.iterrows():
        # Create a key based on match id, innings, batting team, and batsman
        key = (ball['p_match'], ball['inns'], ball['team_bat'], ball['bat'])
        if key not in batting_stats:
            batting_stats[key] = {
                'runs': 0,
                'balls': 0,
                'fours': 0,
                'sixes': 0,
                'isOut': False,
                'wicketType': '',
                'fielders': [],  # Empty for now
                'bowler': '',
                'innings': ball['inns']
            }
        stats = batting_stats[key]

        # Count each ball faced
        stats['balls'] += 1

        # Aggregate runs using 'cur_bat_runs'
        try:
            runs = float(ball['cur_bat_runs'])
        except (ValueError, TypeError):
            runs = 0
        stats['runs'] += runs

        # Count boundaries
        if runs == 4:
            stats['fours'] += 1
        elif runs == 6:
            stats['sixes'] += 1

        # Check if the batsman got out (using the 'dismissal' column)
        if pd.notna(ball['dismissal']) and str(ball['dismissal']).strip() != "":
            stats['isOut'] = True
            stats['wicketType'] = ball['dismissal']
            # Record the bowler if not already set
            if stats['bowler'] == '':
                stats['bowler'] = ball['bowl']

    # Retrieve match-level metadata from the first row of the CSV
    match_id = df['p_match'].iloc[0]
    match_date = df['date'].iloc[0]
    match_venue = df['ground'].iloc[0]

    # Prepare the aggregated results
    results = []
    for key, stats in batting_stats.items():
        (match_id_key, innings, team, batsman) = key
        strike_rate = (stats['runs'] / stats['balls'] * 100) if stats['balls'] > 0 else 0
        results.append({
            'MatchID': match_id_key,
            'Date': match_date,
            'Venue': match_venue,
            'innings': innings,
            'team': team,
            'batsman': batsman,
            'runs': stats['runs'],
            'balls': stats['balls'],
            'fours': stats['fours'],
            'sixes': stats['sixes'],
            'strikeRate': round(strike_rate, 2),
            'isOut': stats['isOut'],
            'wicketType': stats['wicketType'] if stats['isOut'] else '',
            'fielders': stats['fielders'],
            'bowler': stats['bowler']
        })

    return pd.DataFrame(results)


def main():
    # Hardcoded input file path
    ball_by_ball_file = r"D:\ED\FIFS_IPL\data\t20_bbb_filtered.csv"

    if not os.path.exists(ball_by_ball_file):
        print(f"File not found: {ball_by_ball_file}")
        return

    batting_scorecard = process_batting_scorecard(ball_by_ball_file)

    # Hardcoded output file path
    output_file = r"D:\ED\FIFS_IPL\data\match_batting_scorecard.csv"
    batting_scorecard.to_csv(output_file, index=False)
    print(f"Match batting scorecard saved to: {output_file}")


if __name__ == "__main__":
    main()
