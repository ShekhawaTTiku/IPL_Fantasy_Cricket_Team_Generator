import os
import pandas as pd
import pulp
import logging

def get_player_rankings(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get player rankings based on predicted fantasy points.
    """
    try:
        rankings = final_df.copy()

        # Sort by predicted points and add rank
        rankings = rankings.sort_values('total_fp', ascending=False)
        rankings['Rank'] = range(1, len(rankings) + 1)
        rankings.drop(columns=['player_id', 'total_fp', 'key_cricinfo', 'credits', 'player_role'], inplace=True)

        return rankings

    except Exception as e:
        logging.error(f"Error in get_player_rankings: {str(e)}")
        return pd.DataFrame()


def optimize_best_xi(df: pd.DataFrame) -> list:
    """
    Optimize for Best XI team selection with given constraints.
    """
    prob = pulp.LpProblem("best_XI", pulp.LpMaximize)
    players = df.index.tolist()

    # Decision variables
    x = pulp.LpVariable.dicts("select", players, cat="Binary")

    # Objective: maximize total fantasy points
    prob += pulp.lpSum(df.loc[i, 'total_fp'] * x[i] for i in players)

    # Exactly 11 players
    prob += pulp.lpSum(x[i] for i in players) == 11

    # Credit limit of 100
    prob += pulp.lpSum(df.loc[i, 'credits'] * x[i] for i in players) <= 100

    # Role constraints
    for role in ['WK', 'ALL']:
        idx = df[df['player_role'] == role].index.tolist()
        prob += pulp.lpSum(x[i] for i in idx) >= 1  # At least 1
        prob += pulp.lpSum(x[i] for i in idx) <= 5  # At most 5

    for role in ['BAT', 'BOWL']:
        idx = df[df['player_role'] == role].index.tolist()
        prob += pulp.lpSum(x[i] for i in idx) >= 2  # At least 2
        prob += pulp.lpSum(x[i] for i in idx) <= 5  # At most 5

    # At least one player from each team
    for team in df['player_team'].unique():
        idx = df[df['player_team'] == team].index.tolist()
        prob += pulp.lpSum(x[i] for i in idx) >= 1

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    return [i for i in players if pulp.value(x[i]) == 1]


def optimize_best_xv(df: pd.DataFrame) -> tuple:
    """
    Optimize for Best XV team selection with given constraints.
    Returns both XI and XV selections.
    """
    prob = pulp.LpProblem("best_XV", pulp.LpMaximize)
    players = df.index.tolist()

    # Decision variables for XV and XI
    xv = pulp.LpVariable.dicts("select_xv", players, cat="Binary")
    xi = pulp.LpVariable.dicts("select_xi", players, cat="Binary")

    # Objective: maximize total fantasy points with higher weight to XI
    prob += pulp.lpSum(df.loc[i, 'total_fp'] * (2 * xi[i] + xv[i]) for i in players)

    # Squad size constraints
    prob += pulp.lpSum(xv[i] for i in players) == 15  # Exactly 15 players in squad
    prob += pulp.lpSum(xi[i] for i in players) == 11  # Exactly 11 players in XI

    # XI must be subset of XV
    for i in players:
        prob += xi[i] <= xv[i]

    # Credit constraints
    prob += pulp.lpSum(df.loc[i, 'credits'] * xv[i] for i in players) <= 145  # XV credit limit
    prob += pulp.lpSum(df.loc[i, 'credits'] * xi[i] for i in players) <= 100  # XI credit limit

    # Role constraints for XI
    for role in ['WK', 'ALL']:
        idx = df[df['player_role'] == role].index.tolist()
        prob += pulp.lpSum(xi[i] for i in idx) >= 1  # At least 1 in XI
        prob += pulp.lpSum(xi[i] for i in idx) <= 5  # At most 5 in XI

    for role in ['BAT', 'BOWL']:
        idx = df[df['player_role'] == role].index.tolist()
        prob += pulp.lpSum(xi[i] for i in idx) >= 2  # At least 2 in XI
        prob += pulp.lpSum(xi[i] for i in idx) <= 5  # At most 5 in XI

    # Role constraints for XV
    for role in ['WK', 'ALL']:
        idx = df[df['player_role'] == role].index.tolist()
        prob += pulp.lpSum(xv[i] for i in idx) >= 2  # At least 2 in XV
        prob += pulp.lpSum(xv[i] for i in idx) <= 7  # At most 7 in XV

    for role in ['BAT', 'BOWL']:
        idx = df[df['player_role'] == role].index.tolist()
        prob += pulp.lpSum(xv[i] for i in idx) >= 3  # At least 3 in XV
        prob += pulp.lpSum(xv[i] for i in idx) <= 7  # At most 7 in XV

    # Team constraints
    for team in df['player_team'].unique():
        idx = df[df['player_team'] == team].index.tolist()
        prob += pulp.lpSum(xi[i] for i in idx) >= 1  # At least 1 in XI
        prob += pulp.lpSum(xv[i] for i in idx) >= 3  # At least 3 in XV

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    sel_xv = [i for i in players if pulp.value(xv[i]) == 1]
    sel_xi = [i for i in players if pulp.value(xi[i]) == 1]

    return sel_xi, sel_xv


def optimize_fantasy_team(
        match_number: int,
        fp_df: pd.DataFrame,
        squad_df: pd.DataFrame,
        output_dir: str,
        output_mode: int = 2
) -> pd.DataFrame:
    """
    Main function to handle team optimization based on selected mode.
    """
    try:
        # Ensure correct columns exist
        if 'player_id' not in fp_df.columns or 'total_fp' not in fp_df.columns:
            logging.error("fp_df must contain 'player_id' and 'total_fp' columns")

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
        ).rename(columns={
            'dream11_name': 'player_name',
            'role': 'player_role',
            'team': 'player_team'
        }).reset_index(drop=True)

        if df.empty:
            logging.error("No valid players found after merging data")

        # Handle different modes
        if output_mode == 1:
            # Best XI
            selected = optimize_best_xi(df)
            result = df.loc[selected].copy()
            # format results before saving
            result.sort_values('total_fp', ascending=False, inplace=True)
            result['C/VC'] = None

            if not result.empty:
                result.iloc[0, result.columns.get_loc('C/VC')] = 'captain'
            if len(result) > 1:
                result.iloc[1, result.columns.get_loc('C/VC')] = 'vice captain'
            result.drop(columns=['player_id', 'total_fp', 'key_cricinfo', 'credits', 'player_role'], inplace=True)

        elif output_mode == 2:
            # Best XV
            sel_xi, sel_xv = optimize_best_xv(df)
            result = df.loc[sel_xv].copy()
            # format results before saving
            result.sort_values('total_fp', ascending=False, inplace=True)
            result['C/VC'] = None

            if not result.empty:
                result.iloc[0, result.columns.get_loc('C/VC')] = 'captain'
            if len(result) > 1:
                result.iloc[1, result.columns.get_loc('C/VC')] = 'vice captain'
            result.drop(columns=['player_id', 'total_fp', 'key_cricinfo', 'credits', 'player_role'], inplace=True)

        else:
            # Rankings
            result = get_player_rankings(df)

        # Save results
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"team_selection_match_{match_number}_mode_{output_mode}.csv")
        result.to_csv(output_file, index=False)

        # Display results
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(f"\nResults for Match {match_number}:")
        print("=" * 40)
        print(result.to_string(index=False))
        print(f"\nResults saved to: {output_file}")

        return result

    except Exception as e:
        logging.error(f"Error in optimize_fantasy_team: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()