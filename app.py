# app.py

import logging
import os
import pandas as pd
from flask import Flask, request, jsonify, render_template
from functools import lru_cache  # Import the caching tool

from scripts.data_loading import get_data
from scripts.model_loading import load_models
from scripts.input_module import process_input_custom, process_input_scraper
from scripts.test_data_gen_bat import get_test_bat
from scripts.test_data_gen_bowl import get_test_bowl
from scripts.test_data_gen_matchup import get_matchup_score
from scripts.predict_match import predict_one_match
from scripts.optimiser import optimize_fantasy_team

# Configure logging to output to the console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)


# ===== LAZY-LOADING FUNCTIONS WITH CACHING =====
# These functions will only run once. The @lru_cache decorator stores
# the result, so subsequent calls return the stored value instantly
# without re-running the function.

@lru_cache(maxsize=None)
def get_cached_data():
    """Loads and caches the dataframes."""
    logging.info("Loading and caching data for the first time...")
    try:
        data = get_data()
        logging.info("Data loaded and cached successfully.")
        return data
    except Exception as e:
        logging.critical(f"FATAL: Could not load data. Error: {e}")
        return None, None, None, None


@lru_cache(maxsize=None)
def get_cached_models():
    """Loads and caches the ML models."""
    logging.info("Loading and caching models for the first time...")
    try:
        models = load_models()
        logging.info("Models loaded and cached successfully.")
        return models
    except Exception as e:
        logging.critical(f"FATAL: Could not load models. Error: {e}")
        return None, None, None


# ===== FLASK ROUTES =====

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    """Handles the prediction request from the frontend."""

    # --- Load data and models on-demand ---
    # These functions will execute their content only on the very first request.
    logging.info("Attempting to load data and models from cache...")
    mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df = get_cached_data()
    batting_model, bowling_model, label_encoder = get_cached_models()

    # Check if loading failed during the first request
    if squad_df is None or batting_model is None:
        return jsonify(
            {"error": "Server error: Could not load necessary data or models. Please check the server logs."}), 500

    try:
        data = request.get_json()
        logging.info(f"Received prediction request with data: {data}")

        input_method = data.get('input_method')
        output_mode = int(data.get('output_mode', 2))
        output_folder = 'Output'
        os.makedirs(output_folder, exist_ok=True)

        # --- Process Input ---
        if input_method == 'scraper':
            match_number = int(data.get('match_number'))
            match_df = process_input_scraper(match_number)
        elif input_method == 'custom':
            match_details = data.get('match_details')
            match_df = process_input_custom(squad_df, match_details)
            match_number = int(f"{pd.Timestamp.now().strftime('%y%m%d%H%M')}")
        else:
            return jsonify({"error": "Invalid input method"}), 400

        if match_df is None or match_df.empty:
            return jsonify(
                {"error": "Failed to get match details. The scraper might have failed or input was invalid."}), 400

        # --- Run the ML Pipeline ---
        logging.info("Generating test data...")
        test_bat = get_test_bat(mbm_bat_final, match_df)
        test_bowl = get_test_bowl(mbm_bowl_final, match_df)
        matchup_df = get_matchup_score(perf_metric_df, mbm_bowl_final, match_df, squad_df)

        logging.info("Running predictions...")
        fp_df = predict_one_match(
            match_number=match_number,
            test_bat_df=test_bat,
            test_bowl_df=test_bowl,
            matchup_df=matchup_df,
            bat_model=batting_model,
            bowl_model=bowling_model,
            label_encoder=label_encoder,
            save_dir=output_folder
        )

        logging.info("Optimising fantasy team...")
        result_df = optimize_fantasy_team(
            match_number=match_number,
            fp_df=fp_df,
            squad_df=squad_df,
            output_dir=output_folder,
            output_mode=output_mode
        )

        if result_df is None or result_df.empty:
            return jsonify({"error": "Could not generate a team. Please check logs."}), 500

        result_json = result_df.to_dict(orient='records')
        return jsonify(result_json)

    except Exception as e:
        logging.error(f"An unexpected error occurred in /predict: {str(e)}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))