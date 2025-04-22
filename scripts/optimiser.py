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
        if df.empty or len(df) < 15:
            raise ValueError("Not enough players available for optimization.")

        df = df.rename(columns={
            'dream11_name': 'player_name',
            'role': 'player_role',
            'team': 'player_team'
        }).reset_index(drop=True)

        # Setup LP problem
        prob = pulp.LpProblem("starting_XV", pulp.LpMaximize)
        players = df.index.tolist()

        # Create variables for selecting players
        x = pulp.LpVariable.dicts("select", players, cat="Binary")

        # Create variables for top 11 players
        top11 = pulp.LpVariable.dicts("top11", players, cat="Binary")

        # Objective: maximize total_fp with higher weight to top 11
        prob += pulp.lpSum(df.loc[i, 'total_fp'] * (2 * top11[i] + x[i]) for i in players), "TotalFP"

        # Exactly 15 players selected in total
        prob += pulp.lpSum(x[i] for i in players) == 15, "TotalPlayers"

        # Exactly 11 players in top 11
        prob += pulp.lpSum(top11[i] for i in players) == 11, "Top11Players"

        # Every player in top 11 must be selected
        for i in players:
            prob += top11[i] <= x[i], f"Top11_Selected_{i}"

        # Credit cap - ONLY FOR TOP 11 PLAYERS
        prob += pulp.lpSum(df.loc[i, 'credits'] * top11[i] for i in players) <= 100, "TotalCredits"

        # Team constraints: min 1, max 10 from each team
        for team in df['player_team'].unique():
            idx = df[df['player_team'] == team].index.tolist()
            prob += pulp.lpSum(x[i] for i in idx) >= 1, f"Min_{team}"
            prob += pulp.lpSum(x[i] for i in idx) <= 10, f"Max_{team}"

        # Constraints for top 11
        # At least 1 WK, 1 ALL, 1 BOWL in top 11
        for role in ['WK', 'ALL', 'BOWL']:
            idx = df[df['player_role'] == role].index.tolist()
            prob += pulp.lpSum(top11[i] for i in idx) >= 1, f"Min_Top11_{role}"

        # At least 2 BAT in top 11
        bat_idx = df[df['player_role'] == 'BAT'].index.tolist()
        prob += pulp.lpSum(top11[i] for i in bat_idx) >= 2, "Min_Top11_BAT"

        # At least 6 WK + ALL + BAT in top 11
        wk_all_bat_idx = df[df['player_role'].isin(['WK', 'ALL', 'BAT'])].index.tolist()
        prob += pulp.lpSum(top11[i] for i in wk_all_bat_idx) >= 6, "Min_Top11_WK_ALL_BAT"

        # Constraints for all 15 players
        # At least 3 BAT in all 15
        prob += pulp.lpSum(x[i] for i in bat_idx) >= 3, "Min_All15_BAT"

        # At least 8 WK + ALL + BAT in all 15
        prob += pulp.lpSum(x[i] for i in wk_all_bat_idx) >= 8, "Min_All15_WK_ALL_BAT"

        # Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[prob.status] != 'Optimal':
            raise RuntimeError("No optimal solution found.")

        # Selected players
        sel_all = [i for i in players if pulp.value(x[i]) == 1]
        sel_top11 = [i for i in players if pulp.value(top11[i]) == 1]

        # Sort by whether in top 11 and then by points
        selected = df.loc[sel_all].copy()
        selected['is_top11'] = selected.index.isin(sel_top11)
        selected = selected.sort_values(['is_top11', 'total_fp'], ascending=[False, False])

        # Assign C/VC
        selected['C/VC'] = 'player'
        if len(selected) > 0:
            selected.iloc[0, selected.columns.get_loc('C/VC')] = 'captain'
        if len(selected) > 1:
            selected.iloc[1, selected.columns.get_loc('C/VC')] = 'vice captain'

        out = selected[['player_name', 'player_role', 'player_team', 'C/VC']].rename(columns={
            'player_name': 'Player Name',
            'player_role': 'Role',
            'player_team': 'Team'
        })

        # Save CSV
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"output_team_match_no_{match_number}.csv")
        out.to_csv(path, index=False)
        print(f"Optimized team saved to {path}")
        return out

    except Exception as e:
        print(f"ERROR in optimize_fantasy_team: {e}")
        import traceback;
        traceback.print_exc()
        return pd.DataFrame()