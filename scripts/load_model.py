import joblib
import os
from pycaret.regression import load_model

def load_bat_model(bat_model_path):
    """
    Load the batting model from a specified path.
    """
    try:
        # Pass the path directly to load_model, don't open the file first
        model = load_model(bat_model_path)
        print(f"Batting model loaded successfully from {bat_model_path}")
        return model
    except Exception as e:
        print(f"Error loading batting model: {e}")
        return None


def load_bowl_model(bowl_model_path):
    """
    Load the bowling model from a specified path.
    """
    try:
        # Pass the path directly to load_model, don't open the file first
        model = load_model(bowl_model_path)
        print(f"Bowling model loaded successfully from {bowl_model_path}")
        return model
    except Exception as e:
        print(f"Error loading bowling model: {e}")
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
        print(f"Label encoder loaded successfully from {encoder_path}")
        return label_encoder

    except Exception as e:
        print(f"Error loading label encoder: {e}")
        return None


def load_model_pycaret():
    """
    Load both batting and bowling models using PyCaret.
    Paths are determined internally using os module.

    Returns:
    --------
    batting_model : object
        The loaded batting model.
    bowling_model : object
        The loaded bowling model.
    label_encoder : object
        The loaded label encoder.
    """
    try:
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one directory to the project root
        project_root = os.path.dirname(script_dir)

        # Define model directory paths using project root
        model_dir = os.path.join(project_root, 'model')
        bat_model_path = os.path.join(model_dir, 'batting_model_pycaret')
        bowl_model_path = os.path.join(model_dir, 'bowling_model_pycaret')
        encoder_path = os.path.join(model_dir, 'label_encoders.joblib')

        print(
            f"Using paths: \nBatting model: {bat_model_path} \nBowling model: {bowl_model_path} \nEncoder: {encoder_path}")

        # Load batting model
        batting_model = load_bat_model(bat_model_path)
        if batting_model is None:
            print("Failed to load batting model")
            exit(1)

        # Load bowling model
        bowling_model = load_bowl_model(bowl_model_path)
        if bowling_model is None:
            print("Failed to load bowling model")
            exit(1)

        # Load label encoder
        label_encoder = load_label_encoder(encoder_path)
        if label_encoder is None:
            print("Failed to load label encoder")
            exit(1)

        print("All models loaded successfully")
        return batting_model, bowling_model, label_encoder

    except Exception as e:
        print(f"Error loading models: {e}")
        exit(1)