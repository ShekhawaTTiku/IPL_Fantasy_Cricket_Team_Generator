#!/usr/bin/env python3
import pandas as pd
import os


def filter_years(csv_path, output_csv):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_path)

    # Filter rows where the 'year' column is in [2015, 2016, 2017]
    df_filtered = df[df['year'].isin([2015, 2016, 2017])]

    # Optionally, print the number of filtered rows
    print(f"Filtered CSV contains {df_filtered.shape[0]} rows.")

    # Write the filtered DataFrame to a new CSV file without the index
    df_filtered.to_csv(output_csv, index=False)
    print(f"Filtered CSV saved to {output_csv}")


if __name__ == "__main__":
    # Define the input and output CSV file paths
    input_csv = r"D:\ED\FIFS_IPL\data\t20_bbb_sorted.csv"
    output_csv = r"D:\ED\FIFS_IPL\data\t20_bbb_filtered.csv"

    # Check if the input file exists
    if not os.path.exists(input_csv):
        print(f"Input file does not exist: {input_csv}")
    else:
        filter_years(input_csv, output_csv)
