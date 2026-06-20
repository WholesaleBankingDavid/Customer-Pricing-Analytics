"""Model evaluation helpers for win-probability classifiers."""

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
)


def calculate_brier_score(y_true, y_probability) -> float:
    """Return Brier score for probability estimates."""

    return float(brier_score_loss(y_true, y_probability))


def evaluate_classifier(y_true, y_probability, threshold: float = 0.5) -> dict:
    """Evaluate a binary classifier using probability outputs."""

    y_pred = np.asarray(y_probability) >= threshold
    metrics = {
        "brier_score": calculate_brier_score(y_true, y_probability),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }

    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_probability))
        metrics["pr_auc"] = float(average_precision_score(y_true, y_probability))
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None

    return metrics


def create_decile_lift_table(y_true, y_probability) -> pd.DataFrame:
    """Create a decile lift table sorted by predicted probability."""

    df = pd.DataFrame({"actual": y_true, "probability": y_probability})
    df = df.sort_values("probability", ascending=False).reset_index(drop=True)
    df["decile"] = pd.qcut(df.index + 1, q=10, labels=False, duplicates="drop") + 1
    overall_rate = df["actual"].mean()
    table = df.groupby("decile").agg(
        count=("actual", "size"),
        observed_rate=("actual", "mean"),
        avg_probability=("probability", "mean"),
    )
    table["lift"] = table["observed_rate"] / overall_rate if overall_rate else np.nan
    return table.reset_index()


def calibration_summary(y_true, y_probability, n_bins: int = 10) -> pd.DataFrame:
    """Return observed and predicted probability by calibration bin."""

    prob_true, prob_pred = calibration_curve(
        y_true,
        y_probability,
        n_bins=n_bins,
        strategy="uniform",
    )
    return pd.DataFrame(
        {"mean_predicted_probability": prob_pred, "observed_win_rate": prob_true}
    )
