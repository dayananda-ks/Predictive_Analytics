from __future__ import annotations

from typing import Any


def validate_payload(payload: dict[str, Any], feature_specs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    cleaned: dict[str, Any] = {}
    for feature, spec in feature_specs.items():
        if feature not in payload:
            raise ValueError(f"Missing required field: {feature}")

        value = payload[feature]
        if value in {None, ""}:
            raise ValueError(f"Missing required field: {feature}")

        feature_type = spec.get("type")
        if feature_type == "numeric":
            try:
                numeric_value = float(value)
            except Exception as exc:
                raise ValueError(f"Invalid numeric value for {feature}") from exc
            minimum = spec.get("minimum")
            maximum = spec.get("maximum")
            if minimum is not None and numeric_value < float(minimum):
                raise ValueError(f"{feature} is below the allowed range.")
            if maximum is not None and numeric_value > float(maximum):
                raise ValueError(f"{feature} is above the allowed range.")
            cleaned[feature] = numeric_value
        elif feature_type == "binary":
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"1", "true", "yes"}:
                    cleaned[feature] = 1
                elif lowered in {"0", "false", "no"}:
                    cleaned[feature] = 0
                else:
                    allowed = spec.get("options", [0, 1])
                    if value in allowed:
                        cleaned[feature] = value
                    else:
                        raise ValueError(f"Invalid binary value for {feature}")
            else:
                if int(value) not in {0, 1}:
                    raise ValueError(f"Invalid binary value for {feature}")
                cleaned[feature] = int(value)
        else:
            allowed = [str(option) for option in spec.get("options", [])]
            text = str(value)
            if allowed and text not in allowed:
                raise ValueError(f"Invalid category for {feature}")
            cleaned[feature] = text

    return cleaned
