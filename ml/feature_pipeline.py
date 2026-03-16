"""
feature_pipeline.py
--------------------
Custom scikit-learn transformers + a full ColumnTransformer pipeline.

Engineered features (beyond raw inputs):
  • recency_score       : exponential decay on days_since_last
  • engagement_momentum : engagement × past_response_rate
  • peak_hour_flag      : 1 if time_of_day in known B2B sweet spots
  • social_reach        : linkedin_active × mutual_connections (normed)
  • sentiment_urgency   : news_sentiment × engagement_score
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    StandardScaler, OneHotEncoder, MinMaxScaler
)
from sklearn.impute import SimpleImputer


# ── Feature columns ──────────────────────────────────────────────────────────
NUMERIC_COLS = [
    "engagement_score", "linkedin_active", "news_sentiment",
    "time_of_day", "days_since_last", "past_response_rate",
    "profile_completeness", "mutual_connections",
]

CATEGORICAL_COLS = ["role", "industry", "company_size"]

ENGINEERED_COLS = [
    "recency_score", "engagement_momentum",
    "peak_hour_flag", "social_reach", "sentiment_urgency",
]

# B2B peak outreach hours (9-11 AM, 2-4 PM)
PEAK_HOURS = set(range(9, 12)) | set(range(14, 17))


# ── Custom transformer ────────────────────────────────────────────────────────
class OutreachFeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Computes domain-specific derived features from raw columns.
    Implements fit/transform so it slots cleanly into any sklearn Pipeline.
    """

    def __init__(self, decay_lambda: float = 0.05):
        self.decay_lambda = decay_lambda        # controls recency decay rate

    def fit(self, X: pd.DataFrame, y=None):
        # Store normalisation stats from training data only (no leakage)
        self.mutual_max_ = X["mutual_connections"].max() + 1e-9
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()

        # 1. Recency score: e^(-λ × days) → 1.0 means contacted today
        X["recency_score"] = np.exp(
            -self.decay_lambda * X["days_since_last"]
        )

        # 2. Engagement momentum: combined engagement signal
        X["engagement_momentum"] = (
            X["engagement_score"] * X["past_response_rate"]
        )

        # 3. Peak hour flag
        X["peak_hour_flag"] = (
            X["time_of_day"].isin(PEAK_HOURS)
        ).astype(int)

        # 4. Social reach (normalised)
        X["social_reach"] = (
            X["linkedin_active"]
            * (X["mutual_connections"] / self.mutual_max_)
        )

        # 5. Sentiment urgency: amplifies/dampens engagement by news context
        X["sentiment_urgency"] = (
            X["news_sentiment"] * X["engagement_score"]
        )

        return X[ENGINEERED_COLS]  # return only the new columns


# ── Full preprocessing pipeline ───────────────────────────────────────────────
def build_preprocessor() -> ColumnTransformer:
    """
    Returns a ColumnTransformer that:
      - Scales numeric features with StandardScaler
      - One-hot encodes categorical features (drop='first' for tree models)
      - Adds the engineered features via OutreachFeatureEngineer + MinMaxScaler
    """
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ohe",     OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    engineered_pipeline = Pipeline([
        ("engineer", OutreachFeatureEngineer(decay_lambda=0.05)),
        ("scaler",   MinMaxScaler()),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num",  numeric_pipeline,     NUMERIC_COLS),
            ("cat",  categorical_pipeline, CATEGORICAL_COLS),
            ("eng",  engineered_pipeline,  NUMERIC_COLS),   # needs raw cols too
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )

    return preprocessor


def get_feature_names(preprocessor: ColumnTransformer) -> list:
    """Extract feature names post-fit for SHAP and reporting."""
    names = []
    for name, transformer, cols in preprocessor.transformers_:
        if name == "num":
            names.extend(NUMERIC_COLS)
        elif name == "cat":
            ohe = transformer.named_steps["ohe"]
            names.extend(ohe.get_feature_names_out(CATEGORICAL_COLS).tolist())
        elif name == "eng":
            names.extend(ENGINEERED_COLS)
    return names
