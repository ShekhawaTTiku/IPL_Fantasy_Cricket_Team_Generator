import os
import pandas as pd
import pulp

def optimize_fantasy_team(
    match_number: int,
    fp_df: pd.DataFrame,
    squad_df: pd.DataFrame,
    output_dir: str
) -> pd.DataFrame:
    """
    Optimizes a fantasy cricket team using total fantasy points and squad data.

    Args:
        match_number (int): Match number used for file naming.
        fp_df (pd.DataFrame): DataFrame of merged fantasy points with columns 'player_id' and 'total_fp'.
        squad_df (pd.DataFrame): DataFrame of squad details with 'key_cricinfo', 'dream11_name', 'credits', 'role', 'team'.
        output_dir (str): Directory to save the output team CSV.

    Returns:
        pd.DataFrame: Optimized team DataFrame with columns - Player Name, Role, Team, C/VC.
    """
    try:
        # Ensure correct column exists
        if 'player_id' not in fp_df.columns or 'total_fp' not in fp_df.columns:
            raise KeyError("fp_df must contain 'player_id' and 'total_fp' columns")

        # Normalize ID types
        fp_df['player_id'] = fp_df['player_id'].astype(str)
        squad_df['key_cricinfo'] = squad_df['key_cricinfo'].astype(str)

        # Merge points with squad info
        df = pd.merge(
            fp_df[['player_id', 'total_fp']],
            squad_df[['key_cricinfo', 'dream11_name', 'credits', 'role', 'team']],
            left_on='player_id',
            right_on='key_cricinfo',
            how='inner'
        )
        if df.empty or len(df) < 11:
            raise ValueError("Not enough players available for optimization.")

        df = df.rename(columns={
            'dream11_name': 'player_name',
            'role': 'player_role',
            'team': 'player_team'
        }).reset_index(drop=True)

        # Setup LP problem
        prob = pulp.LpProblem("starting_XI", pulp.LpMaximize)
        players = df.index.tolist()
        x = pulp.LpVariable.dicts("select", players, cat="Binary")

        # Objective: maximize total_fp
        prob += pulp.lpSum(df.loc[i, 'total_fp'] * x[i] for i in players), "TotalFP"

        # Exact 11 players
        prob += pulp.lpSum(x[i] for i in players) == 11, "TotalPlayers"
        # Credit cap
        prob += pulp.lpSum(df.loc[i, 'credits'] * x[i] for i in players) <= 100, "TotalCredits"

        # Team constraints: min 1, max 10 from each team
        for team in df['player_team'].unique():
            idx = df[df['player_team'] == team].index.tolist()
            prob += pulp.lpSum(x[i] for i in idx) >= 1, f"Min_{team}"
            prob += pulp.lpSum(x[i] for i in idx) <= 10, f"Max_{team}"

        # Role constraints: at least 1 WK, 1 BOWL, 1 ALL, and combined BAT+ALL >= 5
        # Single-role minima
        for role in ['WK', 'BOWL', 'ALL']:
            idx = df[df['player_role'] == role].index.tolist()
            prob += pulp.lpSum(x[i] for i in idx) >= 1, f"Min_{role}"
        # Combined BAT+ALL
        bat_all_idx = df[df['player_role'].isin(['BAT','ALL'])].index.tolist()
        prob += pulp.lpSum(x[i] for i in bat_all_idx) >= 5, "Min_BAT_ALL"

        # Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[prob.status] != 'Optimal':
            raise RuntimeError("No optimal solution found.")

        # Selected players
        sel = [i for i in players if pulp.value(x[i]) == 1]
        selected = df.loc[sel].copy().sort_values('total_fp', ascending=False)

        # Assign C/VC
        selected['C/VC'] = 'player'
        if len(selected) > 0:
            selected.iloc[0, selected.columns.get_loc('C/VC')] = 'captain'
        if len(selected) > 1:
            selected.iloc[1, selected.columns.get_loc('C/VC')] = 'vice captain'

        out = selected[['player_name','player_role','player_team','C/VC']].rename(columns={
            'player_name':'Player Name',
            'player_role':'Role',
            'player_team':'Team'
        })

        # Save CSV
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(f"output_team_match_no_{match_number}.csv")
        out.to_csv(path, index=False)
        print(f"Optimized team saved to {path}")
        return out

    except Exception as e:
        print(f"ERROR in optimize_fantasy_team: {e}")
        import traceback; traceback.print_exc()
        return pd.DataFrame()
