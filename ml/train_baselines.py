"""Train and Benchmark Baseline Machine Learning Models.

Evaluates Dummy, Logistic Regression, and Random Forest baselines on held-out temporal data.
Saves model artifacts and records actual measured metrics in docs/EXPERIMENTS.md.
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
from ml.src.models.baselines import (
    DummyBaselineModel,
    LogisticRegressionBaseline,
    RandomForestBaseline,
)
from ml.src.evaluation.metrics import compute_fraud_metrics, format_metrics_table


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate baseline models")
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed/features_dataset.parquet",
        help="Path to processed features parquet"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="ml/models/saved",
        help="Directory to save model artifacts"
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[*] Loading processed feature dataset from {args.input}...")
    df = pd.read_parquet(args.input)
    print(f"[+] Loaded {len(df)} rows. Positive fraud cases: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.2f}%).")

    # 1. Temporal Chronological Splitting
    print("[*] Performing chronological temporal splitting (70% Train, 15% Val, 15% Test)...")
    splitter = TemporalSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    split_res = splitter.split(df)
    train_df, val_df, test_df = split_res.train_df, split_res.val_df, split_res.test_df

    print(f"[+] Split boundaries:")
    print(f"    Train: {len(train_df)} samples ({split_res.boundaries['train_start']} -> {split_res.boundaries['train_end']}), fraud={train_df['is_fraud'].sum()} ({split_res.boundaries['train_fraud_rate']}%)")
    print(f"    Val  : {len(val_df)} samples ({split_res.boundaries['val_start']} -> {split_res.boundaries['val_end']}), fraud={val_df['is_fraud'].sum()} ({split_res.boundaries['val_fraud_rate']}%)")
    print(f"    Test : {len(test_df)} samples ({split_res.boundaries['test_start']} -> {split_res.boundaries['test_end']}), fraud={test_df['is_fraud'].sum()} ({split_res.boundaries['test_fraud_rate']}%)")

    # Feature matrix X and target y
    feature_cols = [c for c in FEATURE_NAMES if c in train_df.columns]
    X_train, y_train = train_df[feature_cols], train_df["is_fraud"].astype(int)
    X_val, y_val = val_df[feature_cols], val_df["is_fraud"].astype(int)
    X_test, y_test = test_df[feature_cols], test_df["is_fraud"].astype(int)

    results = {}

    # 2. Train Dummy Classifier
    print("\n[*] Training Model 1: Dummy Baseline Classifier...")
    dummy = DummyBaselineModel()
    dummy.fit(X_train.values, y_train.values)
    dummy_probs = dummy.predict_proba(X_test.values)
    results["DummyClassifier"] = compute_fraud_metrics(y_test.values, dummy_probs, threshold=0.5)
    joblib.dump(dummy, os.path.join(args.output_dir, "dummy_baseline.joblib"))

    # 3. Train Logistic Regression Baseline
    print("[*] Training Model 2: Logistic Regression (L2 Balanced)...")
    lr = LogisticRegressionBaseline(C=1.0, class_weight="balanced", random_state=42)
    lr.fit(X_train, y_train)
    lr_probs = lr.predict_proba(X_test)
    results["LogisticRegression"] = compute_fraud_metrics(y_test.values, lr_probs, threshold=0.5)
    joblib.dump(lr, os.path.join(args.output_dir, "logistic_baseline.joblib"))

    # 4. Train Random Forest Baseline
    print("[*] Training Model 3: Random Forest (100 Trees, Depth 12)...")
    rf = RandomForestBaseline(n_estimators=100, max_depth=12, class_weight="balanced", random_state=42)
    rf.fit(X_train, y_train)
    rf_probs = rf.predict_proba(X_test)
    results["RandomForest"] = compute_fraud_metrics(y_test.values, rf_probs, threshold=0.5)
    joblib.dump(rf, os.path.join(args.output_dir, "random_forest_baseline.joblib"))

    # 5. Display Evaluation Results
    print("\n" + "=" * 80)
    print("BASELINE MODELS EVALUATION (HELD-OUT TEST SET)")
    print("=" * 80)
    print(format_metrics_table(results))

    print("\nTop 5 Logistic Regression Coefficients (Log-Odds):")
    for feat, coef in lr.get_coefficients()[:5]:
        print(f"  {feat:<28} : {coef:+.4f}")

    print("\nTop 5 Random Forest Gini Feature Importances:")
    for feat, imp in rf.get_feature_importances()[:5]:
        print(f"  {feat:<28} : {imp:.4f}")
    print("=" * 80 + "\n")

    # Save metrics JSON
    metrics_path = os.path.join(args.output_dir, "baseline_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[+] Baseline metrics saved to {metrics_path}")

    # Return results for programmatic consumption or test assertions
    return results


if __name__ == "__main__":
    main()
