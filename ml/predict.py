from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from backend.config import get_config


@dataclass
class PredictionResult:
    t21_probability: float
    t21_percentage: float
    t21_risk_level: str
    t18_probability: float
    t18_percentage: float
    t18_risk_level: str
    selected_models: dict[str, str]
    feature_contributions: dict[str, list[dict[str, Any]]]


def _risk_category(probability: float, low_threshold: float, high_threshold: float) -> str:
    if probability < low_threshold:
        return "Prototype Low Screening Risk"
    if probability < high_threshold:
        return "Prototype Moderate Screening Risk"
    return "Prototype High Screening Risk"


class ScreeningPredictor:
    def __init__(self, model_dir: str | Path | None = None) -> None:
        config = get_config()
        self.model_dir = Path(model_dir or config.MODEL_DIR)
        self.metadata_path = self.model_dir / "model_metadata.json"
        self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8")) if self.metadata_path.exists() else {}
        self.t21_model = joblib.load(self.model_dir / "t21_model.joblib") if (self.model_dir / "t21_model.joblib").exists() else None
        self.t18_model = joblib.load(self.model_dir / "t18_model.joblib") if (self.model_dir / "t18_model.joblib").exists() else None
        self.t21_preprocessor = joblib.load(self.model_dir / "preprocessing_t21.joblib") if (self.model_dir / "preprocessing_t21.joblib").exists() else None
        self.t18_preprocessor = joblib.load(self.model_dir / "preprocessing_t18.joblib") if (self.model_dir / "preprocessing_t18.joblib").exists() else None

    def artifact_ready(self) -> bool:
        return all([self.t21_model, self.t18_model, self.t21_preprocessor, self.t18_preprocessor])

    def _feature_columns(self) -> list[str]:
        feature_specs = self.metadata.get("feature_specs", {})
        if feature_specs:
            return list(feature_specs.keys())
        return []

    def _validate_payload(self, payload: dict[str, Any]) -> pd.DataFrame:
        feature_specs = self.metadata.get("feature_specs", {})
        if not feature_specs:
            raise ValueError("Model metadata is missing feature specifications.")
        rows: dict[str, Any] = {}
        for feature, spec in feature_specs.items():
            if feature not in payload:
                raise ValueError(f"Missing required field: {feature}")
            value = payload[feature]
            if value is None or value == "":
                raise ValueError(f"Missing required field: {feature}")
            if spec.get("type") == "numeric":
                rows[feature] = float(value)
            elif spec.get("type") == "binary":
                if isinstance(value, str):
                    lowered = value.strip().lower()
                    if lowered in {"1", "true", "yes"}:
                        rows[feature] = 1
                    elif lowered in {"0", "false", "no"}:
                        rows[feature] = 0
                    else:
                        raise ValueError(f"Invalid binary value for {feature}")
                else:
                    rows[feature] = int(value)
            else:
                rows[feature] = str(value)
        return pd.DataFrame([rows])

    def _risk_categories(self, probability: float, target: str) -> str:
        thresholds = self.metadata.get("thresholds", {})
        config = get_config()
        low_threshold = float(
            thresholds.get(f"{target}_low", config.T21_LOW_THRESHOLD if target == "t21" else config.T18_LOW_THRESHOLD)
        )
        high_threshold = float(
            thresholds.get(f"{target}_high", config.T21_HIGH_THRESHOLD if target == "t21" else config.T18_HIGH_THRESHOLD)
        )
        return _risk_category(probability, low_threshold, high_threshold)

    def _feature_names_after_preprocess(self, preprocessor: Any) -> list[str]:
        try:
            return list(preprocessor.get_feature_names_out())
        except Exception:
            return []

    def _explain(self, model: Any, preprocessor: Any, input_frame: pd.DataFrame, target_name: str) -> list[dict[str, Any]]:
        transformed = preprocessor.transform(input_frame)
        transformed_array = np.asarray(transformed)
        feature_names = self._feature_names_after_preprocess(preprocessor)
        if not feature_names:
            feature_names = self._feature_columns()
        contributions: list[dict[str, Any]] = []

        try:
            import shap  # type: ignore

            background_size = min(25, transformed_array.shape[0])
            explainer = shap.Explainer(model, transformed_array[:background_size])
            shap_values = explainer(transformed_array)
            values = np.abs(np.asarray(shap_values.values)[0])
            ranked = np.argsort(values)[::-1][:5]
            for index in ranked:
                contributions.append(
                    {
                        "feature": feature_names[index] if index < len(feature_names) else f"feature_{index}",
                        "contribution": float(values[index]),
                        "method": "shap",
                        "target": target_name,
                    }
                )
            return contributions
        except Exception:
            pass

        if hasattr(model, "coef_"):
            weights = np.abs(model.coef_[0])
            ranked = np.argsort(weights)[::-1][:5]
            for index in ranked:
                contributions.append(
                    {
                        "feature": feature_names[index] if index < len(feature_names) else f"feature_{index}",
                        "contribution": float(weights[index]),
                        "method": "coefficient",
                        "target": target_name,
                    }
                )
            return contributions

        if hasattr(model, "feature_importances_"):
            weights = np.abs(model.feature_importances_)
            ranked = np.argsort(weights)[::-1][:5]
            for index in ranked:
                contributions.append(
                    {
                        "feature": feature_names[index] if index < len(feature_names) else f"feature_{index}",
                        "contribution": float(weights[index]),
                        "method": "feature_importance",
                        "target": target_name,
                    }
                )
            return contributions

        for feature in feature_names[:5]:
            contributions.append(
                {
                    "feature": feature,
                    "contribution": 0.0,
                    "method": "unavailable",
                    "target": target_name,
                }
            )
        return contributions

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.artifact_ready():
            raise FileNotFoundError("Trained models are not available. Run python -m ml.train first.")
        input_frame = self._validate_payload(payload)

        t21_probability = float(self.t21_model.predict_proba(self.t21_preprocessor.transform(input_frame))[:, 1][0])
        t18_probability = float(self.t18_model.predict_proba(self.t18_preprocessor.transform(input_frame))[:, 1][0])

        t21_risk_level = self._risk_categories(t21_probability, "t21")
        t18_risk_level = self._risk_categories(t18_probability, "t18")

        selected_models = {
            "t21": self.metadata.get("selected_models", {}).get("t21", "unknown"),
            "t18": self.metadata.get("selected_models", {}).get("t18", "unknown"),
        }
        contributions = {
            "t21": self._explain(self.t21_model, self.t21_preprocessor, input_frame, "t21"),
            "t18": self._explain(self.t18_model, self.t18_preprocessor, input_frame, "t18"),
        }

        return {
            "t21_probability": t21_probability,
            "t21_percentage": round(t21_probability * 100.0, 2),
            "t21_risk_level": t21_risk_level,
            "t18_probability": t18_probability,
            "t18_percentage": round(t18_probability * 100.0, 2),
            "t18_risk_level": t18_risk_level,
            "selected_models": selected_models,
            "feature_contributions": contributions,
            "input_features": input_frame.to_dict(orient="records")[0],
        }


def predict_screening(payload: dict[str, Any]) -> dict[str, Any]:
    return ScreeningPredictor().predict(payload)
