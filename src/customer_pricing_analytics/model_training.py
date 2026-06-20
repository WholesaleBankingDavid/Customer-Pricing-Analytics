"""Baseline model training for commercial win probability."""

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from customer_pricing_analytics.model_evaluation import evaluate_classifier


def train_baseline_logistic_regression(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    test_size: float = 0.25,
    random_state: int = 42,
) -> tuple[Pipeline, dict]:
    """Train an explainable baseline logistic-regression classifier."""

    missing = [column for column in [target_col, *feature_cols] if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    data = df[[target_col, *feature_cols]].dropna(subset=[target_col]).copy()
    target = data[target_col]
    if target.dtype == object:
        target = target.astype(str).str.lower().map({"won": 1, "lost": 0})
    target = target.astype(int)
    features = data[feature_cols]

    numeric_features = list(features.select_dtypes(include=["number", "bool"]).columns)
    categorical_features = [column for column in feature_cols if column not in numeric_features]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )

    stratify = target if target.nunique() > 1 else None
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    metrics = evaluate_classifier(y_test, probabilities)
    return model, metrics
