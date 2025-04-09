import pandas as pd
from collections import defaultdict
import sys

def find_duplicate_ids(csv_path):
    """
    Find and print players with duplicate IDs in the given CSV file.
    
    Args:
        csv_path (str): Path to the CSV file to check
    """
    print(f"Checking for duplicate IDs in: {csv_path}")
    
    try:
        # Read the CSV file
        data = pd.read_csv(csv_path)
        
        # Check if the required columns exist
        name_col = 'cricbuzz_name'
        id_col = 'key_cricbuzz'
        
        if name_col not in data.columns:
            print(f"Error: Column '{name_col}' not found in the CSV file.")
            print(f"Available columns: {data.columns.tolist()}")
            return
        
        if id_col not in data.columns:
            print(f"Error: Column '{id_col}' not found in the CSV file.")
            print(f"Available columns: {data.columns.tolist()}")
            return
        
        # Create a dictionary to map IDs to player names
        id_to_names = defaultdict(list)
        
        # Only process rows where the ID is not empty/NaN
        valid_data = data[data[id_col].notna()]
        
        # Fill the dictionary
        for _, row in valid_data.iterrows():
            player_id = row[id_col]
            player_name = row[name_col]
            
            # Skip if player ID or name is missing
            if pd.isna(player_id) or pd.isna(player_name) or player_id == 0 or player_id == '':
                continue
                
            id_to_names[player_id].append(player_name)
        
        # Find and print duplicates
        print("\n=== PLAYERS WITH DUPLICATE IDs ===")
        found_duplicates = False
        
        for player_id, names in id_to_names.items():
            if len(names) > 1:
                found_duplicates = True
                print(f"\nID: {player_id} is assigned to {len(names)} players:")
                for i, name in enumerate(names, 1):
                    print(f"  {i}. {name}")
        
        if not found_duplicates:
            print("No duplicate IDs found!")
        
        # Print some statistics
        print("\n=== STATISTICS ===")
        print(f"Total players in file: {len(data)}")
        print(f"Players with valid IDs: {len(valid_data)}")
        print(f"Unique IDs used: {len(id_to_names)}")
        
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    # Check if a file path was provided as a command-line argument
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = 'data/register_data/squadData_ipl25_updated_new.csv'
    
    find_duplicate_ids(csv_path)