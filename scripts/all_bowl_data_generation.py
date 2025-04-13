import pandas as pd
import numpy as np
import os


# Preprocessing the data
def preprocess_data(df):
    print("Preprocessing data...")
    # Convert dates to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort data chronologically
    df.sort_values(by=['date', 'inns'], inplace=True)
    
    # Extract season from date
    df['season'] = df['date'].dt.year
    
    # Handle 'DNB' (Did Not Bowl) entries
    df['overs'] = df['overs'].replace('DNB', '0.0')
    
    # Split overs into whole overs and remaining balls
    df[['overs_int', 'balls_int']] = df['overs'].astype(str).str.split('.', expand=True).astype(int)
    
    # Calculate total balls and overs
    df['total_balls'] = df['overs_int'] * 6 + df['balls_int']
    df['total_overs'] = df['total_balls'] / 6
    
    print("Data preprocessing complete!")
    return df


# Calculate career statistics
def calculate_career_stats(df):
    print("Calculating career statistics...")
    df['cumulative_runs'] = df.groupby(['bowler_id', 'league'])['runs'].cumsum() - df['runs']
    df['cumulative_wickets'] = df.groupby(['bowler_id', 'league'])['wickets'].cumsum() - df['wickets']
    df['cumulative_balls'] = df.groupby(['bowler_id', 'league'])['total_balls'].cumsum() - df['total_balls']
    df['cum_matches'] = df.groupby(['bowler_id', 'league']).cumcount()
    
    # Career metrics
    df['career_avg'] = df['cumulative_runs'] / df['cumulative_wickets']
    df['career_eco'] = df['cumulative_runs'] / (df['cumulative_balls'] / 6)
    df['career_sr'] = df['cumulative_balls'] / df['cumulative_wickets']
    df['career_wpm'] = df['cumulative_wickets'] / df['cum_matches']
    df['career_opm'] = (df['cumulative_balls'] / 6) / df['cum_matches']
    
    print("Career statistics calculation complete!")
    return df


# Calculate innings-specific statistics
def calculate_innings_stats(df):
    print("Calculating innings-specific statistics...")
    
    # Group by bowler_id, league, and inns
    innings_groups = df.groupby(['bowler_id', 'league', 'inns'])
    
    # Compute cumulative sums for metrics
    cumulative_runs = innings_groups['runs'].cumsum()
    cumulative_wickets = innings_groups['wickets'].cumsum()
    cumulative_balls = innings_groups['total_balls'].cumsum()
    matches_played = innings_groups.cumcount()

    # Calculate innings-specific statistics
    df['inns_avg'] = (cumulative_runs - df['runs']) / (cumulative_wickets - df['wickets']).replace(0, np.nan)
    df['inns_eco'] = (cumulative_runs - df['runs']) / ((cumulative_balls - df['total_balls']) / 6)
    df['inns_sr'] = (cumulative_balls - df['total_balls']) / (cumulative_wickets - df['wickets']).replace(0, np.nan)
    df['inns_wpm'] = (cumulative_wickets - df['wickets']) / matches_played.replace(0, np.nan)
    df['inns_opm'] = ((cumulative_balls - df['total_balls']) / 6) / matches_played.replace(0, np.nan)
    
    print("Innings-specific statistics calculation complete!")
    return df


# Calculate venue-specific statistics
def calculate_venue_stats(df):
    print("Calculating venue-specific statistics...")

    # Group by bowler_id, league, and venue
    venue_groups = df.groupby(['bowler_id', 'league', 'venue'])

    # Compute cumulative sums for metrics
    cumulative_runs = venue_groups['runs'].cumsum()
    cumulative_wickets = venue_groups['wickets'].cumsum()
    cumulative_balls = venue_groups['total_balls'].cumsum()
    matches_played = venue_groups.cumcount()

    # Calculate venue-specific statistics
    df['venue_avg'] = (cumulative_runs - df['runs']) / (cumulative_wickets - df['wickets']).replace(0, np.nan)
    df['venue_eco'] = (cumulative_runs - df['runs']) / ((cumulative_balls - df['total_balls']) / 6)
    df['venue_sr'] = (cumulative_balls - df['total_balls']) / (cumulative_wickets - df['wickets']).replace(0, np.nan)
    df['venue_wpm'] = (cumulative_wickets - df['wickets']) / matches_played.replace(0, np.nan)
    df['venue_opm'] = ((cumulative_balls - df['total_balls']) / 6) / matches_played.replace(0, np.nan)

    print("Venue-specific statistics calculation complete!")
    return df


