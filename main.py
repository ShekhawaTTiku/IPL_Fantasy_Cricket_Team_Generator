import pandas as pd
import csv
import numpy as np
import os
import pickle
import argparse
import sys
from scripts.google_sheet_data_fetch import get_data_from_google_sheet
from scripts.match_scraper import get_today_details
from scripts.backup_match_scraper import backup_match_scrapping
from scripts.test_data_gen_bat import get_test_bat
from scripts.test_data_gen_bowl import get_test_bowl
from scripts.test_data_gen_matchup import get_matchup_score
from scripts.load_model import load_model_pycaret
from scripts.batting_prediction import predict_batting_performance
from scripts.predict_match import predict_one_match
from scripts.optimiser import optimize_fantasy_team

# Parse command line arguments with proper validation
parser = argparse.ArgumentParser(description='Cricket Fantasy Team Optimization')
parser.add_argument('--match', '-m', dest='match_number', type=int, default=1,
                   help='Match number to process (default: 1)')

try:
    args = parser.parse_args()
    if args.match_number <= 0:
        raise ValueError("Match number must be positive")
except Exception as e:
    print(f"Error with command line arguments: {e}")
    sys.exit(1)

# =====MAKING DIRECTORIES=====
downloads_folder = 'Downloads'
output_folder = 'Output'

if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"Created folder: {output_folder}")
else:
    print(f"Folder already exists: {output_folder}")

if not os.path.exists(downloads_folder):
    os.makedirs(downloads_folder)
    print(f"Created folder: {downloads_folder}")
else:
    print(f"Folder already exists: {downloads_folder}")

# =====FETCHING GOOGLE SHEET DATA=====
# Define CSV file paths.
mbm_bat_csv = os.path.join(downloads_folder, 'mbm_bat_final.csv')
mbm_bowl_csv = os.path.join(downloads_folder, 'mbm_bowl_final.csv')
perf_csv = os.path.join(downloads_folder, 'perf_metric_df.csv')
squad_csv = os.path.join(downloads_folder, 'squad_df.csv')

# Load data from CSV files if they exist; otherwise, fetch from Google Sheets.
if all(os.path.exists(path) for path in [mbm_bat_csv, mbm_bowl_csv, perf_csv, squad_csv]):
    print("Loading data from CSV files...")
    mbm_bat_final = pd.read_csv(mbm_bat_csv)
    mbm_bowl_final = pd.read_csv(mbm_bowl_csv)
    perf_metric_df = pd.read_csv(perf_csv)
    squad_df = pd.read_csv(squad_csv)
else:
    print("Fetching data from Google Sheets...")
    mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df = get_data_from_google_sheet()
    mbm_bowl_final.to_csv(mbm_bowl_csv, index=False)
    mbm_bat_final.to_csv(mbm_bat_csv, index=False)
    perf_metric_df.to_csv(perf_csv, index=False)
    squad_df.to_csv(squad_csv, index=False)

# =====MATCH DETAIL SCRAPING=====
# Get match number from command line arguments
match_number = args.match_number
print(f"\nProcessing match number: {match_number}")
print("Starting match scrapper...")

# Scrape match details
match_df = get_today_details(match_number=match_number)
# Check if match_df is empty
if not match_df.empty:
    print("Successfully scraped match data!")
    print(f"Match date: {match_df['Date'].iloc[0]}")
else:
    print(f"Failed to scrape match data for match number {match_number}.")
    print("Using backup match scrapping...")
    match_df = backup_match_scrapping()

if match_df.empty:
    print("Error: No match data found. Toss has not happened yet.")
    sys.exit(1)

# Save the match data to CSV files with match number suffix.
match_df.to_csv(os.path.join(output_folder, f'match_df{match_number}.csv'), index=False)

# =====TEST DATA GENERATION=====
# Generate test data for batting, bowling, and matchup scores.
test_bat = get_test_bat(mbm_bat_final, match_df)
test_bowl = get_test_bowl(mbm_bowl_final, match_df)
matchup_df = get_matchup_score(perf_metric_df, mbm_bowl_final, match_df, squad_df)


# Save the test data to CSV files with match number suffix.
test_bat.to_csv(os.path.join(output_folder, f'test_bat{match_number}.csv'), index=False)
test_bowl.to_csv(os.path.join(output_folder, f'test_bowl{match_number}.csv'), index=False)
matchup_df.to_csv(os.path.join(output_folder, f'matchup_score{match_number}.csv'), index=False)

print(f"Test data for match number {match_number} generated and saved to CSV files.")

# MODEL PREDICTION
# Load the model
bat_model, bowl_model, label_encoder = load_model_pycaret()

# Prediction
# run predictions for this single match
fp_df = predict_one_match(
    match_number=match_number,
    bat_model=bat_model,
    bowl_model=bowl_model,
    label_encoder=label_encoder,
    test_bat_df=test_bat,
    test_bowl_df=test_bowl,
    matchup_df=matchup_df,
    save_dir=output_folder
)

# OPTIMISATION
out = optimize_fantasy_team(match_number=match_number, fp_df=fp_df, squad_df=squad_df, output_dir=output_folder)

print(out)