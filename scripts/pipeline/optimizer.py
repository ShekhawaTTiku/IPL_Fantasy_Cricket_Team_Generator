import os
import pandas as pd
import pulp

def optimize_team(match_number):
    """
    Optimize fantasy cricket team selection based on merged fantasy points.
    
    Args:
        match_number: Match number to identify which merged file to use
        squad_data_path: Path to the squad data CSV containing player credits, roles, and teams
    """
    # Define file paths
    fp_file = fr"D:\App\FIFS_IPL\fp_predictor_merged\predicted_merged_{match_number}.csv"
    output_dir = r"D:\App\FIFS_IPL\starting_XI"
    squad_data_path=r"D:\App\FIFS_IPL\data\register_data\squadData_ipl25.csv"
    output_file = os.path.join(output_dir, f"team_{match_number}.csv")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    print(f"Starting team optimization for match {match_number}")
    #starting_XI
    try:
        # Read the merged fantasy points CSV
        print(f"Reading fantasy points from {fp_file}")
        fp_df = pd.read_csv(fp_file)
        
        # Read the squad data to get credits, roles, and teams
        print(f"Reading squad data from {squad_data_path}")
        squad_df = pd.read_csv(squad_data_path)
        
        # Convert player ID to string in fp_df to match with key_cricinfo in squad_df
        fp_df['player id'] = fp_df['player id'].astype(str)
        squad_df['key_cricinfo'] = squad_df['key_cricinfo'].astype(str)
        
        # Merge fantasy points with squad data
        print("Merging fantasy points with player information")
        df = pd.merge(
            fp_df,
            squad_df[['key_cricinfo', 'dream11_name', 'credits', 'role', 'team']],
            left_on='player id',
            right_on='key_cricinfo',
            how='inner'
        )
        
        # Check if we have enough players after merging
        if len(df) < 22:  # Need at least 22 players (11 per team) for meaningful selection
            print(f"WARNING: Only {len(df)} players found after merging. May not be enough for optimal team selection.")
        
        # Rename columns to match optimizer's expected format
        df = df.rename(columns={
            'dream11_name': 'player_name',
            'role': 'player_role',
            'team': 'player_team',
            'final_fp': 'final_fp'
        })
        
        # Reset index for PuLP variable creation
        df.reset_index(drop=True, inplace=True)
        
        print(f"Working with {len(df)} players from {df['player_team'].nunique()} teams")
        
        # Create the optimization problem (maximization)
        prob = pulp.LpProblem("starting_XI", pulp.LpMaximize)
        
        # Create a binary decision variable for each player (1 if selected, 0 otherwise)
        players = df.index
        x = pulp.LpVariable.dicts("select", players, cat="Binary")
        
        # Objective: maximize the total final_fp of the selected players
        prob += pulp.lpSum([df.loc[i, "final_fp"] * x[i] for i in players]), "TotalFinalFP"
        
        # Constraint: exactly 11 players are selected
        prob += pulp.lpSum([x[i] for i in players]) == 11, "TotalPlayers"
        
        # Constraint: total credits must not exceed 100
        prob += pulp.lpSum([df.loc[i, "credits"] * x[i] for i in players]) <= 100, "TotalCredits"
        
        # Team Constraint: Choose between 2-9 players from each team
        teams = df["player_team"].unique()
        if len(teams) < 2:
            print("Warning: Less than two teams found in the data.")
            team_A = teams[0]
        else:
            team_A = teams[0]  # Choose the first team as Team A
            print(f"Team A selected as: {team_A}")
            
        team_A_indices = df[df["player_team"] == team_A].index
        prob += pulp.lpSum([x[i] for i in team_A_indices]) >= 1, "TeamA_Min"
        prob += pulp.lpSum([x[i] for i in team_A_indices]) <= 10, "TeamA_Max"
        
        # Role constraints: at least one player for each role WK, BAT, BOWL, ALL
        for role in ["WK", "BAT", "BOWL", "ALL"]:
            role_indices = df[df["player_role"] == role].index
            if len(role_indices) > 0:
                prob += pulp.lpSum([x[i] for i in role_indices]) >= 1, f"Min_{role}"
            else:
                print(f"Warning: No players found with role {role}")
        
        # Solve the optimization problem
        print("Solving optimization problem...")
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        print("Status:", pulp.LpStatus[prob.status])
        if pulp.LpStatus[prob.status] != "Optimal":
            print("No optimal solution found!")
            return
        
        # Extract selected players
        selected_indices = [i for i in players if pulp.value(x[i]) == 1]
        selected_df = df.loc[selected_indices].copy()
        
        # Sort selected players by final_fp in descending order
        selected_df.sort_values("final_fp", ascending=False, inplace=True)
        
        # Assign C/VC: highest final_fp gets "captain", second highest gets "vice captain", others get "player"
        # Initialize all as "player" first
        selected_df["C/VC"] = "player"
        
        # Set captain and vice-captain
        if len(selected_df) >= 1:
            selected_df.iloc[0, selected_df.columns.get_loc("C/VC")] = "captain"
        if len(selected_df) >= 2:
            selected_df.iloc[1, selected_df.columns.get_loc("C/VC")] = "vice captain"
        
        # Prepare output: columns: Player Name, Role, Team, C/VC
        output_df = selected_df[["player_name", "player_role", "player_team", "C/VC"]].copy()
        output_df = output_df.rename(columns={
            "player_name": "Player Name", 
            "player_role": "Role",
            "player_team": "Team"
        })
        
        # Calculate total credits and expected fantasy points (for console output only)
        total_credits = selected_df["credits"].sum()
        captain_fp = selected_df.iloc[0]["final_fp"] * 2  # Captain gets 2x points
        vc_fp = selected_df.iloc[1]["final_fp"] * 1.5     # Vice Captain gets 1.5x points
        regular_fp = selected_df.iloc[2:]["final_fp"].sum()
        total_fp = captain_fp + vc_fp + regular_fp
        
        
        # Save the output CSV with 4 columns as requested
        output_df.to_csv(output_file, index=False)
        print(f"Optimized team saved to {output_file}")
        print(f"Team summary:")
        print(f"  Total players: {len(output_df)}")
        print(f"  Total credits used: {total_credits}")
        print(f"  Expected fantasy points: {total_fp:.2f}")
        print(f"  Captain: {output_df.iloc[0]['Player Name']} ({selected_df.iloc[0]['final_fp']:.2f} points)")
        print(f"  Vice Captain: {output_df.iloc[1]['Player Name']} ({selected_df.iloc[1]['final_fp']:.2f} points)")
        print(f"  Team composition:")
        role_counts = output_df["Role"].value_counts()
        for role, count in role_counts.items():
            print(f"    {role}: {count}")
        team_counts = output_df["Team"].value_counts()
        for team, count in team_counts.items():
            print(f"    {team}: {count}")

        print("\nSelected Team:")
        print(output_df)
        
    except FileNotFoundError as e:
        print(f"ERROR: File not found - {e}")
    except Exception as e:
        print(f"ERROR: Failed to optimize team: {str(e)}")
        import traceback
        traceback.print_exc()