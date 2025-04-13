import pandas as pd
import numpy as np
import os


# Validate the input data
def validate_columns(df):
    required_columns = [
        'match_id', 'date', 'inns', 'batter', 'batter_id', 'bat_team', 'bowl_team',
        'runs', 'balls', 'fours', 'sixes', 'sr', 'isOut', 'wicketType', 'bowler',
        'bowler_id', 'venue', 'league'
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"The following required columns are missing: {missing_columns}")


# Preprocessing the data
def preprocess_data(df):
    print("Preprocessing data...")
    # Convert dates to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Sort data chronologically
    df.sort_values(by=['date', 'inns'], inplace=True)
    
    # Extract season from date
    df['season'] = df['date'].dt.year
    
    # Handle missing or NaN values for relevant columns
    df['runs'] = df['runs'].fillna(0).astype(int)  # Assuming 'runs' column contains runs scored
    df['balls'] = df['balls'].fillna(0).astype(int)  # Assuming 'balls' column contains balls faced
    df['fours'] = df['fours'].fillna(0).astype(int)  # Assuming 'fours' column contains number of 4s
    df['sixes'] = df['sixes'].fillna(0).astype(int)  # Assuming 'sixes' column contains number of 6s
    df['isOut'] = df['isOut'].fillna(0).astype(int)  # Assuming 'isOut' is binary (1 if out, 0 if not out)
    
    # Calculate boundaries as the sum of fours and sixes
    df['boundaries'] = df['fours'] + df['sixes']
    
    print("Data preprocessing complete!")
    return df


# Calculate career statistics
def calculate_career_stats(df):
    print("Calculating career statistics...")
    df['cumulative_runs'] = df.groupby(['batter_id', 'league'])['runs'].cumsum() - df['runs']
    df['cumulative_balls'] = df.groupby(['batter_id', 'league'])['balls'].cumsum() - df['balls']
    df['cumulative_dismissals'] = df.groupby(['batter_id', 'league'])['isOut'].cumsum() - df['isOut']
    df['cum_matches'] = df.groupby(['batter_id', 'league']).cumcount()
    
    # Career metrics
    df['career_avg'] = df['cumulative_runs'] / df['cumulative_dismissals'].replace(0, np.nan)
    df['career_sr'] = (df['cumulative_runs'] / df['cumulative_balls'].replace(0, np.nan)) * 100
    df['career_rpm'] = df['cumulative_runs'] / df['cum_matches'].replace(0, np.nan)
    df['career_bpm'] = df.groupby(['batter_id', 'league'])['boundaries'].cumsum() / df['cum_matches'].replace(0, np.nan)
    df['career_bfpm'] = df['cumulative_balls'] / df['cum_matches'].replace(0, np.nan)
    
    print("Career statistics calculation complete!")
    return df


# Calculate innings-specific statistics
def calculate_innings_stats(df):
    print("Calculating innings-specific statistics (optimized)...")
    
    # Group by batter_id, league, and innings
    innings_groups = df.groupby(['batter_id', 'league', 'inns'])
    
    # Calculate cumulative metrics with proper index alignment
    df['inns_avg'] = innings_groups['runs'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)
    df['inns_sr'] = (
        innings_groups['runs'].apply(lambda x: x.shift().expanding().sum()) /
        innings_groups['balls'].apply(lambda x: x.shift().expanding().sum())
    ).reset_index(level=[0, 1, 2], drop=True) * 100
    df['inns_rpm'] = innings_groups['runs'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)
    df['inns_bpm'] = innings_groups['boundaries'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)
    df['inns_bfpm'] = innings_groups['balls'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)

    print("Innings-specific statistics calculation complete!")
    return df


