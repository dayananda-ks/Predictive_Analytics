from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from backend import create_app
from backend.config import get_config
from backend.database import init_db
from ml.data_utils import create_binary_targets, feature_columns_for_training, infer_feature_specs, load_dataset
from ml.preprocess import build_preprocessor


@pytest.fixture(scope="session")
def dataset_frame() -> pd.DataFrame:
    raw_path = Path("data/raw/prenatal_screening_synthetic_dataset.csv")
    frame = load_dataset(raw_path)
    return create_binary_targets(frame, "outcome")


@pytest.fixture(scope="session")
def feature_specs(dataset_frame: pd.DataFrame):
    feature_columns = feature_columns_for_training(dataset_frame, "outcome")
    return infer_feature_specs(dataset_frame, feature_columns)


@pytest.fixture(scope="session")
def trained_artifact_dir(tmp_path_factory, dataset_frame: pd.DataFrame, feature_specs):
    artifact_dir = tmp_path_factory.mktemp("artifacts")
    feature_columns = list(feature_specs.keys())
    X = dataset_frame[feature_columns].copy()
    preprocessor = build_preprocessor(feature_specs)
    transformed = preprocessor.fit_transform(X)

    for target_name, target_column in [("t21", "t21_target"), ("t18", "t18_target")]:
        model = LogisticRegression(max_iter=1000, class_weight="balanced", solver="liblinear")
        model.fit(transformed, dataset_frame[target_column].astype(int))
        joblib.dump(model, artifact_dir / f"{target_name}_model.joblib")
        joblib.dump(preprocessor, artifact_dir / f"preprocessing_{target_name}.joblib")

    metadata = {
        "feature_specs": feature_specs,
        "selected_models": {"t21": "logistic_regression", "t18": "logistic_regression"},
        "thresholds": {
            "t21_low": 0.15,
            "t21_high": 0.35,
            "t18_low": 0.10,
            "t18_high": 0.30,
        },
        "dataset_info": {"rows": int(dataset_frame.shape[0])},
    }
    (artifact_dir / "model_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return artifact_dir


@pytest.fixture()
def app_client(tmp_path, monkeypatch, trained_artifact_dir):
    database_path = tmp_path / "history.sqlite3"
    report_path = tmp_path / "reports"
    monkeypatch.setenv("MODEL_DIR", str(trained_artifact_dir))
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    monkeypatch.setenv("REPORT_DIR", str(report_path))
    monkeypatch.setenv("RAW_DATA_DIR", str(Path("data/raw")))
    app = create_app()
    init_db(database_path)
    return app.test_client()
