import os
import pandas as pd

def predict_batting_performance(bat_model, test_bat, matchup_df, label_encoder, match_number):
    """
    Generate batting predictions using PyCaret model.

    Parameters:
    -----------
    bat_model : PyCaret model object
        The trained batting prediction model
    test_bat : DataFrame
        Test data for batters
    matchup_df : DataFrame
        Matchup scores data
    label_encoder : dict or object
        Label encoders for categorical variables
    match_number : int
        Match number for output file naming

    Returns:
    --------
    DataFrame
        Predictions for each batter
    """
    try:
        print("\nGenerating batting predictions...")

        # Check if 'matchup_score' exists in matchup_df and rename it
        if 'matchup_score' in matchup_df.columns and 'batter_matchup_score' not in matchup_df.columns:
            print("Renaming 'matchup_score' to 'batter_matchup_score'")
            matchup_df = matchup_df.rename(columns={'matchup_score': 'batter_matchup_score'})

        # Merge test_bat with matchup_df
        X_batting_test = pd.merge(
            test_bat,
            matchup_df,
            how='left',
            on='batter_id'
        )
        print(f"Merged dataset shape: {X_batting_test.shape}")

        # Check if the required column exists after merge
        if 'batter_matchup_score' not in X_batting_test.columns:
            print("WARNING: 'batter_matchup_score' column not found after merge!")
            print("Creating dummy column with default value 0")
            X_batting_test['batter_matchup_score'] = 0

        print(f"Merged dataset shape: {X_batting_test.shape}")

        # Store batter_ids for the output
        batter_ids = X_batting_test['batter_id'].values

        # Convert string columns to numeric where needed
        for col in X_batting_test.select_dtypes(include=['object', 'string']).columns:
            if col != 'batter_id':
                X_batting_test[col] = pd.to_numeric(X_batting_test[col], errors='coerce')

        # Fill NaN values
        X_batting_test.fillna(0, inplace=True)

        # Make predictions
        batting_predictions = bat_model.predict(X_batting_test)

        # Handle different output shapes
        if len(batting_predictions.shape) > 1 and batting_predictions.shape[1] > 1:
            batting_predictions = batting_predictions[:, 0]
        else:
            batting_predictions = batting_predictions.flatten()

        # Create results dataframe
        results_df = pd.DataFrame({
            'batter_id': batter_ids,
            'batting_prediction': batting_predictions
        })

        # Save to CSV
        save_dir = 'Output'
        os.makedirs(save_dir, exist_ok=True)
        csv_path = os.path.join(save_dir, f"prediction_match_{match_number}_bat.csv")
        results_df.to_csv(csv_path, index=False)
        print(f"Saved batting predictions to {csv_path}")

        return results_df

    except Exception as e:
        print(f"Error in batting prediction: {e}")
        import traceback
        traceback.print_exc()
        return None