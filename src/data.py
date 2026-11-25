from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DATA_PATH

CANONICAL_COLUMNS = [
    "timestamp",
    "power",
    "wind_speed",
    "theoretical_power",
    "wind_direction",
]

NUMERIC_COLUMNS = [
    "power",
    "wind_speed",
    "theoretical_power",
    "wind_direction",
]


def _prepare_frame(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.shape[1] < 5:
        raise ValueError(
            "Dataset must contain at least five columns: Date/Time, ActivePower, "
            "Wind Speed, Theoretical Power Curve, and Wind Direction."
        )

    df = raw.iloc[:, :5].copy()
    df.columns = CANONICAL_COLUMNS

    df["timestamp"] = pd.to_datetime(
        df["timestamp"], format="%d %m %Y %H:%M", errors="coerce"
    )

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = (
        df.dropna(subset=["timestamp", "power", "wind_speed"])
        .sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"], keep="first")
        .reset_index(drop=True)
    )

    df["month"] = df["timestamp"].dt.month
    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.dayofweek
    return df


def load_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")
    raw = pd.read_csv(path, encoding="utf-8-sig")
    return _prepare_frame(raw)


def load_data_from_bytes(content: bytes) -> pd.DataFrame:
    raw = pd.read_csv(BytesIO(content), encoding="utf-8-sig")
    return _prepare_frame(raw)


def data_quality_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"Check": "Rows", "Value": f"{len(df):,}"},
        {"Check": "Columns", "Value": str(df.shape[1])},
        {
            "Check": "Time range",
            "Value": f"{df['timestamp'].min():%d %b %Y} to {df['timestamp'].max():%d %b %Y}",
        },
        {"Check": "Duplicate timestamps", "Value": f"{df['timestamp'].duplicated().sum():,}"},
        {"Check": "Missing values", "Value": f"{int(df.isna().sum().sum()):,}"},
        {
            "Check": "Negative power readings",
            "Value": f"{int((df['power'] < 0).sum()):,}",
        },
        {
            "Check": "Zero power readings",
            "Value": f"{int((df['power'] == 0).sum()):,}",
        },
        {
            "Check": "Zero power above 3 m/s",
            "Value": f"{int(((df['power'] == 0) & (df['wind_speed'] > 3)).sum()):,}",
        },
    ]
    return pd.DataFrame(rows)


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["power", "wind_speed", "theoretical_power", "wind_direction"]
    summary = df[columns].describe().T.reset_index()
    summary = summary.rename(columns={"index": "Variable"})
    return summary


def summary_statistics(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "start": df["timestamp"].min(),
        "end": df["timestamp"].max(),
        "wind_min": float(np.nanmin(df["wind_speed"])),
        "wind_max": float(np.nanmax(df["wind_speed"])),
        "power_min": float(np.nanmin(df["power"])),
        "power_max": float(np.nanmax(df["power"])),
    }
