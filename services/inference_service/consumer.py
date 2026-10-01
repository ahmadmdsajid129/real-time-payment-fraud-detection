"""Real-Time ML Inference Consumer Worker.

Listens to `transactions.features`, runs XGBoost champion classifier, Isotonic
probability calibration, unsupervised Isolation Forest anomaly detection,
computes SHAP local explanations, and publishes to `transactions.predictions`.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

import joblib
import numpy as np
import pandas as pd
import shap

from ml.src.features.feature_definitions import FEATURE_NAMES
from ml.src.features.behavioral_profiler import BehavioralProfiler
from services.streaming_client import StreamConsumer, StreamProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("inference-service")


class MLInferenceWorker:
    """Consumes feature-enriched transactions and evaluates multi-model ML inference."""

    def __init__(
        self,
        consumer: Optional[StreamConsumer] = None,
        producer: Optional[StreamProducer] = None,
        models_dir: str = "ml/models/saved",
    ):
        self.consumer = consumer or StreamConsumer(
            topic="transactions.features",
            group_id=os.getenv("KAFKA_CONSUMER_GROUP_INFERENCE", "ml-inference-group"),
        )
        self.producer = producer or StreamProducer()
        self.models_dir = models_dir

        self.model = None
        self.calibrator = None
        self.anomaly_detector = None
        self.profiler = BehavioralProfiler()
        self.shap_explainer = None

        self._load_models()

    def _load_models(self):
        """Loads serialized champion models and calibrators."""
        xgb_path = os.path.join(self.models_dir, "xgboost_champion.joblib")
        calib_path = os.path.join(self.models_dir, "calibrator_isotonic.joblib")
        iforest_path = os.path.join(self.models_dir, "isolation_forest_detector.joblib")

        try:
            if os.path.exists(xgb_path):
                self.model = joblib.load(xgb_path)
                logger.info("Loaded XGBoost champion model from %s", xgb_path)
                try:
                    underlying = getattr(self.model, "model", self.model)
                    self.shap_explainer = shap.TreeExplainer(underlying)
                    logger.info("Initialized TreeExplainer for SHAP local attributions")
                except Exception as e:
                    logger.warning("Could not initialize TreeExplainer: %s", e)
            else:
                logger.warning("XGBoost model not found at %s", xgb_path)

            if os.path.exists(calib_path):
                self.calibrator = joblib.load(calib_path)
                logger.info("Loaded Isotonic Calibrator from %s", calib_path)

            if os.path.exists(iforest_path):
                self.anomaly_detector = joblib.load(iforest_path)
                logger.info("Loaded Isolation Forest detector from %s", iforest_path)
        except Exception as e:
            logger.error("Error loading model artifacts: %s", e)

    def compute_shap_drivers(self, X_df: pd.DataFrame) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Calculates real SHAP feature attributions for local explainability."""
        if self.shap_explainer is None:
            return [], []
        try:
            shap_values = self.shap_explainer.shap_values(X_df)
            if isinstance(shap_values, list) and len(shap_values) > 1:
                vals = shap_values[1][0]
            elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 2:
                vals = shap_values[0]
            else:
                vals = shap_values

            feature_impacts = [
                {"feature": col, "impact": round(float(v), 4)}
                for col, v in zip(X_df.columns, vals)
            ]

            # Top positive fraud risk drivers
            pos_drivers = sorted([f for f in feature_impacts if f["impact"] > 0], key=lambda x: x["impact"], reverse=True)[:3]
            # Top negative / mitigating fraud risk drivers
            neg_drivers = sorted([f for f in feature_impacts if f["impact"] < 0], key=lambda x: x["impact"])[:3]

            return pos_drivers, neg_drivers
        except Exception as e:
            logger.warning("SHAP calculation error: %s", e)
            return [], []

    def evaluate_transaction(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the full inference pipeline on a feature dictionary."""
        start_time = time.perf_counter()

        # Build single-row DataFrame aligned with FEATURE_NAMES
        row = {col: features.get(col, 0.0) for col in FEATURE_NAMES}
        X_df = pd.DataFrame([row], columns=FEATURE_NAMES).fillna(0.0)

        # 1. Supervised XGBoost Inference
        if self.model is not None:
            p = self.model.predict_proba(X_df)
            raw_proba = float(p[0]) if p.ndim == 1 else float(p[0, 1])
        else:
            raw_proba = 0.05

        # 2. Probability Calibration
        if self.calibrator is not None:
            if hasattr(self.calibrator, "predict_proba"):
                calibrated_p = float(self.calibrator.predict_proba(np.array([raw_proba]))[0])
            else:
                calibrated_p = float(self.calibrator.predict(np.array([raw_proba]))[0])
        else:
            calibrated_p = raw_proba

        # 3. Unsupervised Anomaly Scoring
        if self.anomaly_detector is not None:
            if hasattr(self.anomaly_detector, "score"):
                anomaly_score = float(self.anomaly_detector.score(X_df)[0])
            elif hasattr(self.anomaly_detector, "score_single"):
                anomaly_score = float(self.anomaly_detector.score_single(features))
            else:
                anomaly_score = 0.1
        else:
            anomaly_score = 0.1

        # 4. Behavioral Profiling Score
        behav_score, _ = self.profiler.score_behavior(features)

        # 5. Local SHAP Attribution
        pos_drivers, neg_drivers = self.compute_shap_drivers(X_df)

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "raw_score": round(raw_proba, 4),
            "calibrated_probability": round(calibrated_p, 4),
            "anomaly_score": round(anomaly_score, 4),
            "behavioral_score": round(behav_score, 4),
            "inference_latency_ms": round(latency_ms, 2),
            "shap_positive_drivers": pos_drivers,
            "shap_negative_drivers": neg_drivers,
            "model_version_id": "xgboost-champion-v1.0",
        }

    def process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a single feature-enriched event."""
        payload = message.get("value", message)
        txn_id = payload.get("transaction_id")
        cust_id = payload.get("customer_id")
        features = payload.get("features", {})

        if not txn_id or not features:
            logger.warning("Invalid features payload: %s", payload)
            self.consumer.route_error(payload, "Missing features or transaction_id", "inference_service")
            return None

        model_outputs = self.evaluate_transaction(features)

        prediction_event = {
            **payload,
            "model_outputs": model_outputs,
            "evaluated_at": time.time(),
        }

        # Publish to transactions.predictions
        self.producer.send(
            topic="transactions.predictions",
            key=cust_id,
            value=prediction_event,
        )
        logger.info(
            "Inference TXN %s | P(Fraud): %.3f (calib: %.3f) | Anom: %.2f | Latency: %.2fms",
            txn_id,
            model_outputs["raw_score"],
            model_outputs["calibrated_probability"],
            model_outputs["anomaly_score"],
            model_outputs["inference_latency_ms"],
        )

        self.consumer.commit(message.get("raw"))
        return prediction_event

    def run_worker_poll(self, max_messages: Optional[int] = None):
        """Worker loop polling events on transactions.features."""
        logger.info("ML Inference worker started. Awaiting events on transactions.features...")
        processed = 0
        while max_messages is None or processed < max_messages:
            msg = self.consumer.poll(timeout_sec=0.5)
            if msg:
                self.process_message(msg)
                processed += 1
            else:
                time.sleep(0.05)


if __name__ == "__main__":
    worker = MLInferenceWorker()
    worker.run_worker_poll()
