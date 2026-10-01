"""CLI Runner for Statistical Feature and Prediction Drift Analysis.

Evaluates reference training features against recent production events using PSI and KS-test.
Emits data/processed/drift_report.json.
"""

import json
import os
import numpy as np
import pandas as pd

from ml.src.monitoring.drift_detector import DataDriftDetector
from ml.src.features.feature_definitions import NUMERICAL_FEATURES


def run_drift_assessment(
    reference_path: str = "data/processed/features_dataset.parquet",
    output_path: str = "data/processed/drift_report.json",
):
    print("=" * 80)
    print("STATISTICAL DATA DRIFT & COVARIATE SHIFT ASSESSMENT (PSI & KS-TEST)")
    print("=" * 80)

    if not os.path.exists(reference_path):
        print(f"Reference dataset not found at {reference_path}. Generating synthetic reference...")
        from ml.src.features.build_features import build_features_pipeline
        build_features_pipeline()

    ref_df = pd.read_parquet(reference_path)
    print(f"Loaded reference dataset: {len(ref_df):,} rows from {reference_path}")

    # Generate current production window with synthetic drift scenario
    # (e.g. 10% amount inflation and velocity burst in recent transactions)
    np.random.seed(99)
    current_df = ref_df.sample(frac=0.3, replace=True, random_state=99).copy()
    current_df["amount"] = current_df["amount"] * np.random.uniform(1.05, 1.45, size=len(current_df))
    current_df["customer_amount_zscore"] = current_df["customer_amount_zscore"] + np.random.normal(0.4, 0.2, size=len(current_df))

    features_to_monitor = [f for f in NUMERICAL_FEATURES if f in ref_df.columns]
    print(f"Monitoring {len(features_to_monitor)} numerical features...")

    detector = DataDriftDetector()
    report = detector.analyze_dataset_drift(ref_df, current_df, features=features_to_monitor)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\nDrift Analysis Results:")
    print(f"Overall Status: {report['overall_status']}")
    print(f"Features Monitored: {report['total_features_monitored']}")
    print(f"Drifted Features:   {report['drifted_features_count']} ({report['critical_features_count']} Critical)")
    print("-" * 80)
    print(f"{'Feature':<26} | {'PSI':<8} | {'KS Stat':<8} | {'P-Value':<10} | {'Status'}")
    print("-" * 80)
    for feat, res in report["feature_reports"].items():
        print(f"{feat:<26} | {res['psi']:<8.4f} | {res['ks_statistic']:<8.4f} | {res['p_value']:<10.4e} | {res['status']}")
    print("-" * 80)
    print(f"Drift report exported to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    run_drift_assessment()