def calculate_venue_stats(df):
    print("Calculating venue-specific statistics (optimized)...")
    
    # Group by batter_id, league, and venue
    venue_groups = df.groupby(['batter_id', 'league', 'venue'])
    
    # Calculate cumulative metrics with proper index alignment
    df['venue_avg'] = venue_groups['runs'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)
    df['venue_sr'] = (
        venue_groups['runs'].apply(lambda x: x.shift().expanding().sum()) /
        venue_groups['balls'].apply(lambda x: x.shift().expanding().sum())
    ).reset_index(level=[0, 1, 2], drop=True) * 100
    df['venue_rpm'] = venue_groups['runs'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)
    df['venue_bpm'] = venue_groups['boundaries'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)
    df['venue_bfpm'] = venue_groups['balls'].apply(lambda x: x.shift().expanding().mean()).reset_index(level=[0, 1, 2], drop=True)

    print("Venue-specific statistics calculation complete!")
    return df


# Calculate season-specific statistics
def calculate_season_stats(df):
    print("Calculating season-specific statistics...")
    season_groups = df.groupby(['batter_id', 'league', 'season'])
    
    df['ssn_avg'] = season_groups['runs'].transform(lambda x: x.shift().expanding().mean())
    df['ssn_sr'] = (season_groups['runs'].transform(lambda x: x.shift().expanding().sum()) / 
                    season_groups['balls'].transform(lambda x: x.shift().expanding().sum())) * 100
    df['ssn_rpm'] = season_groups['runs'].transform(lambda x: x.shift().expanding().mean())
    df['ssn_bpm'] = season_groups['boundaries'].transform(lambda x: x.shift().expanding().mean())
    df['ssn_bfpm'] = season_groups['balls'].transform(lambda x: x.shift().expanding().mean())
    
    print("Season-specific statistics calculation complete!")
    return df


# Calculate recent form statistics (last N matches)
def calculate_recent_form_stats(df, n_matches=5):
    print("Calculating recent form statistics (optimized)...")
    
    # Ensure data is sorted by batter_id and date
    df = df.sort_values(by=['batter_id', 'date'])
    
    # Group by batter_id
    grouped = df.groupby('batter_id', group_keys=False)
    
    # Calculate rolling metrics for the last N matches
    df['last5_avg'] = grouped['runs'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).mean())
    df['last5_sr'] = (grouped['runs'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).sum()) /
                      grouped['balls'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).sum()) * 100)
    df['last5_rpm'] = grouped['runs'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).mean())
    df['last5_bpm'] = grouped['boundaries'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).mean())
    df['last5_bfpm'] = grouped['balls'].apply(lambda x: x.shift(1).rolling(window=n_matches, min_periods=1).mean())

    print("Recent form statistics calculation complete!")
    return df


# Data cleanup for NULL and infinite values
def cleanup_data(df):
    print("Cleaning up data (handling NaN and Infinite values)...")
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)
    print("Data cleanup complete!")
    return df


# Main function to process the data
def process_batting_data(df):
    print("Starting batting data processing...")
    df = preprocess_data(df)
    df = calculate_career_stats(df)
    df = calculate_innings_stats(df)
    df = calculate_venue_stats(df)
    df = calculate_season_stats(df)
    df = calculate_recent_form_stats(df, n_matches=5)  # Add recent form stats calculation
    df = cleanup_data(df)
    print("Batting data processing complete!")
    return df


# Example usage
if __name__ == "__main__":
    input_file = os.path.join('data', 'mbm', 'all_league', 'all_league_bat_final.csv')
    output_file = os.path.join('scripts', 'processed_batting_data.csv')

    try:
        print(f"Loading input file: {input_file}")
        df = pd.read_csv(input_file)
        print(f"Input file loaded successfully. Number of rows: {len(df)}")
        
        # Validate columns
        validate_columns(df)
        
        # Process data
        processed_df = process_batting_data(df)
        
        # Save the processed data
        print(f"Saving the processed data to: {output_file}")
        processed_df.to_csv(output_file, index=False)
        print(f"Processed data saved to: {output_file}")
    except FileNotFoundError:
        print(f"Error: File not found at {input_file}")
    except ValueError as e:
        print(f"Validation Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")