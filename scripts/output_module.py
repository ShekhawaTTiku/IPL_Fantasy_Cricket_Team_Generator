import logging
from scripts.optimiser import optimize_fantasy_team
import pandas as pd
import os

def get_output_mode():
    """Get the user's preferred output mode."""
    while True:
        print("\nChoose output mode:")
        print("1. BEST XI")
        print("2. BEST XI + BACKUPS")
        print("3. RANKINGS")
        try:
            choice = int(input("Enter your choice (1, 2, or 3): "))
            if choice in [1, 2, 3]:
                return choice
            else:
                logging.warning("Invalid output mode choice entered")
        except ValueError:
            logging.warning("Non-numeric output mode choice entered")

def process_output_mode(mode, match_number, fp_df, squad_df, output_dir):
    """Process the selected output mode."""
    logging.info(f"Processing output mode: {mode}")

    if mode == 1:
        # Best XI
        try:
            return optimize_fantasy_team(
                match_number=match_number,
                fp_df=fp_df,
                squad_df=squad_df,
                output_dir=output_dir,
                output_mode=1
            )
        except Exception as e:
            logging.error(f"Error in team optimization, output mode 1: {str(e)}")

    elif mode == 2:
        # Best XI + Backups (Current Implementation)
        try:
            return optimize_fantasy_team(
                match_number=match_number,
                fp_df=fp_df,
                squad_df=squad_df,
                output_dir=output_dir,
                output_mode=2
            )
        except Exception as e:
            logging.error(f"Error in team optimization, output mode 2: {str(e)}")
            raise

    else:  # mode == 3
        # Player Rankings
        try:
            # Merge fantasy points with squad info to get player roles
            rankings = fp_df.merge(
                squad_df[['key_cricinfo', 'dream11_name', 'role', 'team', 'credits']],
                left_on='player_id',
                right_on='key_cricinfo',
                how='left'
            )

            # Select and rename columns for output
            rankings = rankings[[
                'dream11_name',
                'role',
                'team',
                'credits',
                'total_fp'  # Assuming this is the predicted fantasy points column
            ]].rename(columns={
                'dream11_name': 'Player Name',
                'role': 'Role',
                'team': 'Team',
                'credits': 'Credits',
                'total_fp': 'Predicted Points'
            })

            # Sort by predicted points in descending order
            rankings = rankings.sort_values('Predicted Points', ascending=False)

            # Save rankings to CSV
            output_file = os.path.join(output_dir, f"rankings_match_{match_number}.csv")
            rankings.to_csv(output_file, index=False)

            # Display top 10 rankings
            print("\nTop 10 Players by Predicted Points:")
            print("===================================")
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(rankings.head(10).to_string(index=False))
            print(f"\nComplete rankings have been saved to: {output_file}")

            return rankings

        except Exception as e:
            logging.error(f"Error generating rankings: {str(e)}")
            raise

