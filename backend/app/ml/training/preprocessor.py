from typing import List
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OrdinalEncoder, RobustScaler

NUMERICAL_FEATURES: List[str] = [
    "tenure_months",
    "monthly_fee_current",
    "package_speed_mbps",
    "late_payment_count_3m",
    "late_payment_count_6m",
    "avg_payment_delay_days_3m",
]

CATEGORICAL_FEATURES: List[str] = [
    "payment_status_trend",
]

BOOLEAN_FEATURES: List[str] = [
    "downgrade_flag_6m",
]

ALL_FEATURE_COLUMNS: List[str] = (
    NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BOOLEAN_FEATURES
)


def convert_bool_to_int(X):
    return pd.DataFrame(X).fillna(False).astype(int).to_numpy()


def build_feature_preprocessor() -> ColumnTransformer:
    """Construct Scikit-Learn ColumnTransformer pipeline for tabular ISP churn features."""
    # 1. Numerical Pipeline: Median Imputation + RobustScaler
    num_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]
    )

    # 2. Categorical Pipeline: Ordinal Encoding (IMPROVING: 0, STABLE: 1, WORSENING: 2)
    cat_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="constant", fill_value="STABLE"),
            ),
            (
                "ordinal",
                OrdinalEncoder(
                    categories=[["IMPROVING", "STABLE", "WORSENING"]],  # type: ignore
                    handle_unknown="use_encoded_value",
                    unknown_value=-1,
                ),
            ),
        ]
    )

    # 3. Boolean Pipeline: Impute nulls with 0 and convert boolean to int64
    bool_pipeline = Pipeline(
        steps=[
            ("bool_to_int", FunctionTransformer(convert_bool_to_int, feature_names_out="one-to-one")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", num_pipeline, NUMERICAL_FEATURES),
            ("cat", cat_pipeline, CATEGORICAL_FEATURES),
            ("bool", bool_pipeline, BOOLEAN_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    return preprocessor
