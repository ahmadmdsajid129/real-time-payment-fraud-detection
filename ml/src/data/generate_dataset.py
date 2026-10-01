"""CLI Script to generate synthetic benchmark dataset, validate integrity, and output EDA.

Usage:
    python ml/src/data/generate_dataset.py --num-txns 15000 --fraud-ratio 0.018
"""

import argparse
from datetime import datetime, timezone
import os
import sys
import json
import pandas as pd

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ml.src.data.synthetic_generator import TransactionGenerator
from ml.src.data.validator import DataValidator
from ml.src.data.eda import ExploratoryDataAnalysis


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic payment dataset")
    parser.add_argument("--num-txns", type=int, default=15000, help="Number of transactions to generate")
    parser.add_argument("--fraud-ratio", type=float, default=0.018, help="Target fraud ratio (e.g. 0.018 for 1.8%)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output-dir", type=str, default="data/synthetic", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    print(f"[*] Initializing generator with seed={args.seed}...")
    generator = TransactionGenerator(seed=args.seed)
    generator.generate_population(num_customers=1000, num_merchants=100)

    start_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    print(f"[*] Generating {args.num_txns} transactions starting at {start_time} (fraud_ratio={args.fraud_ratio})...")
    txns = generator.generate_stream(
        start_time=start_time,
        num_transactions=args.num_txns,
        fraud_ratio=args.fraud_ratio,
        avg_seconds_between_txns=8.0,
    )

    df = generator.to_dataframe(txns)
    print(f"[+] Generated {len(df)} transactions spanning from {df['timestamp'].min()} to {df['timestamp'].max()}.")

    # Validation
    print("[*] Running data validation checks...")
    validator = DataValidator()
    report = validator.validate(df)
    if not report.is_valid:
        print(f"[!] Validation FAILED with errors: {report.errors}")
        raise ValueError(f"Data validation failed: {report.errors}")
    print(f"[+] Validation PASSED: {report.total_records} rows, {report.fraud_count} fraud ({report.fraud_ratio_pct}%).")

    # Save to disk
    csv_path = os.path.join(args.output_dir, "transactions.csv")
    parquet_path = os.path.join(args.output_dir, "transactions.parquet")
    print(f"[*] Saving dataset to {csv_path} and {parquet_path}...")
    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    # Save customer & merchant profiles
    cust_records = [c.model_dump() for c in generator.customers.values()]
    merch_records = [m.model_dump() for m in generator.merchants.values()]
    pd.DataFrame(cust_records).to_json(os.path.join(args.output_dir, "customers.json"), orient="records", indent=2)
    pd.DataFrame(merch_records).to_json(os.path.join(args.output_dir, "merchants.json"), orient="records", indent=2)

    # Run EDA
    print("[*] Computing Exploratory Data Analysis (EDA)...")
    eda = ExploratoryDataAnalysis(df)
    eda_summary = eda.compute_summary_report()
    eda_md = eda.generate_markdown_report()

    eda_doc_path = "docs/DATASET.md"
    with open(eda_doc_path, "w", encoding="utf-8") as f:
        f.write(eda_md)
    print(f"[+] EDA report saved to {eda_doc_path}.")

    # Output short terminal summary
    print("\n" + "=" * 60)
    print("DATASET GENERATION & VALIDATION COMPLETE")
    print("=" * 60)
    print(f"Total Transactions : {len(df):,}")
    print(f"Fraud Count        : {report.fraud_count:,} ({report.fraud_ratio_pct}%)")
    print(f"Date Span          : {df['timestamp'].min()} -> {df['timestamp'].max()}")
    print(f"Mean Amount        : INR {df['amount'].mean():.2f}")
    print(f"Max Amount         : INR {df['amount'].max():.2f}")
    print(f"Output Artifacts   : {csv_path}, {parquet_path}, {eda_doc_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