# Calculate season-specific statistics
def calculate_season_stats(df):
    print("Calculating season-specific statistics...")

    # Group by bowler_id, league, and season
    season_groups = df.groupby(['bowler_id', 'league', 'season'])

    # Compute cumulative sums for metrics
    cumulative_runs = season_groups['runs'].cumsum()
    cumulative_wickets = season_groups['wickets'].cumsum()
    cumulative_balls = season_groups['total_balls'].cumsum()
    matches_played = season_groups.cumcount()

    # Calculate season-specific statistics
    df['ssn_avg'] = (cumulative_runs - df['runs']) / (cumulative_wickets - df['wickets']).replace(0, np.nan)
    df['ssn_eco'] = (cumulative_runs - df['runs']) / ((cumulative_balls - df['total_balls']) / 6)
    df['ssn_sr'] = (cumulative_balls - df['total_balls']) / (cumulative_wickets - df['wickets']).replace(0, np.nan)
    df['ssn_wpm'] = (cumulative_wickets - df['wickets']) / matches_played.replace(0, np.nan)
    df['ssn_opm'] = ((cumulative_balls - df['total_balls']) / 6) / matches_played.replace(0, np.nan)

    print("Season-specific statistics calculation complete!")
    return df


# Calculate recent form statistics (last N matches)
def calculate_recent_form_stats(df, n_matches=5):
    print("Calculating recent form statistics (optimized)...")
    
    # Ensure data is sorted by bowler_id and date
    df = df.sort_values(by=['bowler_id', 'date'])
    
    # Rolling metrics
    grouped = df.groupby('bowler_id', group_keys=False)
    
    # Calculate rolling averages and totals for the last N matches
    df['last5_avg'] = grouped['runs'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).mean())
    df['last5_eco'] = grouped.apply(
        lambda group: (group['runs'].shift(1).rolling(window=n_matches, min_periods=1).sum()) /
                      ((group['total_balls'].shift(1).rolling(window=n_matches, min_periods=1).sum()) / 6)
    ).reset_index(level=0, drop=True)
    df['last5_sr'] = grouped.apply(
        lambda group: (group['total_balls'].shift(1).rolling(window=n_matches, min_periods=1).sum()) /
                      (group['wickets'].shift(1).rolling(window=n_matches, min_periods=1).sum().replace(0, np.nan))
    ).reset_index(level=0, drop=True)
    df['last5_wpm'] = grouped['wickets'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).mean())
    df['last5_opm'] = grouped.apply(
        lambda group: (group['total_balls'].shift(1).rolling(window=n_matches, min_periods=1).sum() / 6) /
                      n_matches
    ).reset_index(level=0, drop=True)
    
    print("Recent form statistics calculation complete!")
    return df


# Data cleanup for NULL and infinite values
def cleanup_data(df):
    print("Cleaning up data (handling NaN and Infinite values)...")
    for col in ['career_avg', 'career_eco', 'career_sr', 'inns_avg', 'inns_eco', 'inns_sr', 
                'venue_avg', 'venue_eco', 'venue_sr', 'ssn_avg', 'ssn_eco', 'ssn_sr',
                'last5_avg', 'last5_eco', 'last5_sr']:
        df[col] = df[col].replace([np.inf, -np.inf], 0.0)
        df[col] = df[col].fillna(0)
    
    # Mark first occurrences NULL
    for col in ['career_avg', 'career_eco', 'career_sr', 'career_wpm', 'career_opm']:
        df.loc[df.groupby(['bowler_id', 'league']).head(1).index, col] = pd.NA
    
    print("Data cleanup complete!")
    return df


# Main function to process the data
def process_bowling_data(df):
    print("Starting bowling data processing...")
    df = preprocess_data(df)
    df = calculate_career_stats(df)
    df = calculate_innings_stats(df)
    df = calculate_venue_stats(df)
    df = calculate_season_stats(df)
    df = calculate_recent_form_stats(df)
    df = cleanup_data(df)
    print("Bowling data processing complete!")
    return df


# Example usage
if __name__ == "__main__":
    input_file = 'data/mbm/all_league/all_league_bowl_final.csv'
    output_file = 'scripts/processed_bowling_data.csv'

    print(f"Loading input file: {input_file}")
    try:
        df = pd.read_csv(input_file)
        print(f"Input file loaded successfully. Number of rows: {len(df)}")
        
        # Process data
        processed_df = process_bowling_data(df)
        
        # Save the processed data
        print(f"Saving the processed data to: {output_file}")
        processed_df.to_csv(output_file, index=False)
        print(f"File saved successfully to: {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")