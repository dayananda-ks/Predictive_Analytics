from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


EXPECTED_OUTCOME_VALUES = {"Unaffected", "Trisomy21", "Trisomy18"}
ID_COLUMNS = {"patient_id"}
TARGET_COLUMN_CANDIDATES = {"outcome", "target", "label", "class"}


@dataclass
class DatasetSummary:
    filename: str
    rows: int
    columns: int
    column_names: list[str]
    dtypes: dict[str, str]
    missing_values: dict[str, int]
    duplicate_rows: int
    class_distribution: dict[str, int]
    target_candidates: list[str]
    source: str = "unknown"
    license: str = "unknown"
    citation: str = "unknown"
    synthetic: bool = False
    compatible_for_primary_model: bool = False
    notes: str = ""


def discover_csv_files(raw_dir: Path) -> list[Path]:
    return sorted(raw_dir.glob("*.csv"))


def load_dataset(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def infer_target_candidates(df: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for column in df.columns:
        if column.lower() in TARGET_COLUMN_CANDIDATES:
            candidates.append(column)
            continue
        if df[column].dtype == object and df[column].nunique(dropna=True) <= 10:
            candidates.append(column)
    return candidates


def summarize_dataset(path: Path, df: pd.DataFrame) -> DatasetSummary:
    target_candidates = infer_target_candidates(df)
    outcome_counts: dict[str, int] = {}
    if "outcome" in df.columns:
        outcome_counts = df["outcome"].value_counts(dropna=False).to_dict()
    elif target_candidates:
        first_target = target_candidates[0]
        outcome_counts = df[first_target].value_counts(dropna=False).to_dict()

    compatible = "outcome" in df.columns and EXPECTED_OUTCOME_VALUES.issubset(
        set(df["outcome"].dropna().astype(str).unique())
    )

    return DatasetSummary(
        filename=path.name,
        rows=int(df.shape[0]),
        columns=int(df.shape[1]),
        column_names=list(df.columns),
        dtypes={column: str(dtype) for column, dtype in df.dtypes.items()},
        missing_values={column: int(count) for column, count in df.isna().sum().items()},
        duplicate_rows=int(df.duplicated().sum()),
        class_distribution={str(key): int(value) for key, value in outcome_counts.items()},
        target_candidates=target_candidates,
        synthetic=True,
        compatible_for_primary_model=compatible,
        notes="Synthetic dataset detected from local workspace." if compatible else "",
    )


def dataset_summary_to_dict(summary: DatasetSummary) -> dict[str, Any]:
    return {
        "filename": summary.filename,
        "rows": summary.rows,
        "columns": summary.columns,
        "column_names": summary.column_names,
        "dtypes": summary.dtypes,
        "missing_values": summary.missing_values,
        "duplicate_rows": summary.duplicate_rows,
        "class_distribution": summary.class_distribution,
        "target_candidates": summary.target_candidates,
        "source": summary.source,
        "license": summary.license,
        "citation": summary.citation,
        "synthetic": summary.synthetic,
        "compatible_for_primary_model": summary.compatible_for_primary_model,
        "notes": summary.notes,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def create_binary_targets(df: pd.DataFrame, target_column: str = "outcome") -> pd.DataFrame:
    required_values = {"Unaffected", "Trisomy21", "Trisomy18"}
    if target_column not in df.columns:
        raise ValueError(f"Missing target column: {target_column}")
    observed = set(df[target_column].dropna().astype(str).unique())
    if not required_values.issubset(observed):
        raise ValueError(
            f"Target column {target_column} does not contain expected values: {sorted(required_values)}"
        )
    result = df.copy()
    result["t21_target"] = result[target_column].map(
        {"Trisomy21": 1, "Unaffected": 0, "Trisomy18": 0}
    )
    result["t18_target"] = result[target_column].map(
        {"Trisomy18": 1, "Unaffected": 0, "Trisomy21": 0}
    )
    return result


def select_primary_dataset(summaries: list[DatasetSummary]) -> str | None:
    for summary in summaries:
        if summary.compatible_for_primary_model:
            return summary.filename
    return None


def infer_feature_specs(df: pd.DataFrame, feature_columns: list[str]) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for column in feature_columns:
        series = df[column]
        non_null = series.dropna()
        if non_null.empty:
            specs[column] = {"type": "unknown", "required": False}
            continue

        if pd.api.types.is_numeric_dtype(series):
            unique_values = set(non_null.unique().tolist())
            if unique_values.issubset({0, 1, 0.0, 1.0}):
                specs[column] = {
                    "type": "binary",
                    "required": True,
                    "options": [0, 1],
                    "minimum": 0,
                    "maximum": 1,
                }
            else:
                specs[column] = {
                    "type": "numeric",
                    "required": True,
                    "minimum": float(non_null.min()),
                    "maximum": float(non_null.max()),
                    "mean": float(non_null.mean()),
                    "median": float(non_null.median()),
                }
        else:
            unique_values = sorted({str(value) for value in non_null.unique().tolist()})
            if set(unique_values).issubset({"0", "1", "True", "False", "Yes", "No"}):
                specs[column] = {
                    "type": "binary",
                    "required": True,
                    "options": unique_values,
                }
            else:
                specs[column] = {
                    "type": "categorical",
                    "required": True,
                    "options": unique_values,
                }
    return specs


def feature_columns_for_training(df: pd.DataFrame, target_column: str = "outcome") -> list[str]:
    excluded = ID_COLUMNS | {target_column, "t21_target", "t18_target"}
    return [column for column in df.columns if column not in excluded]
