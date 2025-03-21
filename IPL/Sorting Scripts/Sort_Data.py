#!/usr/bin/env python3
import pandas as pd
import os


def filter_and_sort(csv_path, output_csv):
    """Filter the CSV by year and sort by year, p_match, innings, and ball ID."""
    # Read the CSV file into a DataFrame with low_memory=False to suppress warnings
    df = pd.read_csv(csv_path, low_memory=False)

    # Filter rows where the 'year' column is 2025
    df_filtered = df[df['year'] == 2022]

    # Optionally, print the number of filtered rows
    print(f"Filtered CSV contains {df_filtered.shape[0]} rows.")

    # Verify that the required columns exist
    required_columns = ['year', 'p_match', 'inns', 'ball_id']
    missing_columns = [col for col in required_columns if col not in df_filtered.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Define a custom key function to sort ball_id properly
    def ball_id_key(ball_id):
        try:
            # Convert to string to handle mixed types or floats
            ball_id = str(ball_id)
            over_str, ball_str = ball_id.split('.')
            over = int(over_str)  # Over number
            ball = int(ball_str)  # Ball number within the over
            return over * 6 + ball  # Total balls bowled in the innings
        except (ValueError, AttributeError):
            # If there's an issue with conversion, return a large number to push it to the end
            return float('inf')

    # First sort by 'year', 'p_match', and 'inns' without using a key function
    df_sorted = df_filtered.sort_values(by=['year', 'p_match', 'inns'])

    # Then sort by 'ball_id' using the custom key function within each group (p_match and inns)
    df_sorted['ball_id_sort'] = df_sorted['ball_id'].map(ball_id_key)
    df_sorted = df_sorted.sort_values(by=['year', 'p_match', 'inns', 'ball_id_sort'])
    df_sorted = df_sorted.drop(columns=['ball_id_sort'])  # Drop the temporary sort column

    # Write the sorted and filtered DataFrame to a new CSV file without the index
    df_sorted.to_csv(output_csv, index=False)
    print(f"Filtered and sorted CSV saved to {output_csv}")


if __name__ == "__main__":
    # Define the input and output CSV file paths
    input_csv = r"E:\IPL\dream11_points_predictor-main\dream11_points_predictor-main\IPL\Data\t20_bbb.csv"
    output_csv = r"E:\IPL\dream11_points_predictor-main\dream11_points_predictor-main\IPL\Sorted_Data\t20_bbb_22_filtered.csv"

    # Check if the input file exists
    if not os.path.exists(input_csv):
        print(f"Input file does not exist: {input_csv}")
    else:
        filter_and_sort(input_csv, output_csv)
