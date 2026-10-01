"""Train and Evaluate Primary XGBoost Fraud Classifier.

Optimizes gradient-boosted trees on temporal train/val splits and benchmarks
performance against baselines on the held-out test set.
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
from ml.src.models.xgboost_model import XGBoostFraudClassifier
from ml.src.evaluation.metrics import compute_fraud_metrics, format_metrics_table


def main():
    parser = argparse.ArgumentParser(description="Train primary XGBoost fraud classifier")
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

    print(f"[*] Loading feature dataset from {args.input}...")
    df = pd.read_parquet(args.input)
    print(f"[+] Loaded {len(df)} rows. Fraud count: {df['is_fraud'].sum()} ({df['is_fraud'].mean()*100:.2f}%).")

    # 1. Temporal Split
    print("[*] Performing chronological temporal splitting...")
    splitter = TemporalSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    split_res = splitter.split(df)
    train_df, val_df, test_df = split_res.train_df, split_res.val_df, split_res.test_df

    feature_cols = [c for c in FEATURE_NAMES if c in train_df.columns]
    X_train, y_train = train_df[feature_cols], train_df["is_fraud"].astype(int)
    X_val, y_val = val_df[feature_cols], val_df["is_fraud"].astype(int)
    X_test, y_test = test_df[feature_cols], test_df["is_fraud"].astype(int)

    # 2. Train XGBoost
    print("\n[*] Initializing and Training XGBoost Primary Classifier...")
    model = XGBoostFraudClassifier(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.05,
        reg_lambda=1.0,
        random_state=42,
    )

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )
    print(f"[+] XGBoost training complete. Optimal scale_pos_weight: {model.params['scale_pos_weight']}")

    # 3. Evaluate on Held-Out Test Set
    y_test_probs = model.predict_proba(X_test)
    xgb_metrics = compute_fraud_metrics(y_test.values, y_test_probs, threshold=0.5)

    # Load baseline metrics if present to display complete leaderboard
    baseline_metrics_path = os.path.join(args.output_dir, "baseline_metrics.json")
    all_results = {}
    if os.path.exists(baseline_metrics_path):
        with open(baseline_metrics_path, "r", encoding="utf-8") as f:
            all_results = json.load(f)

    all_results["XGBoost (Primary)"] = xgb_metrics

    print("\n" + "=" * 80)
    print("COMPLETE MODEL LEADERBOARD (HELD-OUT TEST SET)")
    print("=" * 80)
    print(format_metrics_table(all_results))

    print("\nTop 8 XGBoost Feature Importances (Gain):")
    for feat, gain in model.get_feature_importances(importance_type="gain")[:8]:
        print(f"  {feat:<28} : {gain:.4f}")
    print("=" * 80 + "\n")

    # 4. Save Artifacts
    model_path = os.path.join(args.output_dir, "xgboost_champion.joblib")
    joblib.dump(model, model_path)
    print(f"[+] Saved XGBoost champion model artifact to {model_path}")

    metrics_path = os.path.join(args.output_dir, "xgboost_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(xgb_metrics, f, indent=2)
    print(f"[+] Saved XGBoost metrics to {metrics_path}")

    return xgb_metrics


if __name__ == "__main__":
    main()
