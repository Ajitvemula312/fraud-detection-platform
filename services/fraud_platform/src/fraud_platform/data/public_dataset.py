from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


MERCHANT_CATEGORIES = [
    "grocery",
    "electronics",
    "travel",
    "fashion",
    "fuel",
    "gaming",
    "health",
    "restaurants",
]
TRANSACTION_TYPES = ["chip", "online", "tap", "cash_withdrawal"]
REGIONS = ["north_america", "europe", "asia", "latam", "middle_east", "africa"]


def load_kaggle_creditcard_dataset(csv_path: str | Path) -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Download Kaggle creditcard.csv into data/raw first."
        )
    dataframe = pd.read_csv(path)
    required_columns = {"Time", "Amount", "Class"}
    missing = required_columns - set(dataframe.columns)
    if missing:
        raise ValueError(f"Dataset missing expected columns: {sorted(missing)}")
    return dataframe


def enrich_creditcard_dataset(dataframe: pd.DataFrame) -> pd.DataFrame:
    df = dataframe.copy()
    df = df.fillna(0)
    df["transaction_timestamp"] = pd.Timestamp("2024-01-01") + pd.to_timedelta(df["Time"], unit="s")
    df["transaction_id"] = [f"txn_{index:07d}" for index in range(len(df))]
    df["account_id"] = [f"acct_{abs(hash((row.V1, row.V2, idx))) % 2000:04d}" for idx, row in df.iterrows()]
    df["merchant_category"] = [
        MERCHANT_CATEGORIES[int(abs(row.V3 * 10_000 + idx)) % len(MERCHANT_CATEGORIES)]
        for idx, row in df.iterrows()
    ]
    df["transaction_type"] = [
        TRANSACTION_TYPES[int(abs(row.V5 * 10_000 + idx)) % len(TRANSACTION_TYPES)]
        for idx, row in df.iterrows()
    ]
    df["region"] = [
        REGIONS[int(abs(row.V7 * 10_000 + idx)) % len(REGIONS)]
        for idx, row in df.iterrows()
    ]
    df["account_age_days"] = (np.abs(df["V6"]) * 365).round().clip(30, 3650).astype(int)
    df["hour_of_day"] = ((df["Time"] // 3600) % 24).astype(int)
    df["weekend_flag"] = df["hour_of_day"].isin([0, 1, 2, 3, 4, 5, 22, 23])
    df = df.sort_values(["account_id", "transaction_timestamp", "transaction_id"]).reset_index(drop=True)

    grouped = df.groupby("account_id", sort=False)
    df["previous_txn_count"] = grouped.cumcount()
    df["avg_spend_rolling"] = grouped["Amount"].transform(lambda series: series.shift(1).expanding().mean()).fillna(df["Amount"].median())
    df["merchant_txn_count"] = df.groupby(["account_id", "merchant_category"]).cumcount()
    df["time_delta_seconds"] = grouped["Time"].diff().fillna(0).clip(lower=0)
    df["txn_velocity_score"] = (3600 / df["time_delta_seconds"].replace(0, 30)).clip(0, 120)

    region_average = df.groupby("region")["Class"].transform("mean").fillna(df["Class"].mean())
    amount_mean = df["Amount"].mean()
    amount_std = max(float(df["Amount"].std(ddof=0)), 1.0)

    df["region_risk_score"] = region_average.round(4)
    df["amount_zscore"] = ((df["Amount"] - amount_mean) / amount_std).round(4)
    safe_avg = df["avg_spend_rolling"].replace(0, amount_mean)
    df["amount_to_avg_ratio"] = (df["Amount"] / safe_avg).clip(0, 50)
    df["risk_aggregation_score"] = (
        0.45 * df["amount_to_avg_ratio"]
        + 0.35 * df["txn_velocity_score"] / 10
        + 0.20 * df["region_risk_score"] * 10
    )
    df["is_fraud"] = df["Class"].astype(int)
    return df


def prepare_training_dataset(csv_path: str | Path) -> pd.DataFrame:
    raw_df = load_kaggle_creditcard_dataset(csv_path)
    return enrich_creditcard_dataset(raw_df)

