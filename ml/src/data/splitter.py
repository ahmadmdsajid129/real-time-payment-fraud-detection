"""Temporal Data Splitting Engine for Time-Series Payment Fraud.

Strict Requirement: Chronological splitting without random shuffling.
Train <= t1 < Val <= t2 < Test.
"""

from typing import Tuple, Dict, Any
import pandas as pd


class TemporalSplitResult:
    """Encapsulates temporally split DataFrames and boundary timestamps."""

    def __init__(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        test_df: pd.DataFrame,
        boundaries: Dict[str, Any]
    ):
        self.train_df = train_df
        self.val_df = val_df
        self.test_df = test_df
        self.boundaries = boundaries


class TemporalSplitter:
    """Partitions time-sorted payment DataFrames into Train, Validation, and Test sets."""

    def __init__(self, train_ratio: float = 0.70, val_ratio: float = 0.15, test_ratio: float = 0.15):
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-5, "Ratios must sum to 1.0"
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

    def split(self, df: pd.DataFrame, timestamp_col: str = "timestamp") -> TemporalSplitResult:
        if df.empty:
            raise ValueError("Cannot split an empty DataFrame.")

        # Ensure sorted chronologically
        df_sorted = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df_sorted[timestamp_col]):
            df_sorted[timestamp_col] = pd.to_datetime(df_sorted[timestamp_col])
        df_sorted.sort_values(by=timestamp_col, inplace=True)
        df_sorted.reset_index(drop=True, inplace=True)

        n = len(df_sorted)
        train_end_idx = int(n * self.train_ratio)
        val_end_idx = train_end_idx + int(n * self.val_ratio)

        train_df = df_sorted.iloc[:train_end_idx].copy().reset_index(drop=True)
        val_df = df_sorted.iloc[train_end_idx:val_end_idx].copy().reset_index(drop=True)
        test_df = df_sorted.iloc[val_end_idx:].copy().reset_index(drop=True)

        boundaries = {
            "total_samples": n,
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "train_start": str(train_df[timestamp_col].min()),
            "train_end": str(train_df[timestamp_col].max()),
            "val_start": str(val_df[timestamp_col].min()),
            "val_end": str(val_df[timestamp_col].max()),
            "test_start": str(test_df[timestamp_col].min()),
            "test_end": str(test_df[timestamp_col].max()),
            "train_fraud_rate": round(float(train_df["is_fraud"].mean() * 100.0), 3),
            "val_fraud_rate": round(float(val_df["is_fraud"].mean() * 100.0), 3),
            "test_fraud_rate": round(float(test_df["is_fraud"].mean() * 100.0), 3),
        }

        # Assert no temporal overlap
        assert train_df[timestamp_col].max() <= val_df[timestamp_col].min(), "Train/Val timestamp overlap detected!"
        assert val_df[timestamp_col].max() <= test_df[timestamp_col].min(), "Val/Test timestamp overlap detected!"

        return TemporalSplitResult(train_df, val_df, test_df, boundaries)
