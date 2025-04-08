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
            
            # Check if the file has the required columns
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
    
    # Create a structured version of player data for better matching
    structured_player_data = []
    for name, player_id in player_id_map.items():
        parts = name.split()
        if len(parts) >= 2:
            first_name = " ".join(parts[:-1])  # Everything except last name
            last_name = parts[-1]              # Last name
            structured_player_data.append({
                'full_name': name,
                'first_name': first_name,
                'last_name': last_name,
                'id': player_id
            })
        else:
            # For single name players
            structured_player_data.append({
                'full_name': name,
                'first_name': name,
                'last_name': name,
                'id': player_id
            })
    
    # Function to find the best match for a player name
    def find_id_for_player(name):
        # Direct match
        if name in player_id_map:
            return player_id_map[name]
        
        # Process the name
        name_parts = name.split()
        if len(name_parts) < 2:
            # For single name, try exact match only
            return None
            
        # Extract first and last name components
        last_name = name_parts[-1]
        
        # Check for initials 
        if len(name_parts) >= 2:
            # If the name has format like "MS Dhoni", we consider "MS" as first name and "Dhoni" as last name
            first_name = " ".join(name_parts[:-1])
            
            # Try to find a match where both first name components and last name match
            potential_matches = []
            
            for player in structured_player_data:
                # Check last name exact match first
                if player['last_name'].lower() == last_name.lower():
                    # Check first name components
                    player_first = player['first_name'].lower()
                    player_first_initials = ''.join([p[0] for p in player_first.split() if p])
                    
                    name_first = first_name.lower()
                    name_first_initials = ''.join([p[0] for p in name_first.split() if p])
                    
                    # Calculate match score based on first name comparison
                    score = 0
                    
                    # Exact first name match (highest priority)
                    if player_first == name_first:
                        score = 100
                    # Check if initials match (medium priority)
                    elif player_first_initials == name_first or name_first_initials == player_first:
                        score = 80
                    # Check if initials are contained in each other
                    elif (name_first_initials and player_first_initials and 
                          (name_first_initials in player_first_initials or 
                           player_first_initials in name_first_initials)):
                        score = 60
                    # Check if there's any overlap in first name components
                    elif any(p in player_first.split() for p in name_first.split()):
                        score = 40
                    # Last name only match (lowest priority)
                    else:
                        score = 20
                        
                    if score > 0:
                        potential_matches.append((player['full_name'], player['id'], score))
            
            if potential_matches:
                # Sort by score (highest first)
                potential_matches.sort(key=lambda x: x[2], reverse=True)
                best_match = potential_matches[0]
                
                # Only use matches with a reasonable score
                if best_match[2] >= 40:  # Threshold for a reasonable match
                    print(f"Matched '{name}' to '{best_match[0]}' with score {best_match[2]}")
                    return best_match[1]
        
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
        
        # Skip if name is missing
        if pd.isna(player_name) or player_name == '':
            continue
            
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
    updated_file_path = 'data/register_data/squadData_ipl25_updated3.csv'
    squad_data.to_csv(updated_file_path, index=False)
    
    print(f"Updated {updated_count} player IDs in squadData_ipl25.csv")
    print(f"Updated file saved as {updated_file_path}")

if __name__ == "__main__":
    update_player_ids()