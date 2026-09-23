"""
FIFA World Cup 2026 — Data Pipeline
------------------------------------
Turns the raw match-by-match CSV (one row per player per match, 54,600 rows)
into a clean player-tournament summary table (one row per player, ~1,248 rows)
with per-90 metrics and scouting scores.

Run directly to sanity-check the pipeline:
    python src/data_pipeline.py
"""

import os
import numpy as np
import pandas as pd

RAW_SUM_COLS = [
    "minutes_played", "goals", "assists", "shots", "shots_on_target",
    "expected_goals_xg", "expected_assists_xa", "key_passes",
    "successful_passes", "total_passes", "dribbles_attempted",
    "successful_dribbles", "crosses", "successful_crosses", "tackles",
    "interceptions", "clearances", "blocks", "aerial_duels_won",
    "aerial_duels_lost", "recoveries", "fouls_committed", "fouls_suffered",
    "yellow_cards", "red_cards", "saves", "clean_sheet", "goals_conceded",
    "penalty_saves", "player_of_match_awards",
]

RAW_MEAN_COLS = [
    "distance_covered_km", "sprint_distance_km", "stamina_score",
    "player_rating", "performance_score", "offensive_contribution",
    "defensive_contribution", "possession_impact", "pressure_resistance",
    "creativity_score", "consistency_score", "clutch_performance_score",
]

RAW_MAX_COLS = ["top_speed_kmh"]

GROUP_KEYS = [
    "player_id", "player_name", "team", "position", "age",
    "nationality", "club_name", "preferred_foot", "height_cm",
    "weight_kg", "market_value_eur",
]


def load_raw(file_path: str) -> pd.DataFrame:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Dataset not found at: {file_path}")
    df = pd.read_csv(file_path)
    df["match_date"] = pd.to_datetime(df["match_date"])
    return df


