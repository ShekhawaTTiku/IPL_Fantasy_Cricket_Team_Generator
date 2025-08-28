import joblib
from pycaret.regression import load_model
import logging
from huggingface_hub import hf_hub_download
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def load_bat_model(bat_model_path):
    """
    Load the batting model from a specified path.
    """
    try:
        # Pass the path directly to load_model, don't open the file first
        model = load_model(bat_model_path)
        return model
    except Exception as e:
        logging.error(f"Error loading batting model: {e}")
        return None


def load_bowl_model(bowl_model_path):
    """
    Load the bowling model from a specified path.
    """
    try:
        # Pass the path directly to load_model, don't open the file first
        model = load_model(bowl_model_path)
        return model
    except Exception as e:
        logging.error(f"Error loading bowling model: {e}")
        return None


def load_label_encoder(encoder_path):
    """
    Load the label encoder from a specified path.

    Parameters:
    -----------
    encoder_path : str
        Path to the label encoder file.

    Returns:
    --------
    encoder : object
        The loaded label encoder.
    """
    try:
        label_encoder = joblib.load(encoder_path)
        return label_encoder

    except Exception as e:
        logging.error(f"Error loading label encoder: {e}")
        return None


def load_models():
    """
    Downloads and loads batting, bowling, and label encoder models from a private Hugging Face Hub repository.

    Returns:
    --------
    batting_model : object
        The loaded batting model.
    bowling_model : object
        The loaded bowling model.
    label_encoder : object
        The loaded label encoder.
    """
    HF_REPO_ID = "s1nghayush/FIFS_IPL"
    BATTING_MODEL_FILENAME = "batting_model_pycaret.pkl"
    BOWLING_MODEL_FILENAME = "bowling_model_pycaret.pkl"
    ENCODER_FILENAME = "label_encoders.joblib"
    HF_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

    if not HF_TOKEN:
        logging.error("Hugging Face token not found. Please create a .env file and set the HUGGING_FACE_TOKEN variable.")
        exit(1)

    try:
        logging.info(f"Downloading models from Hugging Face repository: {HF_REPO_ID}")

        # Download and load batting model using the auth token
        bat_model_path_pkl = hf_hub_download(repo_id=HF_REPO_ID, filename=BATTING_MODEL_FILENAME, token=HF_TOKEN)
        bat_model_path = bat_model_path_pkl.replace(".pkl", "")
        batting_model = load_bat_model(bat_model_path)
        if batting_model is None:
            logging.error("Failed to load batting model")
            exit(1)

        # Download and load bowling model using the auth token
        bowl_model_path_pkl = hf_hub_download(repo_id=HF_REPO_ID, filename=BOWLING_MODEL_FILENAME, token=HF_TOKEN)
        bowl_model_path = bowl_model_path_pkl.replace(".pkl", "")
        bowling_model = load_bowl_model(bowl_model_path)
        if bowling_model is None:
            logging.error("Failed to load bowling model")
            exit(1)

        # Download and load label encoder using the auth token
        encoder_path = hf_hub_download(repo_id=HF_REPO_ID, filename=ENCODER_FILENAME, token=HF_TOKEN)
        label_encoder = load_label_encoder(encoder_path)
        if label_encoder is None:
            logging.error("Failed to load label encoder")
            exit(1)

        logging.info("All models downloaded and loaded successfully from Hugging Face Hub.")
        return batting_model, bowling_model, label_encoder

    except Exception as e:
        logging.error(f"Error loading models from Hugging Face Hub: {e}")
        exit(1)