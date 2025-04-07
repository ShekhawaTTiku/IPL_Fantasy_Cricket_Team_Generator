import os
import pandas as pd
import glob

def update_player_ids():
    """
    Match player names between squadData_ipl25.csv and player details CSV files.
    Update the key_crickbuzz column with matching Player IDs.
    """
    # Load squad data with the correct path
    squad_data_path = 'data/register_data/squadData_ipl25.csv'
    squad_data = pd.read_csv(squad_data_path)
    
    # Print column names to debug
    print("Columns in squadData_ipl25.csv:", squad_data.columns.tolist())
    
    # Initialize a dictionary to store player name to ID mappings
    player_id_map = {}
    
    # Path to the folder containing player details CSV files
    player_files_path = 'Today_Match_Details/'
    
    # Get all CSV files in the player details folder
    player_files = glob.glob(os.path.join(player_files_path, '*.csv'))
    
    print(f"Found {len(player_files)} player data files")
    
    # Process each player file
    for file in player_files:
        try:
            # Read the player data file
            player_data = pd.read_csv(file)
            
            # Print column names of the first file to debug
            if player_files.index(file) == 0:
                print(f"Columns in {os.path.basename(file)}:", player_data.columns.tolist())
            
            # Check if the file has the required columns - adapt this based on your actual column names
            # This part may need adjustment based on the actual column names in your files
            name_column = next((col for col in player_data.columns if 'name' in col.lower()), None)
            id_column = next((col for col in player_data.columns if 'id' in col.lower()), None)
            
            if name_column and id_column:
                # Extract player name and ID
                for _, row in player_data.iterrows():
                    player_name = str(row[name_column]).strip()
                    player_id = row[id_column]
                    
                    # Store in the mapping dictionary
                    player_id_map[player_name] = player_id
                    
                print(f"Processed {os.path.basename(file)} with columns: {name_column} and {id_column}")
            else:
                print(f"Required columns not found in {os.path.basename(file)}")
        except Exception as e:
            print(f"Error processing file {file}: {e}")
    
    print(f"Created mapping for {len(player_id_map)} players")
    
    # Function to find the best match for a player name
    def find_id_for_player(name):
        # Direct match
        if name in player_id_map:
            return player_id_map[name]
        
        # Try without initials (for cases like "MS Dhoni" vs "Dhoni")
        last_name = name.split()[-1]
        for player_name, player_id in player_id_map.items():
            if player_name.endswith(last_name):
                return player_id
        
        # No match found
        return None
    
    # Find the correct column name for cricbuzz_name and key_cricbuzz
    name_col = 'cricbuzz_name'
    key_col = 'key_cricbuzz'
    
    if name_col not in squad_data.columns:
        print(f"Column '{name_col}' not found. Available columns: {squad_data.columns.tolist()}")
        return
    
    if key_col not in squad_data.columns:
        print(f"Column '{key_col}' not found. Available columns: {squad_data.columns.tolist()}")
        return
    
    # Update the key_cricbuzz column in squad data
    updated_count = 0
    for idx, row in squad_data.iterrows():
        player_name = row[name_col]
        
        # Get the current value in the key_cricbuzz column
        current_value = row[key_col]
        
        # Only update if the field is currently empty or NaN
        if pd.isna(current_value) or current_value == '' or current_value == 0:
            player_id = find_id_for_player(player_name)
            if player_id is not None:
                squad_data.at[idx, key_col] = player_id
                updated_count += 1
                print(f"Updated {player_name} with ID: {player_id}")
    
    # Save the updated data
    updated_file_path = 'data/register_data/squadData_ipl25_updated2.csv'
    squad_data.to_csv(updated_file_path, index=False)
    
    print(f"Updated {updated_count} player IDs in squadData_ipl25.csv")
    print(f"Updated file saved as {updated_file_path}")

if __name__ == "__main__":
    update_player_ids()