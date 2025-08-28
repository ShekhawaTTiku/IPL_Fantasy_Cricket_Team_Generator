from flask import Flask, request, jsonify, render_template
import logging
import os
import pandas as pd
from scripts.test_data_gen_bat import get_test_bat
from scripts.test_data_gen_bowl import get_test_bowl
from scripts.test_data_gen_matchup import get_matchup_score
from scripts.predict_match import predict_one_match
from scripts.data_loading import get_data
from scripts.model_loading import load_models
from scripts.optimiser import optimize_fantasy_team
from scripts.input_module import process_input_custom, process_input_scraper, generate_match_number

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fantasy_team.log'),
        logging.StreamHandler()
    ]
)

# ===== GLOBAL VARIABLES =====
# To avoid reloading data and models on every request, we load them once when the app starts.
mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df = None, None, None, None
batting_model, bowling_model, label_encoder = None, None, None

def load_initial_data():
    """Load all necessary data and models into global variables."""
    global mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df
    global batting_model, bowling_model, label_encoder

    logging.info("Loading initial data and models for the Flask app...")
    # =====FETCHING GOOGLE SHEET DATA=====
    mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df = get_data()

    # =====MODEL LOADING=====
    batting_model, bowling_model, label_encoder = load_models()
    logging.info("Initial data and models loaded successfully.")

@app.route('/')
def index():
    """Render the main page with the input form."""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """API endpoint to generate fantasy team predictions."""
    try:
        data = request.get_json()
        input_method = data.get('input_method')
        output_mode = int(data.get('output_mode', 2)) # Default to Best XI + Backups

        if not input_method:
            return jsonify({"error": "Input method not specified."}), 400

        if input_method == 'scraper':
            match_number = int(data.get('match_number'))
            match_df = process_input_scraper(match_number)
        elif input_method == 'custom':
            match_details = data.get('match_details')
            match_df = process_input_custom(squad_df, match_details)
            match_number = generate_match_number()
        else:
            return jsonify({"error": "Invalid input method."}), 400

        if match_df is None or match_df.empty:
            return jsonify({"error": "Failed to process match details."}), 500

        # =====TEST DATA GENERATION=====
        logging.info("Generating test data")
        test_bat = get_test_bat(mbm_bat_final, match_df)
        test_bowl = get_test_bowl(mbm_bowl_final, match_df)
        matchup_df = get_matchup_score(perf_metric_df, mbm_bowl_final, match_df, squad_df)

        # =====MODEL PREDICTION=====
        logging.info("Running predictions")
        output_folder = 'Output'
        os.makedirs(output_folder, exist_ok=True)
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

        # =====OPTIMISATION=====
        logging.info(f"Optimizing team for match {match_number}")
        result_df = optimize_fantasy_team(
            match_number=match_number,
            fp_df=fp_df,
            squad_df=squad_df,
            output_dir=output_folder,
            output_mode=output_mode
        )

        if result_df is not None and not result_df.empty:
            logging.info("Team selection completed successfully")
            return jsonify(result_df.to_dict(orient='records'))
        else:
            return jsonify({"error": "Failed to generate fantasy team."}), 500

    except Exception as e:
        logging.error(f"An error occurred during prediction: {str(e)}")
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    load_initial_data()
    app.run(debug=True)