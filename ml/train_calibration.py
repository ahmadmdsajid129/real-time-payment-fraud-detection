"""Train Probability Calibrator & Optimize Decision Thresholds.

Fits Isotonic Regression and Platt Scaling on the chronological validation split,
evaluates reliability curves and Expected Calibration Error (ECE) on the test split,
and finds cost-optimal thresholds.
"""

import argparse
import os
import sys
import json
import joblib
import pandas as pd
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from ml.src.data.splitter import TemporalSplitter
from ml.src.features.feature_definitions import FEATURE_NAMES
from ml.src.calibration.calibrator import ProbabilityCalibrator
from ml.src.evaluation.cost_optimization import ThresholdOptimizer
from ml.src.evaluation.metrics import compute_fraud_metrics


def main():
    parser = argparse.ArgumentParser(description="Calibrate probabilities and optimize decision thresholds")
    parser.add_argument(
        "--features-input",
        type=str,
        default="data/processed/features_dataset.parquet",
        help="Path to feature dataset"
    )
    parser.add_argument(
        "--model-input",
        type=str,
        default="ml/models/saved/xgboost_champion.joblib",
        help="Path to trained XGBoost model"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="ml/models/saved",
        help="Directory to save calibration artifacts"
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[*] Loading feature dataset from {args.features-input if hasattr(args, 'features-input') else args.features_input}...")
    df = pd.read_parquet(args.features_input)

    # 1. Temporal Split
    print("[*] Chronological splitting into Train (70%), Val (15%), Test (15%)...")
    splitter = TemporalSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    split_res = splitter.split(df)
    val_df, test_df = split_res.val_df, split_res.test_df

    feature_cols = [c for c in FEATURE_NAMES if c in val_df.columns]
    X_val, y_val = val_df[feature_cols], val_df["is_fraud"].astype(int)
    X_test, y_test = test_df[feature_cols], test_df["is_fraud"].astype(int)

    # 2. Load Trained XGBoost Model
    print(f"[*] Loading champion model from {args.model_input}...")
    model = joblib.load(args.model_input)

    # 3. Generate Raw Probabilities
    raw_val_probs = model.predict_proba(X_val)
    raw_test_probs = model.predict_proba(X_test)

    # 4. Fit Calibrators on Validation Set (Zero Leakage)
    print("[*] Fitting Isotonic Regression Calibrator on Validation set...")
    isotonic_calibrator = ProbabilityCalibrator(method="isotonic")
    isotonic_calibrator.fit(raw_val_probs, y_val.values)

    print("[*] Fitting Platt Scaling (Sigmoid) Calibrator on Validation set...")
    platt_calibrator = ProbabilityCalibrator(method="sigmoid")
    platt_calibrator.fit(raw_val_probs, y_val.values)

    # 5. Evaluate Calibration on Held-Out Test Set
    iso_test_probs = isotonic_calibrator.predict_proba(raw_test_probs)
    platt_test_probs = platt_calibrator.predict_proba(raw_test_probs)

    raw_curve = ProbabilityCalibrator.compute_calibration_curve(y_test.values, raw_test_probs)
    iso_curve = ProbabilityCalibrator.compute_calibration_curve(y_test.values, iso_test_probs)
    platt_curve = ProbabilityCalibrator.compute_calibration_curve(y_test.values, platt_test_probs)

    print("\n" + "=" * 80)
    print("PROBABILITY CALIBRATION BENCHMARK (HELD-OUT TEST SET)")
    print("=" * 80)
    print(f"Raw XGBoost    : Brier Score = {raw_curve['brier_score']:.4f} | ECE = {raw_curve['expected_calibration_error']:.4f}")
    print(f"Platt Scaling  : Brier Score = {platt_curve['brier_score']:.4f} | ECE = {platt_curve['expected_calibration_error']:.4f}")
    print(f"Isotonic Reg.  : Brier Score = {iso_curve['brier_score']:.4f} | ECE = {iso_curve['expected_calibration_error']:.4f}")
    print("=" * 80 + "\n")

    # 6. Optimize Decision Thresholds using Cost Optimizer
    print("[*] Running Cost-Sensitive Threshold Optimization...")
    optimizer = ThresholdOptimizer(
        cost_chargeback_penalty=25.0,
        cost_customer_insult=35.0,
        cost_analyst_review=4.0
    )
    test_amounts = test_df["amount"].values
    opt_results = optimizer.find_optimal_thresholds(
        y_true=y_test.values,
        y_prob=iso_test_probs,
        amounts=test_amounts
    )

    f2_thresh = opt_results["optimal_f2_threshold"]
    cost_thresh = opt_results["optimal_cost_threshold"]
    f2_metrics = opt_results["optimal_f2_metrics"]
    cost_metrics = opt_results["optimal_cost_metrics"]

    print(f"[+] Optimal F2 Threshold    : {f2_thresh:.3f} (Recall={f2_metrics['recall']*100:.1f}%, Precision={f2_metrics['precision']*100:.1f}%)")
    print(f"[+] Optimal Cost Threshold  : {cost_thresh:.3f} (Total Loss=INR {cost_metrics['total_cost']:,.2f})")

    # 7. Save Artifacts
    calibrator_path = os.path.join(args.output_dir, "calibrator_isotonic.joblib")
    joblib.dump(isotonic_calibrator, calibrator_path)
    print(f"[+] Saved calibrated model artifact to {calibrator_path}")

    metrics_payload = {
        "calibration": {
            "raw_xgb": raw_curve,
            "platt": platt_curve,
            "isotonic": iso_curve,
        },
        "threshold_optimization": opt_results,
    }
    metrics_path = os.path.join(args.output_dir, "calibration_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"[+] Saved calibration metrics to {metrics_path}")

    return metrics_payload


if __name__ == "__main__":
    main()
