import numpy as np
import pandas as pd

from src.config import (
    DEFAULT_MAD_K,
    DEFAULT_OUTLIER_RULES,
    DEFAULT_UNDERPERFORMANCE_RATIO,
    OUTLIER_RULE_LABELS,
)


def derive_physical_parameters(df: pd.DataFrame) -> dict:
    wind = df["wind_speed"].to_numpy(dtype=float)
    theory = df["theoretical_power"].to_numpy(dtype=float)

    valid = np.isfinite(wind) & np.isfinite(theory)
    positive = valid & (theory > 0)
    cut_in = float(np.nanmin(wind[positive])) if positive.any() else 3.0

    max_theory = float(np.nanmax(theory[valid])) if valid.any() else 3600.0
    rated_mask = valid & (theory >= 0.9999 * max_theory)
    rated = float(np.nanmin(wind[rated_mask])) if rated_mask.any() else 13.0
    rated_power = float(round(max_theory, -1))

    return {
        "cut_in": round(cut_in, 2),
        "rated": round(rated, 2),
        "rated_power": rated_power,
        "cut_out": round(float(np.nanmax(wind[valid])), 2),
    }


def add_outlier_flags(
    df: pd.DataFrame,
    cut_in: float,
    rated_power: float,
    mad_k: float = DEFAULT_MAD_K,
    underperformance_ratio: float = DEFAULT_UNDERPERFORMANCE_RATIO,
) -> pd.DataFrame:
    flags = pd.DataFrame(index=df.index)

    flags["negative_power"] = df["power"] < -1e-6
    flags["over_rated_power"] = df["power"] > rated_power * 1.05
    flags["downtime"] = (df["power"] <= 1.0) & (df["wind_speed"] > cut_in)
    flags["underperformance"] = (df["theoretical_power"] > 100) & (
        df["power"] < underperformance_ratio * df["theoretical_power"]
    )

    max_wind = float(np.nanmax(df["wind_speed"]))
    bins = np.arange(0.0, np.ceil(max_wind) + 1.0, 0.5)
    wind_bins = pd.cut(df["wind_speed"], bins=bins, include_lowest=True)
    bin_median = df.groupby(wind_bins, observed=True)["power"].transform("median")
    deviation = (df["power"] - bin_median).abs()
    bin_mad = deviation.groupby(wind_bins, observed=True).transform("median")
    robust_sigma = 1.4826 * bin_mad
    flags["bin_mad_outlier"] = (robust_sigma > 0) & (
        deviation > mad_k * robust_sigma
    )

    flags["any_outlier"] = flags[
        list(OUTLIER_RULE_LABELS.keys())
    ].any(axis=1)
    return flags


def clean_data(
    df: pd.DataFrame,
    cut_in: float,
    rated_power: float,
    rules: dict | None = None,
    mad_k: float = DEFAULT_MAD_K,
    underperformance_ratio: float = DEFAULT_UNDERPERFORMANCE_RATIO,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rules = DEFAULT_OUTLIER_RULES.copy() if rules is None else rules
    flags = add_outlier_flags(
        df,
        cut_in=cut_in,
        rated_power=rated_power,
        mad_k=mad_k,
        underperformance_ratio=underperformance_ratio,
    )

    removal_mask = np.zeros(len(df), dtype=bool)
    summary_rows = []

    for rule, label in OUTLIER_RULE_LABELS.items():
        enabled = bool(rules.get(rule, False))
        rule_mask = flags[rule].to_numpy(dtype=bool)
        if enabled:
            removal_mask |= rule_mask
        summary_rows.append(
            {
                "Rule": label,
                "Flagged": int(rule_mask.sum()),
                "Removed": int(rule_mask.sum()) if enabled else 0,
                "Enabled": "Yes" if enabled else "No",
            }
        )

    cleaned = df.loc[~removal_mask].copy().reset_index(drop=True)
    summary_rows.append(
        {
            "Rule": "Total removed",
            "Flagged": int(flags["any_outlier"].sum()),
            "Removed": int(removal_mask.sum()),
            "Enabled": "",
        }
    )

    summary = pd.DataFrame(summary_rows)
    return cleaned, flags, summary


def prepare_xy(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    x = df[["wind_speed"]].to_numpy(dtype=float)
    y = df["power"].to_numpy(dtype=float)
    return x, y
