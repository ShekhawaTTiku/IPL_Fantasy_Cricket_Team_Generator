import pandas as pd

# File paths (change these as necessary)
sheet1_path = r'D:\ED\FIFS_IPL\IPL\required_data\players_25.csv'  # Contains: player_id,player_object_id,player_name,...
sheet2_path = r'D:\ED\FIFS_IPL\IPL\required_data\people.csv'  # Contains: identifier,name,unique_name,..., key_cricinfo,...

# Read the CSV files into DataFrames
df1 = pd.read_csv(sheet1_path)
df2 = pd.read_csv(sheet2_path)


# Normalize player_object_id from sheet1 to string
def normalize_key(value):
    """
    Converts the input to a normalized string:
    - If value is a float and an integer value (e.g. 12345.0), convert to int first.
    - Otherwise, convert to string.
    """
    try:
        if pd.isnull(value):
            return None
        if isinstance(value, float):
            # If the float is actually an integer value, convert it to int
            if value.is_integer():
                return str(int(value))
            else:
                return str(value)
        return str(value)
    except Exception as e:
        return None


# Create a mapping from normalized player_object_id to player_name from sheet1
mapping = {normalize_key(pid): player_name for pid, player_name in zip(df1['player_object_id'], df1['player_name'])}

# Initialize counters for logging
total_records = len(df2)
update_count = 0
not_found_count = 0
log_details = []

# Iterate through the second sheet and update unique_name if key_cricinfo matches normalized key
for idx, row in df2.iterrows():
    key_raw = row['key_cricinfo']
    key_normalized = normalize_key(key_raw)

    if key_normalized is not None and key_normalized in mapping:
        old_unique_name = row['unique_name']
        new_unique_name = mapping[key_normalized]
        df2.at[idx, 'unique_name'] = new_unique_name
        update_count += 1
        log_details.append(
            f"Row {idx}: key_cricinfo '{key_raw}' normalized to '{key_normalized}' matched. Updated unique_name from '{old_unique_name}' to '{new_unique_name}'.")
    else:
        not_found_count += 1
        log_details.append(
            f"Row {idx}: key_cricinfo '{key_raw}' normalized to '{key_normalized}' not found in sheet1 mapping.")

# Save the updated second sheet to a new CSV file
updated_sheet2_path = 'sheet2_updated.csv'
df2.to_csv(updated_sheet2_path, index=False)

# Create a summary log report
log_report = (
        f"Total records in sheet2: {total_records}\n"
        f"Total updates applied: {update_count}\n"
        f"Total records not matched: {not_found_count}\n"
        f"Detailed Log:\n" + "\n".join(log_details)
)

# Write the log to a file using UTF-8 encoding to handle special characters
with open('update_log.txt', 'w', encoding='utf-8') as f:
    f.write(log_report)

# Print the summary log report
print(log_report)
