#!/usr/bin/env python3
import pandas as pd
import os


def sort_csv_by_date(input_csv, output_csv):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(input_csv)

    # Convert the 'date' column to datetime objects.
    # If your date format is specific, you can specify it with the format parameter.
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Sort the DataFrame by the 'date' column (ascending order)
    df_sorted = df.sort_values(by='date', ascending=True)

    # Write the sorted DataFrame to a new CSV file without the index
    df_sorted.to_csv(output_csv, index=False)
    print(f"Sorted CSV saved to {output_csv}")


if __name__ == "__main__":
    # Define the input and output CSV file paths
    input_csv = r"D:\ED\FIFS_IPL\data\t20_bbb.csv"
    output_csv = r"D:\ED\FIFS_IPL\data\t20_bbb_sorted.csv"

    # Check if the input file exists
    if not os.path.exists(input_csv):
        print(f"Input file does not exist: {input_csv}")
    else:
        sort_csv_by_date(input_csv, output_csv)
