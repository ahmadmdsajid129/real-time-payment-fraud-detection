"""Train Unsupervised Anomaly Detection Model (Isolation Forest).

Evaluates structural outlier scores on held-out test data and exports model artifacts.
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
from ml.src.anomaly.isolation_forest import IsolationForestDetector
from ml.src.features.behavioral_profiler import BehavioralProfiler


def main():
    parser = argparse.ArgumentParser(description="Train unsupervised Isolation Forest detector")
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed/features_dataset.parquet",
        help="Path to feature dataset"
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

    # 1. Temporal Split
    print("[*] Performing temporal split...")
    splitter = TemporalSplitter(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15)
    split_res = splitter.split(df)
    train_df, test_df = split_res.train_df, split_res.test_df

    # 2. Train Isolation Forest Detector
    print("[*] Training Isolation Forest detector on training features...")
    detector = IsolationForestDetector(n_estimators=120, contamination=0.03, random_state=42)
    detector.fit(train_df)
    print(f"[+] Fitted detector on {len(detector.feature_names)} features: {detector.feature_names}")

    # 3. Score Held-Out Test Set
    test_scores = detector.score(test_df)
    y_test = test_df["is_fraud"].astype(int).values

    # Evaluate correlation and separation between normal and fraud transactions
    mean_normal_score = float(np.mean(test_scores[y_test == 0]))
    mean_fraud_score = float(np.mean(test_scores[y_test == 1]))
    corr_with_fraud = float(np.corrcoef(test_scores, y_test)[0, 1])

    # Behavioral Profile scoring on test set
    behavioral_scores = []
    for _, row in test_df.iterrows():
        b_score, _ = BehavioralProfiler.score_behavior(row.to_dict())
        behavioral_scores.append(b_score)
    behavioral_scores = np.array(behavioral_scores)
    b_corr = float(np.corrcoef(behavioral_scores, y_test)[0, 1])

    print("\n" + "=" * 80)
    print("UNSUPERVISED ANOMALY & BEHAVIORAL SCORING EVALUATION")
    print("=" * 80)
    print(f"Isolation Forest Anomaly Score:")
    print(f"  Mean Score for Legitimate Transactions : {mean_normal_score:.4f}")
    print(f"  Mean Score for Fraudulent Transactions : {mean_fraud_score:.4f}")
    print(f"  Correlation with Ground-Truth Fraud    : {corr_with_fraud:+.4f}")
    print(f"\nBehavioral Deviation Score:")
    print(f"  Correlation with Ground-Truth Fraud    : {b_corr:+.4f}")
    print("=" * 80 + "\n")

    # 4. Save Model Artifact
    model_path = os.path.join(args.output_dir, "isolation_forest_detector.joblib")
    joblib.dump(detector, model_path)
    print(f"[+] Saved Isolation Forest model to {model_path}")

    metrics_payload = {
        "isolation_forest": {
            "mean_normal_score": round(mean_normal_score, 4),
            "mean_fraud_score": round(mean_fraud_score, 4),
            "correlation_with_fraud": round(corr_with_fraud, 4),
            "features_used": detector.feature_names,
        },
        "behavioral_profiler": {
            "correlation_with_fraud": round(b_corr, 4),
        }
    }
    metrics_path = os.path.join(args.output_dir, "anomaly_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"[+] Saved anomaly metrics to {metrics_path}")

    return metrics_payload


if __name__ == "__main__":
    main()
