import joblib
from pycaret.regression import load_model


def load_models_and_encoders():
    """Load machine learning models and encoders."""
    try:
        print("Loading batting model...")
        batting_model = load_model(r"D:\App\FIFS_IPL\Testing_model\flaml_final\modelsbatting_model_flaml")
        print("Batting model loaded successfully")
    except Exception as e:
        print(f"Error loading batting model: {e}")
        raise

    try:
        print("Loading bowling model...")
        bowling_model = load_model(r"D:\App\FIFS_IPL\Testing_model\flaml_final\modelsbowling_model_flaml")
        print("Bowling model loaded successfully")

        # Extract required columns for bowling model to check later
        if hasattr(bowling_model, 'feature_names_'):
            required_bowling_columns = bowling_model.feature_names_
            print(f"Bowling model requires these columns: {required_bowling_columns}")
        else:
            print("Could not determine required columns for bowling model")

    except Exception as e:
        print(f"Error loading bowling model: {e}")
        raise

    try:
        label_encoder = joblib.load(r'D:\App\FIFS_IPL\Testing_model\flaml_final\label_encoders_flaml.joblib')
        print("Label encoder loaded successfully")
        print(f"Label encoder type: {type(label_encoder)}")
        if hasattr(label_encoder, 'classes_'):
            print(f"Classes: {label_encoder.classes_}")
        elif isinstance(label_encoder, dict):
            print(f"Encoder keys: {list(label_encoder.keys())}")
    except Exception as e:
        print(f"Error loading label encoder: {e}")
        raise

    return batting_model, bowling_model, label_encoder