import pandas as pd
import numpy as np
import datetime


class BowlerQualityCalculator:
    """
    A class to compute and apply historical bowling quality scores, with train/test separation.
    """

    def __init__(self, credibility_matches: int = 45,
                 weights: dict = None):
        self.weights = weights or {'avg': 0.2, 'sr': 0.2, 'wp': 0.3, 'op': 0.3}
        self.cred_matches = credibility_matches
        self.norm_params = {}

    def fit(self, bowl_df: pd.DataFrame) -> None:
        train_hist = bowl_df.copy()
        train_hist['date'] = pd.to_datetime(train_hist['date'])
        train_hist['overs'] = pd.to_numeric(train_hist['overs'], errors='coerce')
        train_hist['balls'] = pd.to_numeric(train_hist['balls'], errors='coerce')
        train_hist['runs'] = pd.to_numeric(train_hist['runs'], errors='coerce')
        train_hist['wickets'] = pd.to_numeric(train_hist['wickets'], errors='coerce')

        agg = train_hist.groupby(['key_cricinfo', 'bowler']).agg(
            matches_played=('match_id', 'nunique'),
            runs=('runs', 'sum'),
            wickets=('wickets', 'sum'),
            overs=('overs', 'sum'),
            balls=('balls', 'sum')
        ).reset_index()

        agg['bowling_avg_hist'] = np.where(
            agg['wickets'] > 0,
            agg['runs'] / agg['wickets'],
            np.where(agg['runs'] > 30, agg['runs'], agg['runs'] * 1.4)
        )
        agg['strike_rate_hist'] = np.where(
            agg['wickets'] > 0,
            agg['balls'] / agg['wickets'],
            np.where(agg['balls'] > 25, agg['balls'], agg['balls'] * 1.4)
        )
        agg['wickets_per_match'] = agg['wickets'] / agg['matches_played']
        agg['overs_per_match'] = agg['overs'] / agg['matches_played']

        self.norm_params = {
            'bowling_avg_min': agg['bowling_avg_hist'].min(),
            'bowling_avg_max': agg['bowling_avg_hist'].max(),
            'strike_rate_min': agg['strike_rate_hist'].min(),
            'strike_rate_max': agg['strike_rate_hist'].max(),
            'wpm_min': agg['wickets_per_match'].min(),
            'wpm_max': agg['wickets_per_match'].max(),
            'opm_min': agg['overs_per_match'].min(),
            'opm_max': agg['overs_per_match'].max(),
        }

    def score_for_match(self,
                        bowl_df: pd.DataFrame,
                        player_ids: list,
                        match_date: str) -> pd.DataFrame:
        hist = bowl_df.copy()
        hist['date'] = pd.to_datetime(hist['date'])
        hist = hist[hist['date'] < pd.to_datetime(match_date)]
        hist = hist[hist['key_cricinfo'].isin(player_ids)]
        hist['overs'] = pd.to_numeric(hist['overs'], errors='coerce')
        hist['balls'] = pd.to_numeric(hist['balls'], errors='coerce')
        hist['runs'] = pd.to_numeric(hist['runs'], errors='coerce')
        hist['wickets'] = pd.to_numeric(hist['wickets'], errors='coerce')

        agg = hist.groupby(['key_cricinfo', 'bowler']).agg(
            matches_played=('match_id', 'nunique'),
            runs=('runs', 'sum'),
            wickets=('wickets', 'sum'),
            overs=('overs', 'sum'),
            balls=('balls', 'sum')
        ).reset_index()

        all_ids = pd.DataFrame({'key_cricinfo': player_ids}).drop_duplicates()
        agg = all_ids.merge(agg, on='key_cricinfo', how='left').fillna({
            'bowler': '', 'matches_played': 0, 'runs': 0,
            'wickets': 0, 'overs': 0, 'balls': 0
        })

        agg['bowling_avg_hist'] = np.where(
            agg['wickets'] > 0,
            agg['runs'] / agg['wickets'],
            np.where(agg['runs'] > 30, agg['runs'], agg['runs'] * 1.4)
        )
        agg['strike_rate_hist'] = np.where(
            agg['wickets'] > 0,
            agg['balls'] / agg['wickets'],
            np.where(agg['balls'] > 25, agg['balls'], agg['balls'] * 1.4)
        )
        agg['wickets_per_match'] = np.where(
            agg['matches_played'] > 0,
            agg['wickets'] / agg['matches_played'],
            0
        )
        agg['overs_per_match'] = np.where(
            agg['matches_played'] > 0,
            agg['overs'] / agg['matches_played'],
            0
        )

        def norm(series, mn, mx, inv=False):
            if mx == mn:
                return series.apply(lambda x: 0.0 if x == 0 else 1.0)
            scaled = (series - mn) / (mx - mn)
            return ((mx - series) / (mx - mn)) if inv else scaled

        agg['norm_avg'] = norm(
            agg['bowling_avg_hist'],
            self.norm_params['bowling_avg_min'],
            self.norm_params['bowling_avg_max'], inv=True
        )
        agg['norm_sr'] = norm(
            agg['strike_rate_hist'],
            self.norm_params['strike_rate_min'],
            self.norm_params['strike_rate_max'], inv=True
        )
        agg['norm_wp'] = norm(
            agg['wickets_per_match'],
            self.norm_params['wpm_min'],
            self.norm_params['wpm_max'], inv=False
        )
        agg['norm_op'] = norm(
            agg['overs_per_match'],
            self.norm_params['opm_min'],
            self.norm_params['opm_max'], inv=False
        )

        agg['raw_score'] = (
                self.weights['avg'] * agg['norm_avg'] +
                self.weights['sr'] * agg['norm_sr'] +
                self.weights['wp'] * agg['norm_wp'] +
                self.weights['op'] * agg['norm_op']
        )
        cred = np.minimum(1, agg['matches_played'] / self.cred_matches)
        agg['adj_score'] = agg['raw_score'] * cred
        mask = agg['overs_per_match'] < 0.4
        agg.loc[mask, 'adj_score'] *= (agg.loc[mask, 'overs_per_match'] / 0.4)

        mn_score, mx_score = agg['adj_score'].min(), agg['adj_score'].max()
        if mx_score > mn_score:
            agg['bowler_quality_score'] = (agg['adj_score'] - mn_score) / (mx_score - mn_score)
        else:
            agg['bowler_quality_score'] = 0.0

        # Rename key and cast bowler_id to string.
        agg.rename(columns={'key_cricinfo': 'bowler_id'}, inplace=True)
        agg['bowler_id'] = agg['bowler_id'].astype(str)
        return agg[[
            'bowler_id', 'bowler', 'matches_played',
            'bowling_avg_hist', 'strike_rate_hist',
            'wickets_per_match', 'overs_per_match',
            'bowler_quality_score'
        ]]


