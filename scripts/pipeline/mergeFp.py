import os
import pandas as pd

def merge_fantasy_predictions(match_number):
    """
    Merge batting and bowling fantasy point predictions for a specific match.
    
    This function:
    1. Reads the batting and bowling prediction CSVs for a given match number
    2. Merges them based on player_id
    3. Creates a final_fp column that sums the generated_fp from both sources
    4. Maps player names from squadData_ipl25.csv using key_cricinfo as player_id
    5. Saves the merged result to a new CSV in fp_predictor_merged folder
    """
    
    # Define directories
    source_dir = r"D:\App\FIFS_IPL\fp_predictor"
    target_dir = r"D:\App\FIFS_IPL\fp_predictor_merged"
    squad_data_path=r"D:\App\FIFS_IPL\data\register_data\squadData_ipl25.csv"
    
    # Create target directory if it doesn't exist
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")
    else:
        print(f"Target directory already exists: {target_dir}")
    
    # Define file paths
    batting_file = os.path.join(source_dir, f"predicted_bat_{match_number}.csv")
    bowling_file = os.path.join(source_dir, f"predicted_bowl_{match_number}.csv")
    output_file = os.path.join(target_dir, f"predicted_merged_{match_number}.csv")
    
    # Check if source files exist
    if not os.path.exists(batting_file):
        print(f"ERROR: Batting predictions file not found: {batting_file}")
        return
    
    if not os.path.exists(bowling_file):
        print(f"ERROR: Bowling predictions file not found: {bowling_file}")
        return
    
    try:
        # Read the CSV files
        print(f"Reading batting predictions from {batting_file}")
        batting_df = pd.read_csv(batting_file)
        
        print(f"Reading bowling predictions from {bowling_file}")
        bowling_df = pd.read_csv(bowling_file)
        
        # Read squad data file to get player names
        print(f"Reading squad data from {squad_data_path}")
        squad_df = pd.read_csv(squad_data_path)
        
        # Create a mapping from key_cricinfo (player_id) to dream11_name (player name)
        # Convert key_cricinfo to string to match the player_id datatype in prediction files
        squad_df['key_cricinfo'] = squad_df['key_cricinfo'].astype(str)
        player_name_map = dict(zip(squad_df['key_cricinfo'], squad_df['dream11_name']))
        
        print(f"Created player name mapping for {len(player_name_map)} players")
        
        # Check for expected columns
        if 'player id' not in batting_df.columns or 'generated_fp' not in batting_df.columns:
            print(f"ERROR: Batting file is missing required columns. Found: {batting_df.columns.tolist()}")
            return
            
        if 'player id' not in bowling_df.columns or 'generated_fp' not in bowling_df.columns:
            print(f"ERROR: Bowling file is missing required columns. Found: {bowling_df.columns.tolist()}")
            return
        
        # Create a merged dataframe
        print("Merging batting and bowling data")
        
        # Initialize the merged dataframe with all player IDs
        all_players = pd.concat([
            batting_df[['player id']],
            bowling_df[['player id']]
        ]).drop_duplicates()
        
        # Convert player id to string to match with key_cricinfo
        all_players['player id'] = all_players['player id'].astype(str)
        
        # Add player name column based on mapping
        all_players['player name'] = all_players['player id'].map(player_name_map)
        
        # For any players not found in the mapping, set name to "Unknown"
        all_players['player name'] = all_players['player name'].fillna("Unknown")
        
        # Rename columns for clarity in the merge
        batting_df = batting_df.rename(columns={'generated_fp': 'batting_fp'})
        bowling_df = bowling_df.rename(columns={'generated_fp': 'bowling_fp'})
        
        # Convert player id to string in batting and bowling dataframes
        batting_df['player id'] = batting_df['player id'].astype(str)
        bowling_df['player id'] = bowling_df['player id'].astype(str)
        
        # Merge batting data
        merged_df = pd.merge(
            all_players,
            batting_df[['player id', 'batting_fp']],
            on='player id',
            how='left'
        )
        
        # Merge bowling data
        merged_df = pd.merge(
            merged_df,
            bowling_df[['player id', 'bowling_fp']],
            on='player id',
            how='left'
        )
        
        # Fill NaN values with 0 (players who are only batters or only bowlers)
        merged_df['batting_fp'] = merged_df['batting_fp'].fillna(0)
        merged_df['bowling_fp'] = merged_df['bowling_fp'].fillna(0)
        
        # Calculate final fantasy points
        merged_df['final_fp'] = merged_df['batting_fp'] + merged_df['bowling_fp']
        
        # Reorder columns to have player name first, then id, then fantasy points
        merged_df = merged_df[['player name', 'player id', 'batting_fp', 'bowling_fp', 'final_fp']]
        
        # Save to CSV
        print(f"Saving merged predictions to {output_file}")
        merged_df.to_csv(output_file, index=False)
        
        # Print summary
        print(f"Successfully merged predictions for match {match_number}")
        print(f"Total players: {len(merged_df)}")
        print(f"Players with batting points: {(merged_df['batting_fp'] != None).sum()}")
        print(f"Players with bowling points: {(merged_df['bowling_fp'] != None).sum()}")
        print(f"Players with both batting and bowling points: {((merged_df['batting_fp'] > 0) & (merged_df['bowling_fp'] > 0)).sum()}")
        print(f"Players with mapped names: {(merged_df['player name'] != 'Unknown').sum()}")
        
    except Exception as e:
        print(f"ERROR: Failed to merge predictions: {str(e)}")
        import traceback
        traceback.print_exc()