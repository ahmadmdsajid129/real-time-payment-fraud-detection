"""Unit tests for data validator ensuring domain constraints and error reporting."""

from datetime import datetime, timezone
import pandas as pd
import pytest
from ml.src.data.validator import DataValidator
from ml.src.data.synthetic_generator import TransactionGenerator


@pytest.fixture
def sample_valid_df():
    gen = TransactionGenerator(seed=42)
    txns = gen.generate_stream(
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        num_transactions=50,
        fraud_ratio=0.04
    )
    return gen.to_dataframe(txns)


def test_valid_dataframe_passes(sample_valid_df):
    validator = DataValidator()
    report = validator.validate(sample_valid_df)
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.total_records == 50
    assert report.summary_stats["amount_mean"] > 0


def test_missing_column_fails(sample_valid_df):
    df_missing = sample_valid_df.drop(columns=["customer_id"])
    validator = DataValidator()
    report = validator.validate(df_missing)
    assert report.is_valid is False
    assert any("customer_id" in err for err in report.errors)


def test_null_value_fails(sample_valid_df):
    df_null = sample_valid_df.copy()
    df_null.loc[0, "amount"] = None
    validator = DataValidator()
    report = validator.validate(df_null)
    assert report.is_valid is False
    assert any("amount" in err for err in report.errors)


def test_negative_amount_fails(sample_valid_df):
    df_neg = sample_valid_df.copy()
    df_neg.loc[2, "amount"] = -50.0
    validator = DataValidator()
    report = validator.validate(df_neg)
    assert report.is_valid is False
    assert any("amount <= 0" in err for err in report.errors)


def test_invalid_coordinates_fail(sample_valid_df):
    df_coords = sample_valid_df.copy()
    df_coords.loc[5, "lat"] = 120.0  # Latitude exceeds 90 degrees
    validator = DataValidator()
    report = validator.validate(df_coords)
    assert report.is_valid is False
    assert any("coordinate boundary" in err for err in report.errors)