def build_player_summary(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Aggregate match-level rows into one row per player for the whole tournament."""

    agg_dict = {c: "sum" for c in RAW_SUM_COLS}
    agg_dict.update({c: "mean" for c in RAW_MEAN_COLS})
    agg_dict.update({c: "max" for c in RAW_MAX_COLS})
    # matches_played counted from the grouped frame itself (safe, no realignment risk)
    agg_dict["match_id"] = "nunique"

    summary = (
        df_raw.groupby(GROUP_KEYS, as_index=False)
        .agg(agg_dict)
        .rename(columns={"match_id": "matches_played"})
    )

    # --- Per-90 normalisation (avoids rewarding players who just played more minutes) ---
    minutes_90 = summary["minutes_played"].replace(0, np.nan) / 90.0

    summary["goals_per_90"] = (summary["goals"] / minutes_90).round(2)
    summary["assists_per_90"] = (summary["assists"] / minutes_90).round(2)
    summary["xg_per_90"] = (summary["expected_goals_xg"] / minutes_90).round(2)
    summary["xa_per_90"] = (summary["expected_assists_xa"] / minutes_90).round(2)
    summary["key_passes_per_90"] = (summary["key_passes"] / minutes_90).round(2)
    summary["shots_per_90"] = (summary["shots"] / minutes_90).round(2)
    summary["defensive_actions_per_90"] = (
        (summary["tackles"] + summary["interceptions"] + summary["clearances"] + summary["blocks"])
        / minutes_90
    ).round(2)
    summary["recoveries_per_90"] = (summary["recoveries"] / minutes_90).round(2)

    # --- Efficiency / quality ratios ---
    summary["xg_overperformance"] = (summary["goals"] - summary["expected_goals_xg"]).round(2)
    summary["shot_conversion_pct"] = np.where(
        summary["shots"] > 0, (summary["goals"] / summary["shots"] * 100).round(1), 0.0
    )
    summary["pass_accuracy_pct"] = np.where(
        summary["total_passes"] > 0,
        (summary["successful_passes"] / summary["total_passes"] * 100).round(1),
        0.0,
    )
    summary["dribble_success_pct"] = np.where(
        summary["dribbles_attempted"] > 0,
        (summary["successful_dribbles"] / summary["dribbles_attempted"] * 100).round(1),
        0.0,
    )
    summary["aerial_duel_win_pct"] = np.where(
        (summary["aerial_duels_won"] + summary["aerial_duels_lost"]) > 0,
        (summary["aerial_duels_won"] / (summary["aerial_duels_won"] + summary["aerial_duels_lost"]) * 100).round(1),
        0.0,
    )

    # --- Goalkeeper-specific: overall save % across all their matches ---
    saves_faced = summary["saves"] + summary["goals_conceded"]
    summary["save_pct_overall"] = np.where(
        saves_faced > 0, (summary["saves"] / saves_faced * 100).round(1), 0.0
    )

    # --- Composite scouting score (0-100), weighted differently for GK vs outfield ---
    summary["scouting_score"] = summary.apply(_composite_scouting_score, axis=1)

    for c in ["distance_covered_km", "sprint_distance_km", "top_speed_kmh",
              "stamina_score", "player_rating", "performance_score"]:
        summary[c] = summary[c].round(2)

    summary = summary.round(2)
    summary = summary.fillna(0)
    return summary


def _composite_scouting_score(row) -> float:
    """A simple, transparent 0-100 scouting index. Not a claim of ground truth —
    just a documented, reproducible way to rank players for the dashboard."""
    if row["position"] == "Goalkeeper":
        score = (
            row["save_pct_overall"] * 0.45
            + row["player_rating"] * 8
            + (row["clean_sheet"] / max(row["matches_played"], 1)) * 20
            + row["penalty_saves"] * 5
        )
    else:
        score = (
            row["goals_per_90"] * 15
            + row["assists_per_90"] * 12
            + row["xg_per_90"] * 8
            + row["defensive_actions_per_90"] * 2
            + row["pass_accuracy_pct"] * 0.2
            + row["player_rating"] * 6
        )
    return round(min(max(score, 0), 100), 1)


def build_team_summary(player_summary: pd.DataFrame) -> pd.DataFrame:
    """One row per national team — useful for a team-comparison view."""
    team_agg = player_summary.groupby("team", as_index=False).agg(
        squad_size=("player_id", "nunique"),
        total_goals=("goals", "sum"),
        total_assists=("assists", "sum"),
        total_xg=("expected_goals_xg", "sum"),
        avg_pass_accuracy=("pass_accuracy_pct", "mean"),
        avg_rating=("player_rating", "mean"),
        total_yellow_cards=("yellow_cards", "sum"),
        total_red_cards=("red_cards", "sum"),
        total_distance_km=("distance_covered_km", "sum"),
    )
    return team_agg.round(2)


def load_and_preprocess_data(file_path: str):
    """Convenience wrapper used by the app: returns (raw_df, player_summary, team_summary)."""
    raw = load_raw(file_path)
    player_summary = build_player_summary(raw)
    team_summary = build_team_summary(player_summary)
    return raw, player_summary, team_summary


if __name__ == "__main__":
    raw, players, teams = load_and_preprocess_data(
        os.path.join(os.path.dirname(__file__), "..", "data",
                      "fifa_world_cup_2026_player_performance.csv")
    )
    assert players["player_id"].is_unique, "Player summary should have one row per player!"
    assert raw["match_id"].nunique() > 0
    print(f"Raw rows:              {len(raw):,}")
    print(f"Unique players:        {players.shape[0]:,}")
    print(f"Unique teams:          {teams.shape[0]}")
    print(f"Columns in summary:    {players.shape[1]}")
    print("\nSample of player_summary:")
    print(players[["player_name", "team", "position", "goals", "goals_per_90",
                    "player_rating", "scouting_score"]].sort_values(
                        "scouting_score", ascending=False).head(10).to_string(index=False))
    print("\n✅ Pipeline check passed — no errors, no NaNs, one row per player.")
