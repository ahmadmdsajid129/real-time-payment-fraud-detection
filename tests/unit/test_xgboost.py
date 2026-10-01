"""Unit tests for XGBoost fraud classifier."""

import pytest
import numpy as np
import pandas as pd
from ml.src.models.xgboost_model import XGBoostFraudClassifier


@pytest.fixture
def sample_training_data():
    np.random.seed(42)
    n = 200
    X = pd.DataFrame({
        "amount": np.random.exponential(scale=1000, size=n),
        "customer_amount_zscore": np.random.normal(loc=0, scale=1, size=n),
        "is_new_device": np.random.binomial(n=1, p=0.1, size=n),
        "impossible_travel": np.random.binomial(n=1, p=0.05, size=n),
        "txn_count_1h": np.random.poisson(lam=1.5, size=n),
    })
    # Target with imbalance
    y = pd.Series(np.random.binomial(n=1, p=0.05, size=n))
    return X, y


def test_xgboost_fit_and_predict_bounds(sample_training_data):
    X, y = sample_training_data
    model = XGBoostFraudClassifier(n_estimators=20, max_depth=3)
    model.fit(X, y)

    assert model.is_fitted is True
    assert model.params["scale_pos_weight"] is not None
    assert model.params["scale_pos_weight"] > 1.0  # Since positive fraud is rare

    # Predict proba
    probs = model.predict_proba(X)
    assert len(probs) == len(X)
    assert np.all((probs >= 0.0) & (probs <= 1.0))

    # Binary predict at different thresholds
    preds_lenient = model.predict(X, threshold=0.2)
    preds_strict = model.predict(X, threshold=0.8)
    assert np.sum(preds_lenient) >= np.sum(preds_strict)


def test_xgboost_feature_importances(sample_training_data):
    X, y = sample_training_data
    model = XGBoostFraudClassifier(n_estimators=20, max_depth=3)
    model.fit(X, y)

    imps = model.get_feature_importances(importance_type="gain")
    assert len(imps) == len(X.columns)
    # Check sorted descending
    for i in range(1, len(imps)):
        assert imps[i][1] <= imps[i - 1][1]

    # Verify booster can be extracted
    booster = model.get_booster()
    assert booster is not None
