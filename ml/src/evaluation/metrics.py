"""Evaluation Metrics Module for Imbalanced Payment Fraud Classification.

Computes Precision, Recall, F1, PR-AUC, ROC-AUC, Brier Score, and Confusion Matrix.
Never fabricates metrics; all values are computed directly from actual predictions.
"""

from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
)


def compute_fraud_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    threshold: float = 0.50,
) -> Dict[str, Any]:
    """Computes all standard fraud evaluation metrics given ground truth and predicted probabilities."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    # Confusion matrix elements
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    # Rate calculations
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    # Ranking metrics (AUCs)
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except ValueError:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except ValueError:
        pr_auc = float(y_true.mean())

    # Calibration error
    brier = float(brier_score_loss(y_true, y_prob))

    return {
        "threshold": threshold,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": {
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        },
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "total_test_samples": int(len(y_true)),
        "actual_fraud_samples": int(tp + fn),
        "actual_legitimate_samples": int(tn + fp),
    }


def format_metrics_table(models_results: Dict[str, Dict[str, Any]]) -> str:
    """Formats comparison metrics into a clean markdown table."""
    md = "| Model Name | PR-AUC | ROC-AUC | Precision | Recall | F1-Score | Brier Score | FPR (%) | FNR (%) |\n"
    md += "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
    for name, m in models_results.items():
        md += (
            f"| **{name}** | {m['pr_auc']:.4f} | {m['roc_auc']:.4f} | "
            f"{m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | "
            f"{m['brier_score']:.4f} | {m['false_positive_rate']*100:.2f}% | "
            f"{m['false_negative_rate']*100:.2f}% |\n"
        )
    return md
