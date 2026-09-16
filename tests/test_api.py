from __future__ import annotations

import pandas as pd


def _payload(feature_specs):
    payload = {}
    for feature, spec in feature_specs.items():
        if spec["type"] == "numeric":
            payload[feature] = spec["median"]
        elif spec["type"] == "binary":
            payload[feature] = 0
        else:
            payload[feature] = spec["options"][0]
    return payload


def test_api_health(app_client):
    response = app_client.get("/api/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"


def test_api_prediction(app_client, feature_specs):
    response = app_client.post("/api/predict", json=_payload(feature_specs))
    assert response.status_code == 200
    body = response.get_json()
    assert "t21_probability" in body
    assert "t18_probability" in body


def test_api_history_cycle(app_client, feature_specs):
    response = app_client.post("/api/predict", json=_payload(feature_specs))
    assert response.status_code == 200
    history = app_client.get("/api/history")
    assert history.status_code == 200
    records = history.get_json()["records"]
    assert records
    delete_response = app_client.delete(f"/api/history/{records[0]['id']}")
    assert delete_response.status_code == 200

