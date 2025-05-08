# scripts/predict_match.py

import os
import pandas as pd
import numpy as np
from sklearn.exceptions import NotFittedError


def predict_one_match(
    match_number: int,
    bat_model,
    bowl_model,
    label_encoder: dict,
    test_bat_df: pd.DataFrame,
    test_bowl_df: pd.DataFrame,
    matchup_df: pd.DataFrame,
    save_dir: str
):
    """
    1. Merge matchup scores
    2. Label‑encode categorical columns
    3. Generate batting & bowling predictions
    4. Save individual CSVs and a combined CSV with total_fp
    """
    os.makedirs(save_dir, exist_ok=True)

    # ─── PREPARE BAT DATA ────────────────────────────────────────────────────────────────
    df_bat = test_bat_df.copy()
    # Merge matchup score if present
    if 'matchup_score' in matchup_df.columns:
        df_bat = df_bat.merge(
            matchup_df.rename(columns={"matchup_score": "batter_matchup_score"}),
            on="batter_id", how="left"
        )
    # Drop extraneous columns
    for drop in ("batter_name", "match_number"):
        if drop in df_bat.columns:
            df_bat.drop(columns=drop, inplace=True)

    # Encode categorical
    for col in df_bat.select_dtypes(include=["object", "string"]).columns:
        if col == "batter_id":
            continue
        key = f"{col}_encoder"
        if key in label_encoder:
            enc = label_encoder[key]
            if hasattr(enc, "classes_"):
                unknown = set(df_bat[col]) - set(enc.classes_)
                if unknown:
                    df_bat.loc[df_bat[col].isin(unknown), col] = enc.classes_[0]
            df_bat[col] = enc.transform(df_bat[col])
        else:
            df_bat[col], _ = pd.factorize(df_bat[col])

    # Numeric features
    Xb = df_bat.apply(pd.to_numeric, errors="coerce").fillna(0)

    # Batting predictions
    try:
        bat_preds = bat_model.predict(Xb)
    except NotFittedError:
        raise RuntimeError("Batting model is not fitted correctly")
    bat_preds = np.array(bat_preds).flatten()
    out_bat = pd.DataFrame({
        'player_id': df_bat['batter_id'],
        'batting_fp': bat_preds
    })
    # Ensure same dtype for merge
    out_bat['player_id'] = out_bat['player_id'].astype(str)
    bat_csv = os.path.join(save_dir, f"prediction_match_{match_number}_bat.csv")
    out_bat.to_csv(bat_csv, index=False)

    # ─── PREPARE BOWL DATA ────────────────────────────────────────────────────────────────
    df_bowl = test_bowl_df.copy()
    if 'match_number' in df_bowl.columns:
        df_bowl.drop(columns=['match_number'], inplace=True)
    # Encode categorical
    for col in df_bowl.select_dtypes(include=["object", "string"]).columns:
        if col == "bowler_id":
            continue
        key = f"{col}_encoder"
        if key in label_encoder:
            enc = label_encoder[key]
            if hasattr(enc, "classes_"):
                unknown = set(df_bowl[col]) - set(enc.classes_)
                if unknown:
                    df_bowl.loc[df_bowl[col].isin(unknown), col] = enc.classes_[0]
            df_bowl[col] = enc.transform(df_bowl[col])
        else:
            df_bowl[col], _ = pd.factorize(df_bowl[col])

    Xw = df_bowl.apply(pd.to_numeric, errors="coerce").fillna(0)
    # Ensure required columns
    for req in ("season", "ssn_avg"):
        if req not in Xw.columns:
            Xw[req] = 0

    # Bowling predictions
    try:
        bowl_preds = bowl_model.predict(Xw)
    except NotFittedError:
        raise RuntimeError("Bowling model is not fitted correctly")
    bowl_preds = np.array(bowl_preds).flatten()
    out_bowl = pd.DataFrame({
        'player_id': df_bowl['bowler_id'],
        'bowling_fp': bowl_preds
    })
    # Ensure same dtype for merge
    out_bowl['player_id'] = out_bowl['player_id'].astype(str)
    bowl_csv = os.path.join(save_dir, f"prediction_match_{match_number}_bowl.csv")
    out_bowl.to_csv(bowl_csv, index=False)

    # ─── MERGE & COMPUTE TOTAL ────────────────────────────────────────────────────────────
    merged = pd.merge(
        out_bat,
        out_bowl,
        on='player_id', how='outer'
    ).fillna(0)
    merged['total_fp'] = merged['batting_fp'] * 1.275 + merged['bowling_fp']

    merged_csv = os.path.join(save_dir, f"prediction_match_{match_number}_merged.csv")
    merged.to_csv(merged_csv, index=False)
    return merged
