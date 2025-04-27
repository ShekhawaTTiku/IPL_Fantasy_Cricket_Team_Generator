import streamlit as st
import pandas as pd
import time

# Import necessary modules from your project
from scripts.match_scraper import get_match_urls, get_today_details
from scripts.backup_match_scraper import backup_match_scrapping
from scripts.google_sheet_data_fetch import get_data_from_google_sheet
from scripts.test_data_gen_bat import get_test_bat
from scripts.test_data_gen_bowl import get_test_bowl
from scripts.test_data_gen_matchup import get_matchup_score
from scripts.load_model import load_model_pycaret
from scripts.predict_match import predict_one_match
from scripts.optimiser import optimize_fantasy_team

st.set_page_config(page_title="IPL Fantasy Team Predictor", layout="wide")

# Title and description
st.title("IPL 2025 Fantasy Team Predictor")
st.markdown("""
This application predicts optimal fantasy teams for IPL 2025 matches based on historical data and machine learning.
""")

# Sidebar with match selection
st.sidebar.header("Match Selection")


# Function to get available matches - no caching as requested
def get_available_matches():
    try:
        matches = get_match_urls()
        return matches
    except Exception as e:
        st.error(f"Error fetching matches: {e}")
        return []


# Get available matches
with st.spinner("Fetching available matches..."):
    matches = get_available_matches()