def compute_team_bowler_proportions(bowler_quality: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-team proportions of each bowling style based on quality scores.
    Returns DataFrame with columns: Team, bowl_style, proportion.
    """
    team_sum = bowler_quality.groupby('Team')['bowler_quality_score'].sum().reset_index(name='team_total')
    style_sum = bowler_quality.groupby(['Team', 'bowl_style'])['bowler_quality_score'].sum().reset_index(
        name='style_score')
    props = style_sum.merge(team_sum, on='Team')
    props['proportion'] = props['style_score'] / props['team_total']
    return props[['Team', 'bowl_style', 'proportion']]


def compute_batter_matchup_scores(perf_filtered: pd.DataFrame, match_df: pd.DataFrame, team_props: pd.DataFrame,
                                  squad_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute matchup score per batter based on opponent team bowling style proportions.
    """
    team_mapping = {
        'Royal Challengers Bangalore': 'RCB',
        'Mumbai Indians': 'MI',
        'Chennai Super Kings': 'CSK',
        'Kolkata Knight Riders': 'KKR',
        'Punjab Kings': 'PBKS',
        'Rajasthan Royals': 'RR',
        'Sunrisers Hyderabad': 'SRH',
        'Delhi Capitals': 'DC',
        'Gujarat Titans': 'GT',
        'Lucknow Super Giants': 'LSG'
    }

    batter_opp = match_df[['Cricinfo ID', 'Opponent']].drop_duplicates()
    batter_opp.columns = ['batter_id', 'opp_team']
    batter_opp['opp_team'] = batter_opp['opp_team'].map(team_mapping)
    # Convert batter_id to string for consistency.
    batter_opp['batter_id'] = batter_opp['batter_id'].astype(str)

    batter_names = squad_df[['key_cricinfo', 'cricbuzz_name']].drop_duplicates()
    batter_names.columns = ['batter_id', 'batter_name']
    batter_names['batter_id'] = batter_names['batter_id'].astype(str)

    df = perf_filtered.merge(batter_opp, on='batter_id', how='left')
    df = df.merge(
        team_props,
        left_on=['opp_team', 'bowl_style'],
        right_on=['Team', 'bowl_style'],
        how='left'
    ).fillna({'proportion': 0})

    df['weighted_score'] = df['proportion'] * df['batter_perf_metric']
    matchup = df.groupby('batter_id')['weighted_score'].sum().reset_index(name='matchup_score')
    matchup = matchup.merge(batter_names, on='batter_id', how='left')
    matchup = matchup[['batter_id', 'batter_name', 'matchup_score']]
    return matchup


def get_matchup_score(perf_metric_df, bowl_df, match_df, squad_df):
    # Convert player_ids to string.
    player_ids = [pid for pid in match_df['Cricinfo ID'].unique().tolist()]

    date_str = match_df['Date'].iloc[0]
    parsed_date = datetime.datetime.strptime(date_str, "%d %b")
    match_date = parsed_date.replace(year=2025).strftime("%Y-%m-%d")

    # Compute bowler quality.
    calculator = BowlerQualityCalculator()
    calculator.fit(bowl_df)
    bowler_quality = calculator.score_for_match(bowl_df, player_ids, match_date)

    # Merge with squad_df to add bowl_style and team.
    bowler_quality = bowler_quality.merge(
        squad_df[['key_cricinfo', 'bowl_style', 'team']],
        left_on='bowler_id',
        right_on='key_cricinfo',
        how='left'
    )
    bowler_quality['bowl_style'] = bowler_quality['bowl_style'].fillna('RAF')
    bowler_quality = bowler_quality.rename(columns={'team': 'Team'})

    # Prepare performance metrics per batter.
    batter_ids = player_ids.copy()
    styles = perf_metric_df['bowl_style'].unique().tolist()
    full = pd.DataFrame([
        {'batter_id': bid, 'bowl_style': style}
        for bid in batter_ids for style in styles
    ])
    full['batter_id'] = full['batter_id'].astype(str)
    perf_metric_df['batter_id'] = perf_metric_df['batter_id'].astype(str)
    perf_filtered = full.merge(
        perf_metric_df,
        on=['batter_id', 'bowl_style'],
        how='left'
    ).fillna(0)

    # Compute team bowling style proportions.
    team_props = compute_team_bowler_proportions(bowler_quality)

    # Calculate batter matchup scores.
    matchup_df = compute_batter_matchup_scores(perf_filtered, match_df, team_props, squad_df)
    return matchup_df

