import os
import logging
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load env early so downstream modules see env vars
load_dotenv()

# Import your project code
from scripts.data_loading import get_data
from scripts.model_loading import load_models
from scripts.input_module import (
    VALID_TEAMS, VALID_VENUES,
    process_input_custom, process_input_scraper
)
from scripts.test_data_gen_bat import get_test_bat
from scripts.test_data_gen_bowl import get_test_bowl
from scripts.test_data_gen_matchup import get_matchup_score
from scripts.predict_match import predict_one_match
from scripts.optimiser import optimize_fantasy_team

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

st.set_page_config(page_title="Fantasy Cricket Team Generator (Streamlit)", page_icon="🏏", layout="centered")

st.title("Fantasy Cricket Team Generator")
st.caption("Streamlit interface for the FIFS_IPL pipeline")

# Cache heavy resources
@st.cache_resource(show_spinner=True)
def _cached_data():
    return get_data()

@st.cache_resource(show_spinner=True)
def _cached_models():
    return load_models()

def env_checks():
    errs = []
    if not os.getenv("HUGGING_FACE_TOKEN"):
        errs.append("HUGGING_FACE_TOKEN is missing (required for loading models).")
    if not os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL"):
        errs.append("GOOGLE_SERVICE_ACCOUNT_EMAIL is missing (required for Google Sheets).")
    if not os.getenv("GOOGLE_PRIVATE_KEY"):
        errs.append("GOOGLE_PRIVATE_KEY is missing (required for Google Sheets).")
    if not os.getenv("GOOGLE_SHEET_ID_MAPPING"):
        errs.append("GOOGLE_SHEET_ID_MAPPING is missing (ID mapping sheet).")
    if not os.getenv("GOOGLE_SHEET_ID_BAT"):
        errs.append("GOOGLE_SHEET_ID_BAT is missing (batting MBM sheet).")
    if not os.getenv("GOOGLE_SHEET_ID_BOWL"):
        errs.append("GOOGLE_SHEET_ID_BOWL is missing (bowling MBM sheet).")
    return errs

with st.expander("Environment status", expanded=False):
    issues = env_checks()
    if issues:
        for e in issues:
            st.error(e)
    else:
        st.success("All required environment variables found.")

# Sidebar controls
st.sidebar.header("Input Settings")
input_method = st.sidebar.selectbox("Input Method", ["Scraper", "Custom"], index=0)
output_mode_label = st.sidebar.selectbox("Output Mode", ["Best XI", "Best XI + Backups", "Player Rankings"], index=1)
output_mode = {"Best XI": 1, "Best XI + Backups": 2, "Player Rankings": 3}[output_mode_label]

if input_method == "Scraper":
    match_number = st.sidebar.number_input("Match Number (from Cricbuzz fixtures)", min_value=1, step=1, value=1)
else:
    # Custom inputs
    team1 = st.sidebar.selectbox("Team 1", VALID_TEAMS, index=0)
    team2_options = [t for t in VALID_TEAMS if t != team1]
    # Ensure a stable default for team2
    default_team2_idx = 0 if team2_options[0] != team1 else (1 if len(team2_options) > 1 else 0)
    team2 = st.sidebar.selectbox("Team 2", team2_options, index=default_team2_idx)

    venue = st.sidebar.selectbox("Venue", VALID_VENUES, index=0)
    toss_winner = st.sidebar.selectbox("Toss Winner", [team1, team2], index=0)
    toss_decision = st.sidebar.radio("Toss Decision", ["bat", "field"], index=0)

st.sidebar.header("Actions")
reload_clicked = st.sidebar.button("Reload Data/Models (clear cache)")
if reload_clicked:
    _cached_data.clear()
    _cached_models.clear()
    st.sidebar.success("Caches cleared. They will reload on next run.")

run_clicked = st.sidebar.button("Generate Team", type="primary")

def run_pipeline(input_method: str, output_mode: int):
    # Load data/models (cached)
    with st.status("Loading data and models...", expanded=False) as status:
        mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df = _cached_data()
        batting_model, bowling_model, label_encoder = _cached_models()
        status.update(label="Data and models ready", state="complete")

    if squad_df is None or batting_model is None:
        st.error("Server error: Could not load necessary data or models. Check logs and env.")
        return

    # Build match_df
    if input_method == "Scraper":
        st.info(f"Using scraper for match number: {match_number}")
        match_df = process_input_scraper(int(match_number))
    else:
        if team1 == team2:
            st.error("Team 1 and Team 2 cannot be the same.")
            return
        match_details = {
            "team1": team1,
            "team2": team2,
            "venue": venue,
            "toss_winner": toss_winner,
            "toss_decision": toss_decision,
        }
        st.info(f"Using custom input: {match_details}")
        match_df = process_input_custom(squad_df, match_details)
        # Generate unique match number for custom runs
        match_num_str = pd.Timestamp.now().strftime("%y%m%d%H%M")
        match_num_int = int(match_num_str)
    if match_df is None or match_df.empty:
        st.error("Failed to get match details. Scraper might have failed or input invalid.")
        return

    # Display match_df preview
    with st.expander("Match details (preview)"):
        st.dataframe(match_df, use_container_width=True, hide_index=True)

    # Compute test data, predictions and optimize
    with st.spinner("Generating test data..."):
        try:
            test_bat = get_test_bat(mbm_bat_final, match_df)
            test_bowl = get_test_bowl(mbm_bowl_final, match_df)
            matchup_df = get_matchup_score(perf_metric_df, mbm_bowl_final, match_df, squad_df)
        except Exception as e:
            st.error(f"Error in test data generation: {e}")
            return

    with st.spinner("Running predictions..."):
        try:
            out_dir = "Output"
            os.makedirs(out_dir, exist_ok=True)
            fp_df = predict_one_match(
                match_number=(int(match_number) if input_method == "Scraper" else match_num_int),
                test_bat_df=test_bat,
                test_bowl_df=test_bowl,
                matchup_df=matchup_df,
                bat_model=batting_model,
                bowl_model=bowling_model,
                label_encoder=label_encoder,
                save_dir=out_dir
            )
        except Exception as e:
            st.error(f"Prediction error: {e}")
            return

    with st.spinner("Optimizing fantasy team..."):
        try:
            result_df = optimize_fantasy_team(
                match_number=(int(match_number) if input_method == "Scraper" else match_num_int),
                fp_df=fp_df,
                squad_df=squad_df,
                output_dir="Output",
                output_mode=output_mode
            )
        except Exception as e:
            st.error(f"Optimization error: {e}")
            return

    if result_df is None or result_df.empty:
        st.error("No results produced.")
        return

    st.success("Team generated successfully!")
    st.subheader("Results")
    st.dataframe(result_df, use_container_width=True, hide_index=True)

    # Download result
    csv_bytes = result_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv_bytes, file_name="team_selection.csv", mime="text/csv")

    # Optional: show intermediate outputs
    with st.expander("Prediction outputs (merged)", expanded=False):
        st.dataframe(fp_df, use_container_width=True, hide_index=True)

# Main action
if run_clicked:
    try:
        run_pipeline(input_method, output_mode)
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        logging.exception("Streamlit pipeline error")
else:
    st.info("Configure inputs in the sidebar and click 'Generate Team'." )