if matches:
    # Create a dropdown to select match by number
    match_options = [f"Match {i + 1}: {match.split('/')[-1].replace('-', ' ').title()}"
                     for i, match in enumerate(matches)]
    selected_match = st.sidebar.selectbox("Select Match", match_options)
    match_number = int(selected_match.split(":")[0].replace("Match ", ""))

    st.sidebar.markdown("**OR**")

    # Manual entry for match number
    manual_match_number = st.sidebar.number_input("Enter Match Number Manually",
                                                  min_value=1,
                                                  max_value=100,
                                                  value=match_number)

    # Use the manually entered number if different
    if manual_match_number != match_number:
        match_number = manual_match_number

    # Checkbox for using backup scraper
    use_backup = st.sidebar.checkbox("Use Backup Scraper",
                                     help="Use the backup match scraper if the primary one fails")

    # Button to run prediction
    run_prediction = st.sidebar.button("Run Prediction", type="primary")

    # Main content
    if run_prediction:
        # Create tabs for different outputs
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            ["Match Details", "Player Stats", "Predictions", "Optimized Team", "Logs"])

        with tab5:
            log_placeholder = st.empty()


        # Helper function to update logs
        def update_log(message):
            with log_placeholder.container():
                st.markdown(f"**{time.strftime('%H:%M:%S')}** - {message}")


        # Step 1: Always fetch Google Sheet data (no caching)
        with tab1:
            st.header("Match Details")
            update_log("Fetching data from Google Sheets...")

            # Always fetch fresh data from Google Sheets as requested
            mbm_bat_final, mbm_bowl_final, perf_metric_df, squad_df = get_data_from_google_sheet()

            # Step 2: Scrape match details
            update_log(f"Fetching details for match {match_number}...")

            try:
                if use_backup:
                    update_log("Using backup match scraper...")
                    match_df = backup_match_scrapping(match_number)
                else:
                    match_df = get_today_details(match_number)

                    # If primary scraper fails, try backup
                    if match_df is None or match_df.empty:
                        update_log("Primary scraper failed. Trying backup scraper...")
                        match_df = backup_match_scrapping(match_number)

                if match_df is None or match_df.empty:
                    st.error("Failed to fetch match details. Please try again.")
                    update_log("ERROR: Failed to fetch match details.")
                    st.stop()

                # Display match details
                teams = match_df['Team'].unique()
                venue = match_df['Venue'].iloc[0]
                date = match_df['Date'].iloc[0]

                col1, col2, col3 = st.columns(3)
                col1.metric("Home Team", teams[0])
                col2.metric("Away Team", teams[1])
                col3.metric("Venue", venue)

                st.subheader("Match Squads")
                team1_df = match_df[match_df['Team'] == teams[0]][['Player Name', 'Team', 'Innings']]
                team2_df = match_df[match_df['Team'] == teams[1]][['Player Name', 'Team', 'Innings']]

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**{teams[0]} Squad**")
                    st.dataframe(team1_df, hide_index=True)

                with col2:
                    st.write(f"**{teams[1]} Squad**")
                    st.dataframe(team2_df, hide_index=True)

            except Exception as e:
                st.error(f"Error fetching match details: {str(e)}")
                update_log(f"ERROR: {str(e)}")
                st.stop()

        # Step 3: Generate test data
        with tab2:
            st.header("Player Statistics")

            try:
                update_log("Generating batting test data...")
                test_bat = get_test_bat(mbm_bat_final, match_df)

                update_log("Generating bowling test data...")
                test_bowl = get_test_bowl(mbm_bowl_final, match_df)

                update_log("Calculating matchup scores...")
                matchup_df = get_matchup_score(perf_metric_df, mbm_bowl_final, match_df, squad_df)

                # Display stats
                st.subheader("Batting Statistics")
                st.dataframe(test_bat.head(), use_container_width=True)

                st.subheader("Bowling Statistics")
                st.dataframe(test_bowl.head(), use_container_width=True)

                st.subheader("Matchup Scores")
                st.dataframe(matchup_df, use_container_width=True)

                update_log("Test data generation completed.")

            except Exception as e:
                st.error(f"Error generating test data: {str(e)}")
                update_log(f"ERROR: {str(e)}")
                st.stop()

        # Step 4: Load models and make predictions
        with tab3:
            st.header("Predictions")

            try:
                update_log("Loading prediction models...")
                batting_model, bowling_model, label_encoder = load_model_pycaret()

                update_log("Making predictions...")
                fp_df = predict_one_match(
                    match_number=match_number,
                    bat_model=batting_model,
                    bowl_model=bowling_model,
                    test_bat_df=test_bat,
                    test_bowl_df=test_bowl,
                    matchup_df=matchup_df,
                    label_encoder=label_encoder,
                    save_dir="Output"  # This is just a placeholder as we're not saving files
                )

                # Display predictions
                st.subheader("Predicted Fantasy Points")
                st.dataframe(fp_df.sort_values('total_fp', ascending=False), use_container_width=True)

                update_log("Predictions completed.")

            except Exception as e:
                st.error(f"Error making predictions: {str(e)}")
                update_log(f"ERROR: {str(e)}")
                st.stop()

        # Step 5: Optimize team
        with tab4:
            st.header("Optimized Fantasy Team")

            try:
                update_log("Optimizing fantasy team...")
                optimized_team = optimize_fantasy_team(
                    match_number=match_number,
                    fp_df=fp_df,
                    squad_df=squad_df,
                    output_dir="Output"  # This is just a placeholder as we're not saving files
                )

                # Display optimized team
                st.subheader("Selected Team")

                # Sort by role for display - using the actual values in your data
                role_order = {'captain': 0, 'vice captain': 1, 'player': 2}
                optimized_team['role_order'] = optimized_team['C/VC'].map(role_order)
                display_team = optimized_team.sort_values('role_order')

                # Drop the ordering column
                display_team = display_team.drop(columns=['role_order'])

                # Display the team
                st.dataframe(display_team, use_container_width=True)

                # Team visualization
                st.subheader("Team Composition")
                role_counts = optimized_team['Role'].value_counts()
                st.bar_chart(role_counts)

                # Team distribution by actual cricket teams
                st.subheader("Team Distribution")
                team_counts = optimized_team['Team'].value_counts()
                st.bar_chart(team_counts)

                update_log("Team optimization completed.")

            except Exception as e:
                st.error(f"Error optimizing team: {str(e)}")
                update_log(f"ERROR: {str(e)}")
                st.stop()

else:
    st.warning("Could not fetch match list. Please check your internet connection or try again later.")