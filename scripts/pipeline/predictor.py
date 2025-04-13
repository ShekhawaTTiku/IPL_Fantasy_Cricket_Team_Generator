import os
import pandas as pd
import sys
from sklearn.preprocessing import LabelEncoder
from pycaret.classification import load_model, predict_model

def predict_fantasy_points(batting_data, bowling_data, match_number):
    """
    Predict fantasy points using PyCaret models for batting and bowling data.
    """
    print(f"Starting prediction process for match {match_number}")
    
    # Create fp_predictor folder if it doesn't exist
    fp_predictor_dir = r"D:\App\FIFS_IPL\fp_predictor"
    if not os.path.exists(fp_predictor_dir):
        os.makedirs(fp_predictor_dir)
        print(f"Created directory: {fp_predictor_dir}")
    else:
        print(f"Directory already exists: {fp_predictor_dir}")
    
    # Process batting data
    try:
        # Check if batting_data is a file path or DataFrame
        if isinstance(batting_data, str):
            print(f"Reading batting data from file: {batting_data}")
            batting_df = pd.read_csv(batting_data)
        else:
            print("Using provided batting DataFrame")
            batting_df = batting_data.copy()
            
        print(f"Batting data shape: {batting_df.shape[0]} rows, {batting_df.shape[1]} columns")
        print(f"Original column names: {batting_df.columns.tolist()}")
        
        # Store player IDs for later use
        player_ids = batting_df['player_id'].copy()
        
        # Keep a copy of the venue if it exists
        if 'venue' in batting_df.columns:
            venue_values = batting_df['venue'].copy()
        else:
            venue_values = None

        # Keep a copy of the 'season' column if it exists
        if 'season' in batting_df.columns:
            season_values = batting_df['season'].copy()
        else:
            season_values = None
        
        # Create column mapping for batting data
        batting_column_mapping = {
            'player_id': 'batter_id',
            'innings': 'inns',
            'career_batting_average': 'career_avg',
            'career_strike_rate': 'career_sr',
            'career_boundaries_per_match': 'career_bpm',
            'career_runs_per_match': 'career_rpm',
            'career_balls_faced_per_match': 'career_bfpm',
            'last5_batting_average': 'last5_avg',
            'last5_strike_rate': 'last5_sr',
            'last5_boundaries_per_match': 'last5_bpm',
            'last5_runs_per_match': 'last5_rpm',
            'last5_balls_faced_per_match': 'last5_bfpm',
            'innings_batting_average': 'inns_avg',
            'innings_strike_rate': 'inns_sr',
            'innings_boundaries_per_match': 'inns_bpm',
            'innings_runs_per_match': 'inns_rpm',
            'innings_balls_faced_per_match': 'inns_bfpm',
            'venue_batting_average': 'ven_avg',
            'venue_strike_rate': 'ven_sr',
            'venue_boundaries_per_match': 'ven_bpm',
            'venue_runs_per_match': 'ven_rpm',
            'venue_balls_faced_per_match': 'ven_bfpm',
            'season_batting_average': 'ssn_avg',
            'season_strike_rate': 'ssn_sr',
            'season_boundaries_per_match': 'ssn_bpm',
            'season_runs_per_match': 'ssn_rpm',
            'season_balls_faced_per_match': 'ssn_bfpm'
        }
        
        # Rename columns to match what the model expects
        columns_to_rename = {col: mapping for col, mapping in batting_column_mapping.items() 
                           if col in batting_df.columns}
        batting_df = batting_df.rename(columns=columns_to_rename)
        
        # Label encode 'bat_team' and 'bowl_team'
        categorical_columns = ['bat_team', 'bowl_team']
        label_encoder = LabelEncoder()
        
        for col in categorical_columns:
            if col in batting_df.columns:
                print(f"Label encoding column: {col}")
                batting_df[col] = label_encoder.fit_transform(batting_df[col])
                print(f"Unique values in {col} mapped to: {dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))}")
        
        # Remove non-numeric columns that could cause issues (but keep venue)
        columns_to_drop = ['player_name', 'cutoff_date']
        for col in columns_to_drop:
            if col in batting_df.columns:
                batting_df = batting_df.drop(col, axis=1)
                print(f"Dropped column: {col}")
        
        # Add required columns that were used during training
        required_columns = ['career_debut', 'season_debut', 'venue_debut', 'innings_debut']
        for col in required_columns:
            print(f"Adding required column: {col}")
            batting_df[col] = 0  # Set default value to 0
        
        # Re-add 'season' column if it was dropped
        if 'season' not in batting_df.columns and season_values is not None:
            batting_df['season'] = season_values
            print(f"Re-added column: season")
        elif 'season' not in batting_df.columns:
            batting_df['season'] = 0  # Add with default value
            print(f"Added missing column: season")
        
        # Re-add 'venue' column if it was somehow dropped
        if 'venue' not in batting_df.columns and venue_values is not None:
            batting_df['venue'] = venue_values
            print(f"Re-added column: venue")
        
        # Ensure all remaining columns are numeric
        for col in batting_df.columns:
            if batting_df[col].dtype == 'object':
                print(f"Converting column {col} to numeric")
                batting_df[col] = pd.to_numeric(batting_df[col], errors='coerce')
        
        # Fill missing values with 0
        batting_df = batting_df.fillna(0)
        
        print(f"Processed batting data shape: {batting_df.shape[0]} rows, {batting_df.shape[1]} columns")
        print(f"Processed column names: {batting_df.columns.tolist()}")
        
        # Load model - REMOVED .pkl extension
        print("Loading batting model...")
        batting_model = load_model("D:/App/FIFS_IPL/models/batting_model_flag")
        print("Batting model loaded successfully")
        
        # Make predictions
        print("Making batting predictions...")
        batting_predictions = predict_model(batting_model, data=batting_df)
        print(f"Predictions completed. Result shape: {batting_predictions.shape[0]} rows, {batting_predictions.shape[1]} columns")
        print(f"Prediction columns: {batting_predictions.columns.tolist()}")
        
        # Find prediction column (name can vary by PyCaret version)
        pred_cols = [col for col in batting_predictions.columns 
                   if col.startswith('prediction_') or col == 'Label' or col == 'Score']
        
        print(f"Identified prediction columns: {pred_cols}")
        
        if pred_cols:
            # Create result dataframe with required columns
            batting_results = pd.DataFrame()
            
            # Add player id (using stored original player IDs)
            batting_results['player id'] = player_ids
            print("Added player IDs from original data")
            
            # Add prediction
            batting_results['generated_fp'] = batting_predictions[pred_cols[0]]
            print(f"Added generated_fp column from {pred_cols[0]}")
            
            # Save to CSV
            batting_output_path = os.path.join(fp_predictor_dir, f"predicted_bat_{match_number}.csv")
            print(f"Saving batting predictions to {batting_output_path}")
            
            # Print a preview of what we're saving
            print("Preview of batting results:")
            print(batting_results.head())
            
            batting_results.to_csv(batting_output_path, index=False)
            
            # Verify file was created
            if os.path.exists(batting_output_path):
                print(f"SUCCESS: Batting predictions saved to {batting_output_path}")
            else:
                print(f"ERROR: Failed to create {batting_output_path}")
        else:
            print("ERROR: Could not identify prediction column in batting results")
            
    except Exception as e:
        print(f"ERROR processing batting data: {str(e)}")
        import traceback
        traceback.print_exc(file=sys.stdout)
    
    # Process bowling data with similar approach
    try:
        # Check if bowling_data is a file path or DataFrame
        if isinstance(bowling_data, str):
            print(f"Reading bowling data from file: {bowling_data}")
            bowling_df = pd.read_csv(bowling_data)
        else:
            print("Using provided bowling DataFrame")
            bowling_df = bowling_data.copy()
            
        # Store original player IDs
        player_ids = bowling_df['player_id'].copy()
        
        # Keep a copy of the venue if it exists
        if 'venue' in bowling_df.columns:
            venue_values = bowling_df['venue'].copy()
        else:
            venue_values = None

        # Keep a copy of the 'season' column if it exists
        if 'season' in bowling_df.columns:
            season_values = bowling_df['season'].copy()
        else:
            season_values = None
        
        print(f"Bowling data shape: {bowling_df.shape[0]} rows, {bowling_df.shape[1]} columns")
        print(f"Original column names: {bowling_df.columns.tolist()}")
        
        # Create column mapping for bowling data based on your provided column names
        bowling_column_mapping = {
            'player_id': 'bowler_id',
            'innings': 'inns',
            'career_average': 'career_avg',
            'career_strike_rate': 'career_sr',
            'career_economy': 'career_eco',
            'career_wickets_per_match': 'career_wpm',
            'career_overs_per_match': 'career_opm',
            'last5_average': 'last5_avg',
            'last5_strike_rate': 'last5_sr',
            'last5_economy': 'last5_eco',
            'last5_wickets_per_match': 'last5_wpm',
            'last5_overs_per_match': 'last5_opm',
            'innings_average': 'inns_avg',
            'innings_strike_rate': 'inns_sr',
            'innings_economy': 'inns_eco',
            'innings_wickets_per_match': 'inns_wpm',
            'innings_overs_per_match': 'inns_opm',
            'venue_average': 'venue_avg',
            'venue_strike_rate': 'venue_sr',
            'venue_economy': 'venue_eco',
            'venue_wickets_per_match': 'venue_wpm',
            'venue_overs_per_match': 'venue_opm',
            'season_average': 'ssn_avg',
            'season_strike_rate': 'ssn_sr',
            'season_economy': 'ssn_eco',
            'season_wickets_per_match': 'ssn_wpm',
            'season_overs_per_match': 'ssn_opm'
        }
        
        # Rename columns to match what the model expects
        columns_to_rename = {col: mapping for col, mapping in bowling_column_mapping.items() 
                           if col in bowling_df.columns}
        bowling_df = bowling_df.rename(columns=columns_to_rename)
        
        # Label encode 'bat_team' and 'bowl_team'
        categorical_columns = ['bat_team', 'bowl_team']
        label_encoder = LabelEncoder()
        
        for col in categorical_columns:
            if col in bowling_df.columns:
                print(f"Label encoding column: {col}")
                bowling_df[col] = label_encoder.fit_transform(bowling_df[col])
                print(f"Unique values in {col} mapped to: {dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))}")
        
        # Remove non-numeric columns that could cause issues (but keep venue)
        columns_to_drop = ['player_name', 'cutoff_date']
        for col in columns_to_drop:
            if col in bowling_df.columns:
                bowling_df = bowling_df.drop(col, axis=1)
                print(f"Dropped column: {col}")
        
        # Add required columns that were used during training
        required_columns = [
            'career_debut', 'season_debut', 'venue_debut', 'innings_debut', 
        ]
        


        for col in required_columns:
            if col not in bowling_df.columns:
                print(f"Adding required column: {col}")
                bowling_df[col] = 0  # Set default value to 0
        
        # Re-add 'season' column if it was dropped
        if 'season' not in bowling_df.columns and season_values is not None:
            bowling_df['season'] = season_values
            print(f"Re-added column: season")
        elif 'season' not in bowling_df.columns:
            bowling_df['season'] = 0  # Add with default value
            print(f"Added missing column: season")
        
        # Re-add 'venue' column if it was somehow dropped
        if 'venue' not in bowling_df.columns and venue_values is not None:
            bowling_df['venue'] = venue_values
            print(f"Re-added column: venue")
        
        # Ensure all remaining columns are numeric
        for col in bowling_df.columns:
            if bowling_df[col].dtype == 'object':
                print(f"Converting column {col} to numeric")
                bowling_df[col] = pd.to_numeric(bowling_df[col], errors='coerce')
        
        # Fill missing values with 0
        bowling_df = bowling_df.fillna(0)
        
        print(f"Processed bowling data shape: {bowling_df.shape[0]} rows, {bowling_df.shape[1]} columns")
        print(f"Processed column names: {bowling_df.columns.tolist()}")
        
        # Load model
        print("Loading bowling model...")
        bowling_model = load_model(r"D:/App/FIFS_IPL/models/bowling_model_flag")
        print("Bowling model loaded successfully")
        
        # Make predictions
        print("Making bowling predictions...")
        bowling_predictions = predict_model(bowling_model, data=bowling_df)
        print(f"Predictions completed. Result shape: {bowling_predictions.shape[0]} rows, {bowling_predictions.shape[1]} columns")
        
        # Find prediction column
        pred_cols = [col for col in bowling_predictions.columns 
                   if col.startswith('prediction_') or col == 'Label' or col == 'Score']
        
        if pred_cols:
            # Create result dataframe with required columns
            bowling_results = pd.DataFrame()
            
            # Add player id (using stored original player IDs)
            bowling_results['player id'] = player_ids
            print("Added player IDs from original data")
            
            # Add prediction
            bowling_results['generated_fp'] = bowling_predictions[pred_cols[0]]
            print(f"Added generated_fp column from {pred_cols[0]}")
            
            # Save to CSV
            bowling_output_path = os.path.join(fp_predictor_dir, f"predicted_bowl_{match_number}.csv")
            bowling_results.to_csv(bowling_output_path, index=False)
            print(f"SUCCESS: Bowling predictions saved to {bowling_output_path}")
            
        else:
            print("ERROR: Could not identify prediction column in bowling results")
            
    except Exception as e:
        print(f"ERROR processing bowling data: {str(e)}")
        import traceback
        traceback.print_exc(file=sys.stdout)

    print("Prediction process completed.")