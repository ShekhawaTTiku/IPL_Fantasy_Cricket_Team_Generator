import pandas as pd
import numpy as np

def compute_test_data_bowl(df_mbm, df_match_detail, min_season_matches=3):
    # 0) PREP & CLEAN df_mbm
    bowling_df = df_mbm.copy()
    # Convert numerical column to integer

    bowling_df['date']       = pd.to_datetime(bowling_df['date'])
    bowling_df['key_cricinfo']  = bowling_df['key_cricinfo'].astype(str)

    # Convert overs → total_balls & total_overs
    bowling_df['overs'] = bowling_df['overs'].replace('DNB', '0.0').astype(str)
    split = bowling_df['overs'].str.split('.', expand=True).fillna('0')
    bowling_df['overs_int']   = split[0].astype(int)
    bowling_df['balls_int']   = split[1].astype(int)
    bowling_df['total_balls'] = bowling_df['overs_int'] * 6 + bowling_df['balls_int']
    bowling_df['total_overs'] = bowling_df['total_balls'] / 6

    # ——————————————————————————————
    # 0.1) PRECOMPUTE season-statistics
    bowling_df['season'] = bowling_df['date'].dt.year
    grp = bowling_df.groupby(['key_cricinfo','season','league'])
    bowling_df['cumulative_runs']    = grp['runs'].cumsum()    - bowling_df['runs']
    bowling_df['cumulative_wickets'] = grp['wickets'].cumsum() - bowling_df['wickets']
    bowling_df['cumulative_balls']   = grp['total_balls'].cumsum() - bowling_df['total_balls']
    bowling_df['cum_matches']        = grp.cumcount()

    bowling_df['ssn_avg'] = bowling_df['cumulative_runs']    / bowling_df['cumulative_wickets'].replace(0, np.nan)
    bowling_df['ssn_eco'] = bowling_df['cumulative_runs']    / (bowling_df['cumulative_balls'] / 6).replace(0, np.nan)
    bowling_df['ssn_sr']  = bowling_df['cumulative_balls']   / bowling_df['cumulative_wickets'].replace(0, np.nan)
    bowling_df['ssn_wpm'] = bowling_df['cumulative_wickets']/ bowling_df['cum_matches'].replace(0, np.nan)
    bowling_df['ssn_opm'] = (bowling_df['cumulative_balls']/6) / bowling_df['cum_matches'].replace(0, np.nan)

    # drop only the truly temporary cols (keep total_balls & total_overs!)
    bowling_df.drop(columns=[
        'overs_int','balls_int',
        'cumulative_runs','cumulative_wickets','cumulative_balls','cum_matches'
    ], inplace=True)

    # clean up infinities & fill NaN → 0
    for col in ['ssn_avg','ssn_eco','ssn_sr','ssn_wpm','ssn_opm']:
        bowling_df[col] = bowling_df[col].replace([np.inf, -np.inf], 0).fillna(0)

    # mark first row per (bowler,season,league) as NA
    first_idx = bowling_df.groupby(['key_cricinfo','season','league']).head(1).index
    bowling_df.loc[first_idx, ['ssn_avg','ssn_eco','ssn_sr','ssn_wpm','ssn_opm']] = pd.NA
    # ——————————————————————————————

    # 1) PREPARE df_match_detail
    md = df_match_detail.copy()
    md['date']       = pd.to_datetime('2025 ' + md['Date'], format='%Y %d %b')
    md['season']     = md['date'].dt.year
    md['league']     = 'IPL'
    md['bowler_id']  = md['Cricinfo ID'].astype(str)
    md['bowl_team']  = md['Team']
    md['bat_team']   = md['Opponent']
    md['inns']       = md['Innings']
    md['venue']      = md['Venue']

    def compute_bowl_stats(df):
        if df.empty:
            return dict(avg=np.nan, eco=np.nan, sr=np.nan, wpm=np.nan, opm=np.nan)
        runs    = df['runs'].sum()
        wkts    = df['wickets'].sum()
        balls   = df['total_balls'].sum()
        overs   = df['total_overs'].sum()
        matches = len(df)
        return dict(
            avg = runs / (wkts if wkts>0 else 1),
            eco = runs / (overs if overs>0 else 1),
            sr  = balls / (wkts if wkts>0 else 1),
            wpm = wkts / matches,
            opm = overs / matches
        )

    results = []
    for _, row in md.iterrows():
        bid     = row['bowler_id']
        mdate   = row['date']
        cleag   = row['league']
        cses    = row['season']
        inns    = row['inns']
        venue   = row['venue']

        # filter history
        hist = bowling_df[
            (bowling_df['key_cricinfo']==bid) &
            (bowling_df['date']      < mdate)
        ].copy()
        debut = int(hist.empty)

        # A) Career
        h_leag = hist[hist['league']==cleag]
        career = compute_bowl_stats(h_leag)
        if pd.isna(career['avg']):
            career = compute_bowl_stats(hist)

        # B) Venue
        h_ven = hist[hist['venue']==venue]
        venue_stats = compute_bowl_stats(h_ven)
        if pd.isna(venue_stats['avg']):
            venue_stats = compute_bowl_stats(hist)

        # C) Innings
        h_ins_le = h_leag[h_leag['innings']==inns]
        inns_stats = compute_bowl_stats(h_ins_le)
        if pd.isna(inns_stats['avg']):
            inns_stats = compute_bowl_stats(hist[hist['innings']==inns])

        # D) Season: first try the precomputed row, then fallback
        mask = (
            (bowling_df['key_cricinfo']==bid) &
            (bowling_df['league']==cleag) &
            (bowling_df['season']==cses) &
            (bowling_df['date']    < mdate)
        )
        if mask.any():
            last_row = bowling_df.loc[mask].sort_values('date').iloc[-1]
            ssn_stats = {
                'avg': last_row['ssn_avg'],
                'eco': last_row['ssn_eco'],
                'sr' : last_row['ssn_sr'],
                'wpm': last_row['ssn_wpm'],
                'opm': last_row['ssn_opm']
            }
        else:
            ssn_stats = dict(avg=np.nan, eco=np.nan, sr=np.nan, wpm=np.nan, opm=np.nan)

        # fallback block (same as before)
        if pd.isna(ssn_stats['avg']):
            prior = hist
            prior_same = prior[prior['league']==cleag]
            if len(prior_same)>0:
                past_seasons = sorted(prior_same['season'].unique())
                past = [s for s in past_seasons if s < cses]
                grp = (prior_same[prior_same['season']==max(past)]
                       if past else prior)
            else:
                leagues_played = prior['league'].unique()
                grp = None
                order = sorted(
                    leagues_played,
                    key=lambda lg: prior[prior['league']==lg]['date'].max(),
                    reverse=True
                )
                for lg in order:
                    lg_grp = prior[prior['league']==lg]
                    if len(lg_grp)>=min_season_matches:
                        grp = lg_grp
                        break
                if grp is None:
                    curr_oth = prior[prior['season']==cses]
                    grp = curr_oth if len(curr_oth)>0 else prior

            total_runs    = grp['runs'].sum()
            total_wkts    = grp['wickets'].sum()
            total_balls   = grp['total_balls'].sum()
            total_overs   = grp['total_overs'].sum()
            total_matches = len(grp)
            ssn_stats = {
                'avg': total_runs / max(total_wkts,1),
                'eco': total_runs / max(total_overs,1),
                'sr' : total_balls / max(total_wkts,1),
                'wpm': total_wkts / max(total_matches,1),
                'opm': total_overs / max(total_matches,1)
            }

        # E) Last 5
        last5 = hist.sort_values('date', ascending=False).head(5)
        last5_stats = compute_bowl_stats(last5)

        # assemble
        rec = {
            'bowler_id':  bid,
            'bowl_team':  row['bowl_team'],
            'bat_team':   row['bat_team'],
            'league':     cleag,
            'career_avg': career['avg'],
            'career_eco': career['eco'],
            'career_sr':  career['sr'],
            'career_wpm': career['wpm'],
            'career_opm': career['opm'],
            'inns':       inns,
            'inns_avg':   inns_stats['avg'],
            'inns_eco':   inns_stats['eco'],
            'inns_sr':    inns_stats['sr'],
            'inns_wpm':   inns_stats['wpm'],
            'inns_opm':   inns_stats['opm'],
            'venue':      venue,
            'venue_avg':  venue_stats['avg'],
            'venue_eco':  venue_stats['eco'],
            'venue_sr':   venue_stats['sr'],
            'venue_wpm':  venue_stats['wpm'],
            'venue_opm':  venue_stats['opm'],
            'season':     cses,
            'ssn_avg':    ssn_stats['avg'],
            'ssn_eco':    ssn_stats['eco'],
            'ssn_sr':     ssn_stats['sr'],
            'ssn_wpm':    ssn_stats['wpm'],
            'ssn_opm':    ssn_stats['opm'],
            'last5_avg':  last5_stats['avg'],
            'last5_eco':  last5_stats['eco'],
            'last5_sr':   last5_stats['sr'],
            'last5_wpm':  last5_stats['wpm'],
            'last5_opm':  last5_stats['opm'],
            'career_debut': debut
        }

        # fill NaN → 0
        for k,v in rec.items():
            if pd.isna(v):
                rec[k] = 0

        results.append(rec)

        df_results = pd.DataFrame(results)
        df_results.bowler_id = df_results.bowler_id.astype(int)

    return df_results

def get_test_bowl(df_mbm, df_match_detail):
    """
    Computes test data for bowlers based on match details and MBM data.

    Parameters:
        df_mbm (pd.DataFrame): DataFrame containing MBM data.
        df_match_detail (pd.DataFrame): DataFrame containing match details.

    Returns:
        pd.DataFrame: DataFrame with computed test data for bowlers.
    """
    return compute_test_data_bowl(df_mbm, df_match_detail)