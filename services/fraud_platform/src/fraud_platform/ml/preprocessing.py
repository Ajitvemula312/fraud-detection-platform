from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TARGET_COLUMN = "is_fraud"
EXCLUDED_COLUMNS = {TARGET_COLUMN, "Class", "transaction_timestamp"}
CATEGORICAL_COLUMNS = {"transaction_id", "account_id", "merchant_category", "transaction_type", "region"}


@dataclass(slots=True)
class FeatureSpec:
    numeric_features: list[str]
    categorical_features: list[str]
    target_column: str = TARGET_COLUMN

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def infer_feature_spec(dataframe: pd.DataFrame) -> FeatureSpec:
    categorical = [column for column in dataframe.columns if column in CATEGORICAL_COLUMNS]
    numeric = [
        column
        for column in dataframe.columns
        if column not in EXCLUDED_COLUMNS
        and column not in categorical
        and pd.api.types.is_numeric_dtype(dataframe[column])
    ]
    return FeatureSpec(numeric_features=numeric, categorical_features=categorical)


def build_preprocessor(feature_spec: FeatureSpec) -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric_pipeline, feature_spec.numeric_features),
            ("categorical", categorical_pipeline, feature_spec.categorical_features),
        ]
    )

