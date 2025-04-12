#check players which have null key_cricbuzz values
import pandas as pd
import numpy as np

# Load the CSV data
df = pd.read_csv('data/register_data/squadData_ipl25.csv')

# Find rows where key_cricbuzz is null or NaN
# This handles both empty strings and actual NaN values
null_cricbuzz = df[df['key_cricbuzz'].isna() | (df['key_cricbuzz'] == '')]

# Display the count
print(f"Number of players with null key_cricbuzz: {len(null_cricbuzz)}")

# Display the relevant columns for these players
if len(null_cricbuzz) > 0:
    print("\nPlayers with null key_cricbuzz values:")
    display_columns = ['dream11_name', 'team', 'role']
    print(null_cricbuzz[display_columns].reset_index(drop=True))

# Optional: Save the result to a new CSV file
null_cricbuzz.to_csv('players_with_null_cricbuzz.csv', index=False)