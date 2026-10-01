"""CLI Script to extract all behavioral features from raw transactions.

Usage:
    python ml/src/features/build_features.py --input data/synthetic/transactions.parquet --output data/processed/features_dataset.parquet
"""

import argparse
import os
import sys
import json
import pandas as pd
import numpy as np

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ml.src.features.feature_extractor import FeatureExtractor
from ml.src.features.feature_definitions import FEATURE_NAMES, NUMERICAL_FEATURES


def main():
    parser = argparse.ArgumentParser(description="Extract behavioral features with zero temporal leakage")
    parser.add_argument(
        "--input",
        type=str,
        default="data/synthetic/transactions.parquet",
        help="Input transactions parquet path"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/features_dataset.parquet",
        help="Output enriched features parquet path"
    )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    print(f"[*] Reading input transactions from {args.input}...")
    df = pd.read_parquet(args.input)
    print(f"[+] Loaded {len(df)} transactions spanning {df['timestamp'].min()} to {df['timestamp'].max()}.")

    # Load customer profiles if present
    cust_path = "data/synthetic/customers.json"
    cust_profiles = None
    if os.path.exists(cust_path):
        with open(cust_path, "r", encoding="utf-8") as f:
            profiles_list = json.load(f)
            cust_profiles = {p["customer_id"]: p for p in profiles_list}
            print(f"[+] Loaded {len(cust_profiles)} customer profiles for diurnal baseline matching.")

    print("[*] Running chronological zero-leakage feature extraction...")
    extractor = FeatureExtractor()
    features_df = extractor.extract_features_batch(df, customer_profiles=cust_profiles)

    # Check for NaNs
    nan_counts = features_df[FEATURE_NAMES].isna().sum()
    cols_with_nans = nan_counts[nan_counts > 0].to_dict()
    if cols_with_nans:
        print(f"[!] Warning: NaNs detected in features: {cols_with_nans}. Filling with defaults.")
        features_df.fillna(0.0, inplace=True)
    else:
        print("[+] Zero NaNs detected in feature matrix.")

    print(f"[*] Saving processed features to {args.output}...")
    features_df.to_parquet(args.output, index=False)

    # Save small CSV sample for inspection
    sample_csv = "data/processed/features_sample.csv"
    features_df.head(200).to_csv(sample_csv, index=False)
    print(f"[+] Saved sample CSV preview to {sample_csv}.")

    # Compute Feature Correlation with Fraud Label
    print("\n" + "=" * 60)
    print("TOP 10 FEATURES CORRELATED WITH FRAUD")
    print("=" * 60)
    corrs = []
    for col in FEATURE_NAMES:
        if col in features_df.columns:
            c = features_df[col].corr(features_df["is_fraud"].astype(float))
            corrs.append((col, c))
    corrs.sort(key=lambda x: abs(x[1]) if not np.isnan(x[1]) else 0, reverse=True)
    for col, c in corrs[:10]:
        print(f"{col:<28} : {c:+.4f}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
