from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, render_template, request, send_file

from backend.database import add_history_record, delete_history_record, list_history_records
from backend.report_generator import build_pdf_report
from backend.validation import validate_payload
from ml.predict import ScreeningPredictor


bp = Blueprint("app", __name__)


def _config() -> Any:
    return current_app.config


def _predictor() -> ScreeningPredictor:
    return ScreeningPredictor(_config()["MODEL_DIR"])


@bp.route("/")
def home() -> str:
    return render_template("index.html", title=_config()["TITLE"], disclaimer=_config()["DISCLAIMER"])


@bp.route("/screening")
def screening() -> str:
    return render_template("screening.html", title=_config()["TITLE"], disclaimer=_config()["DISCLAIMER"])


@bp.route("/results")
def results() -> str:
    return render_template("results.html", title=_config()["TITLE"], disclaimer=_config()["DISCLAIMER"])


@bp.route("/history")
def history() -> str:
    return render_template("history.html", title=_config()["TITLE"], disclaimer=_config()["DISCLAIMER"])


@bp.route("/model-performance")
def model_performance() -> str:
    return render_template("model_performance.html", title=_config()["TITLE"], disclaimer=_config()["DISCLAIMER"])


@bp.route("/about")
def about() -> str:
    return render_template("about.html", title=_config()["TITLE"], disclaimer=_config()["DISCLAIMER"])


@bp.route("/disclaimer")
def disclaimer() -> str:
    return render_template("disclaimer.html", title=_config()["TITLE"], disclaimer=_config()["DISCLAIMER"])


@bp.route("/api/health")
def health() -> Response:
    predictor = _predictor()
    return jsonify(
        {
            "status": "ok",
            "model_ready": predictor.artifact_ready(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@bp.route("/api/model-info")
def model_info() -> Response:
    predictor = _predictor()
    metadata = predictor.metadata if predictor.metadata else {}
    return jsonify(
        {
            "title": _config()["TITLE"],
            "disclaimer": _config()["DISCLAIMER"],
            "feature_specs": metadata.get("feature_specs", {}),
            "selected_models": metadata.get("selected_models", {}),
            "thresholds": metadata.get("thresholds", {}),
            "dataset_info": metadata.get("dataset_info", {}),
            "model_ready": predictor.artifact_ready(),
        }
    )


@bp.route("/api/metrics")
def metrics() -> Response:
    metrics_path = Path(_config()["REPORT_DIR"]) / "model_metrics" / "results.json"
    if not metrics_path.exists():
        return jsonify({"message": "Models have not been trained yet."}), 503
    return jsonify(json.loads(metrics_path.read_text(encoding="utf-8")))


@bp.route("/api/predict", methods=["POST"])
def predict() -> Response:
    payload = request.get_json(silent=True) or {}
    predictor = _predictor()
    if not predictor.metadata.get("feature_specs"):
        return jsonify({"error": "Models have not been trained yet."}), 503

    try:
        cleaned = validate_payload(payload, predictor.metadata["feature_specs"])
        result = predictor.predict(cleaned)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    history_id = add_history_record(
        _config()["DATABASE_PATH"],
        {
            "input_data": cleaned,
            "t21_probability": result["t21_probability"],
            "t21_risk_level": result["t21_risk_level"],
            "t18_probability": result["t18_probability"],
            "t18_risk_level": result["t18_risk_level"],
            "model_name": json.dumps(result["selected_models"], ensure_ascii=True),
        },
    )
    result["history_id"] = history_id
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return jsonify(result)


@bp.route("/api/history", methods=["GET", "POST"])
def history_api() -> Response:
    database_path = _config()["DATABASE_PATH"]
    if request.method == "GET":
        return jsonify({"records": list_history_records(database_path)})

    payload = request.get_json(silent=True) or {}
    try:
        record_id = add_history_record(database_path, payload)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": record_id}), 201


@bp.route("/api/history/<int:record_id>", methods=["DELETE"])
def delete_history(record_id: int) -> Response:
    deleted = delete_history_record(_config()["DATABASE_PATH"], record_id)
    if not deleted:
        return jsonify({"error": "Record not found."}), 404
    return jsonify({"status": "deleted", "id": record_id})


@bp.route("/api/report", methods=["POST"])
def report() -> Response:
    payload = request.get_json(silent=True) or {}
    try:
        predictor = _predictor()
        cleaned = validate_payload(payload, predictor.metadata["feature_specs"])
        result = predictor.predict(cleaned)
        report_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_data": cleaned,
            "t21_percentage": result["t21_percentage"],
            "t21_risk_level": result["t21_risk_level"],
            "t18_percentage": result["t18_percentage"],
            "t18_risk_level": result["t18_risk_level"],
            "selected_model": json.dumps(result["selected_models"], ensure_ascii=True),
            "feature_contributions": result["feature_contributions"],
        }
        pdf = build_pdf_report(report_payload, _config()["TITLE"], _config()["DISCLAIMER"])
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="prenatal_screening_report.pdf",
    )
