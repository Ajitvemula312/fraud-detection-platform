from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .public_dataset import enrich_creditcard_dataset


def generate_smoke_test_dataset(rows: int = 240, fraud_ratio: float = 0.15, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fraud_rows = int(rows * fraud_ratio)
    labels = np.array([0] * (rows - fraud_rows) + [1] * fraud_rows)
    rng.shuffle(labels)

    base = {
        "Time": np.sort(rng.integers(0, 86_400, size=rows)),
        "Amount": np.where(labels == 1, rng.normal(380, 110, size=rows), rng.normal(92, 45, size=rows)).clip(1, None),
        "Class": labels,
    }
    for index in range(1, 29):
        signal = rng.normal(loc=0.0, scale=1.0, size=rows)
        if index in {4, 10, 12, 14, 17}:
            signal = signal + labels * rng.normal(1.8, 0.35, size=rows)
        base[f"V{index}"] = signal

    dataframe = pd.DataFrame(base)
    return enrich_creditcard_dataset(dataframe)


def write_smoke_test_dataset(output_path: str | Path, rows: int = 240, seed: int = 42) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe = generate_smoke_test_dataset(rows=rows, seed=seed)
    dataframe.to_csv(path, index=False)
    return path

