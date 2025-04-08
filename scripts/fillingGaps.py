import pandas as pd

# Load the two CSV files
# Replace 'first_csv.csv' and 'second_csv.csv' with your actual filenames
df_incomplete = pd.read_csv('data/register_data/squadData_ipl25_updated3.csv')
df_complete = pd.read_csv('data/register_data/squadData_ipl25_updated.csv')

# Make a copy of the original dataframe to preserve it
df_original = df_incomplete.copy()

# Count missing values before the merge
missing_before = df_incomplete['key_cricbuzz'].isna().sum()
print(f"Missing key_cricbuzz values before: {missing_before}")

# Method 1: Fill using key_cricinfo
# Create a mapping dictionary from the complete dataframe
cricinfo_to_cricbuzz = dict(zip(df_complete['key_cricinfo'], df_complete['key_cricbuzz']))

# Fill missing values using key_cricinfo mapping
for idx, row in df_incomplete.iterrows():
    if pd.isna(row['key_cricbuzz']) and row['key_cricinfo'] in cricinfo_to_cricbuzz:
        df_incomplete.at[idx, 'key_cricbuzz'] = cricinfo_to_cricbuzz[row['key_cricinfo']]

# Method 2: Fill using dream11_name for any remaining missing values
# Create a mapping dictionary using dream11_name
dream11_to_cricbuzz = dict(zip(df_complete['dream11_name'], df_complete['key_cricbuzz']))

# Fill remaining missing values using dream11_name mapping
for idx, row in df_incomplete.iterrows():
    if pd.isna(row['key_cricbuzz']) and row['dream11_name'] in dream11_to_cricbuzz:
        df_incomplete.at[idx, 'key_cricbuzz'] = dream11_to_cricbuzz[row['dream11_name']]

# Count missing values after the merge
missing_after = df_incomplete['key_cricbuzz'].isna().sum()
print(f"Missing key_cricbuzz values after: {missing_after}")
print(f"Filled {missing_before - missing_after} values")

# Display rows that still have missing values (if any)
if missing_after > 0:
    print("\nRows with missing key_cricbuzz values after merging:")
    print(df_incomplete[df_incomplete['key_cricbuzz'].isna()])

# Save the updated dataframe to a new CSV file
df_incomplete.to_csv('updated_csv.csv', index=False)
print("Updated CSV saved as 'updated_csv.csv'")