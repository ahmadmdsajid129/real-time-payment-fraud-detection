"""Threshold Optimization and Cost-Sensitive Decision Analysis.

Calculates optimal classification cutoffs by maximizing F-beta score (beta=2)
and minimizing expected financial loss across false positive vs. false negative costs.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, fbeta_score


class ThresholdOptimizer:
    """Finds optimal decision thresholds based on business loss matrix and F2 score."""

    def __init__(
        self,
        cost_chargeback_penalty: float = 25.0,
        cost_customer_insult: float = 35.0,
        cost_analyst_review: float = 4.0,
    ):
        self.c_chargeback = cost_chargeback_penalty
        self.c_insult = cost_customer_insult
        self.c_review = cost_analyst_review

    def evaluate_threshold_grid(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        amounts: Optional[np.ndarray] = None,
        thresholds: Optional[np.ndarray] = None,
    ) -> pd.DataFrame:
        """Sweeps thresholds and evaluates Precision, Recall, F1, F2, and Financial Loss."""
        y_true = np.asarray(y_true, dtype=int)
        y_prob = np.asarray(y_prob, dtype=float)
        if amounts is None:
            amounts = np.full(len(y_true), 1500.0)  # average basket assumption
        else:
            amounts = np.asarray(amounts, dtype=float)

        if thresholds is None:
            thresholds = np.linspace(0.01, 0.99, 99)

        records = []
        for t in thresholds:
            y_pred = (y_prob >= t).astype(int)

            tp_mask = (y_true == 1) & (y_pred == 1)
            fp_mask = (y_true == 0) & (y_pred == 1)
            fn_mask = (y_true == 1) & (y_pred == 0)
            tn_mask = (y_true == 0) & (y_pred == 0)

            tp = int(np.sum(tp_mask))
            fp = int(np.sum(fp_mask))
            fn = int(np.sum(fn_mask))
            tn = int(np.sum(tn_mask))

            precision = float(precision_score(y_true, y_pred, zero_division=0))
            recall = float(recall_score(y_true, y_pred, zero_division=0))
            f1 = float(fbeta_score(y_true, y_pred, beta=1.0, zero_division=0))
            f2 = float(fbeta_score(y_true, y_pred, beta=2.0, zero_division=0))

            # Financial Cost Calculation
            # FN Cost: Lost transaction amount + chargeback fee
            fn_loss = float(np.sum(amounts[fn_mask]) + (fn * self.c_chargeback))
            # FP Cost: Lost interchange + insulted customer churn lifetime value decay
            fp_loss = float(fp * self.c_insult)
            total_cost = fn_loss + fp_loss

            records.append({
                "threshold": round(float(t), 3),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "f2": round(f2, 4),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "fn_loss": round(fn_loss, 2),
                "fp_loss": round(fp_loss, 2),
                "total_cost": round(total_cost, 2),
            })

        return pd.DataFrame(records)

    def find_optimal_thresholds(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
        amounts: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Finds both F2-optimal and Cost-optimal operating thresholds."""
        df = self.evaluate_threshold_grid(y_true, y_prob, amounts=amounts)

        # 1. Best F2 threshold (prioritizing recall twice as heavily as precision)
        best_f2_row = df.loc[df["f2"].idxmax()]

        # 2. Best Cost threshold (minimizing total financial loss)
        best_cost_row = df.loc[df["total_cost"].idxmin()]

        return {
            "optimal_f2_threshold": float(best_f2_row["threshold"]),
            "optimal_f2_metrics": best_f2_row.to_dict(),
            "optimal_cost_threshold": float(best_cost_row["threshold"]),
            "optimal_cost_metrics": best_cost_row.to_dict(),
        }
