from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.database import add_history_record, delete_history_record, list_history_records
from backend.validation import validate_payload
from ml.data_utils import create_binary_targets, discover_csv_files, load_dataset
from ml.predict import ScreeningPredictor
from ml.preprocess import build_preprocessor


def test_data_loading_and_discovery():
    files = discover_csv_files(Path("data/raw"))
    assert files, "Expected at least one CSV file in data/raw"
    frame = load_dataset(files[0])
    assert not frame.empty
    assert "outcome" in frame.columns


def test_target_generation(dataset_frame: pd.DataFrame):
    assert "t21_target" in dataset_frame.columns
    assert "t18_target" in dataset_frame.columns
    assert set(dataset_frame["t21_target"].unique()).issubset({0, 1})
    assert set(dataset_frame["t18_target"].unique()).issubset({0, 1})


def test_preprocessing_pipeline(feature_specs, dataset_frame: pd.DataFrame):
    feature_columns = list(feature_specs.keys())
    preprocessor = build_preprocessor(feature_specs)
    transformed = preprocessor.fit_transform(dataset_frame[feature_columns].copy())
    assert transformed.shape[0] == len(dataset_frame)


def test_validation(feature_specs):
    payload = {}
    for feature, spec in feature_specs.items():
        if spec["type"] == "numeric":
            payload[feature] = spec["median"]
        elif spec["type"] == "binary":
            payload[feature] = 0
        else:
            payload[feature] = spec["options"][0]
    cleaned = validate_payload(payload, feature_specs)
    assert cleaned.keys() == payload.keys()


def test_prediction_service(trained_artifact_dir, feature_specs):
    predictor = ScreeningPredictor(trained_artifact_dir)
    payload = {}
    for feature, spec in feature_specs.items():
        if spec["type"] == "numeric":
            payload[feature] = spec["median"]
        elif spec["type"] == "binary":
            payload[feature] = 0
        else:
            payload[feature] = spec["options"][0]
    result = predictor.predict(payload)
    assert 0.0 <= result["t21_probability"] <= 1.0
    assert 0.0 <= result["t18_probability"] <= 1.0
    assert result["feature_contributions"]


def test_database_history(tmp_path):
    database_path = tmp_path / "history.sqlite3"
    from backend.database import init_db

    init_db(database_path)
    record_id = add_history_record(
        database_path,
        {
            "input_data": {"maternal_age": 30},
            "t21_probability": 0.1,
            "t21_risk_level": "Prototype Low Screening Risk",
            "t18_probability": 0.05,
            "t18_risk_level": "Prototype Low Screening Risk",
            "model_name": "logistic_regression",
        },
    )
    records = list_history_records(database_path)
    assert records and records[0]["id"] == record_id
    assert delete_history_record(database_path, record_id) is True

