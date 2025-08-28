import logging
import os
import pandas as pd
from flask import Flask, request, jsonify, render_template

from scripts.data_loading import get_data
from scripts.model_loading import load_models
from scripts.input_module import process_input_custom, process_input_scraper
from scripts.test_data_gen_bat import get_test_bat
from scripts.test_data_gen_bowl import get_test_bowl
from scripts.test_data_gen_matchup import get_matchup_score
from scripts.predict_match import predict_one_match
from scripts.optimiser import optimize_fantasy_team

# Configure logging to output to the console
# Render will automatically collect these logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # Remove FileHandler, use StreamHandler
)

app = Flask(__name__)

# ===== PRE-LOADING DATA AND MODELS =====
# These will be loaded once when the application starts
logging.info("Pre-loading data and models at startup...")
try:
    MBM_BAT_FINAL, MBM_BOWL_FINAL, PERF_METRIC_DF, SQUAD_DF = get_data()
    BATTING_MODEL, BOWLING_MODEL, LABEL_ENCODER = load_models()
    logging.info("Data and models loaded successfully.")
except Exception as e:
    logging.critical(f"FATAL: Could not load data or models at startup. Error: {e}")
    # In a real scenario, you might want the app to fail here if models can't load.
    SQUAD_DF = pd.DataFrame() # Set to empty to avoid errors in routes

# ===== FLASK ROUTES =====

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Handles the prediction request from the frontend."""
    try:
        data = request.get_json()
        logging.info(f"Received prediction request with data: {data}")

        input_method = data.get('input_method')
        output_mode = int(data.get('output_mode', 2))
        output_folder = 'Output' # Render has an ephemeral filesystem
        os.makedirs(output_folder, exist_ok=True)

        # --- Process Input ---
        if input_method == 'scraper':
            match_number = int(data.get('match_number'))
            match_df = process_input_scraper(match_number)
        elif input_method == 'custom':
            match_details = data.get('match_details')
            # The create_match_df function is not directly exposed, so let's call the wrapper
            # Assuming process_input_custom handles creation
            match_df = process_input_custom(SQUAD_DF, match_details)
            match_number = int(f"{pd.Timestamp.now().strftime('%y%m%d%H%M')}") # Generate a unique number
        else:
            return jsonify({"error": "Invalid input method"}), 400

        if match_df is None or match_df.empty:
            return jsonify({"error": "Failed to get match details. The scraper might have failed or input was invalid."}), 400

        # --- Run the ML Pipeline (similar to your main.py) ---
        logging.info("Generating test data...")
        test_bat = get_test_bat(MBM_BAT_FINAL, match_df)
        test_bowl = get_test_bowl(MBM_BOWL_FINAL, match_df)
        matchup_df = get_matchup_score(PERF_METRIC_DF, MBM_BOWL_FINAL, match_df, SQUAD_DF)

        logging.info("Running predictions...")
        fp_df = predict_one_match(
            match_number=match_number,
            test_bat_df=test_bat,
            test_bowl_df=test_bowl,
            matchup_df=matchup_df,
            bat_model=BATTING_MODEL,
            bowl_model=BOWLING_MODEL,
            label_encoder=LABEL_ENCODER,
            save_dir=output_folder
        )

        logging.info("Optimising fantasy team...")
        result_df = optimize_fantasy_team(
            match_number=match_number,
            fp_df=fp_df,
            squad_df=SQUAD_DF,
            output_dir=output_folder,
            output_mode=output_mode
        )

        if result_df is None or result_df.empty:
             return jsonify({"error": "Could not generate a team. Please check logs."}), 500

        # Convert result to JSON for the frontend
        result_json = result_df.to_dict(orient='records')
        return jsonify(result_json)

    except Exception as e:
        logging.error(f"An unexpected error occurred in /predict: {str(e)}", exc_info=True)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    # This is for local development only.
    # Gunicorn will be used in production.
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))