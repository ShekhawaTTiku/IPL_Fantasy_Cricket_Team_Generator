import logging
import os
from scripts.test_data_gen_bat import get_test_bat
from scripts.test_data_gen_bowl import get_test_bowl
from scripts.test_data_gen_matchup import get_matchup_score
from scripts.predict_match import predict_one_match
from scripts.data_loading import get_data
from scripts.model_loading import load_models
from scripts.output_module import get_output_mode
from scripts.input_module import (get_input_method, process_input)
from scripts.optimiser import optimize_fantasy_team

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fantasy_team.log'),
        logging.StreamHandler()
    ]
)

def main():
    """Main function to run the fantasy team optimization process."""
    try:
        logging.info("Starting fantasy team optimization process")

        # =====MAKING DIRECTORIES=====
        output_folder = 'Output'
        os.makedirs(output_folder, exist_ok=True)

        # =====FETCHING GOOGLE SHEET DATA=====
        logging.info("Fetching data from Google Sheets")
        mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df = get_data()

        # =====GET INPUT METHOD=====
        input_method = get_input_method()
        match_df, match_number = process_input(input_method, squad_df)

        # =====TEST DATA GENERATION=====
        logging.info("Generating test data")
        try:
            test_bat = get_test_bat(mbm_bat_final, match_df)
            test_bowl = get_test_bowl(mbm_bowl_final, match_df)
            matchup_df = get_matchup_score(perf_metric_df, mbm_bowl_final, match_df, squad_df)
        except Exception as e:
            logging.error(f"Error in test data generation: {str(e)}")
            return

        # =====MODEL LOADING=====
        logging.info("Loading ML models")
        try:
            batting_model, bowling_model, label_encoder = load_models()
        except Exception as e:
            logging.error(f"Error in loading models: {str(e)}")
            return

        # =====MODEL PREDICTION=====
        logging.info("Running predictions")
        try:
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
        except Exception as e:
            logging.error(f"Error in prediction: {str(e)}")
            print("Failed to generate predictions. Please try again.")
            return

        # =====OUTPUT MODE SELECTION=====
        logging.info("Selecting output mode")
        output_mode = get_output_mode()

        # =====OPTIMISATION=====
        logging.info(f"Processing output mode {output_mode}")
        try:
            result  = optimize_fantasy_team(
                match_number=match_number,
                fp_df=fp_df,
                squad_df=squad_df,
                output_dir=output_folder,
                output_mode=output_mode
            )

            if result is not None:
                logging.info("Team selection completed successfully")
                logging.info(f"Results have been saved in the {output_folder} directory.")

        except Exception as e:
            logging.error(f"Error in optimising team: {str(e)}")
            return

    except Exception as e:
        logging.error(f"Unexpected error in main process: {str(e)}")
        print("An unexpected error occurred. Please check the logs for details.")
        return

if __name__ == "__main__":
    main()