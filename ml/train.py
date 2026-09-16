from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GroupShuffleSplit, StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from xgboost import XGBClassifier

from backend.config import get_config
from ml.data_utils import (
    create_binary_targets,
    discover_csv_files,
    feature_columns_for_training,
    infer_feature_specs,
    load_dataset,
    select_primary_dataset,
    summarize_dataset,
    write_json,
)
from ml.preprocess import build_preprocessor, prepare_feature_frame


TARGETS = {"t21": "t21_target", "t18": "t18_target"}


@dataclass
class ModelArtifact:
    name: str
    estimator: Any
    params: dict[str, Any]


def _safe_metric(fn, *args, default=np.nan, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return default


def _classification_metrics(y_true: pd.Series, y_pred: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    metrics = {
        "accuracy": float(_safe_metric(accuracy_score, y_true, y_pred)),
        "precision": float(_safe_metric(precision_score, y_true, y_pred, zero_division=0)),
        "recall": float(_safe_metric(recall_score, y_true, y_pred, zero_division=0)),
        "f1": float(_safe_metric(f1_score, y_true, y_pred, zero_division=0)),
        "balanced_accuracy": float(_safe_metric(balanced_accuracy_score, y_true, y_pred)),
        "roc_auc": float(_safe_metric(roc_auc_score, y_true, y_prob)),
        "pr_auc": float(_safe_metric(average_precision_score, y_true, y_prob)),
    }
    return metrics


def _plot_confusion_matrix(cm: np.ndarray, output_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_title(title)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    for (i, j), value in np.ndenumerate(cm):
        ax.text(j, i, int(value), ha="center", va="center", color="black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _plot_curve(x_values: np.ndarray, y_values: np.ndarray, output_path: Path, title: str, x_label: str, y_label: str) -> None:
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(x_values, y_values, linewidth=2)
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _plot_model_comparison(target_name: str, results: dict[str, dict[str, Any]], output_path: Path) -> None:
    labels = list(results.keys())
    balanced_accuracy = [results[name]["test_metrics"]["balanced_accuracy"] for name in labels]
    pr_auc = [results[name]["test_metrics"]["pr_auc"] for name in labels]

    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - width / 2, balanced_accuracy, width, label="Balanced Accuracy")
    ax.bar(x + width / 2, pr_auc, width, label="PR-AUC")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20)
    ax.set_ylim(0, 1.05)
    ax.set_title(f"{target_name.upper()} model comparison")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


def _plot_feature_importance(feature_names: list[str], importance_values: np.ndarray, output_path: Path, title: str) -> list[dict[str, Any]]:
    ranked = np.argsort(importance_values)[::-1][:10]
    top_features = [
        {"feature": feature_names[index], "importance": float(importance_values[index])}
        for index in ranked
    ]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh([feature_names[index] for index in ranked][::-1], importance_values[ranked][::-1])
    ax.set_title(title)
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return top_features


def _create_models(target: str, positive_count: int, negative_count: int) -> dict[str, ModelArtifact]:
    scale_pos_weight = max(1.0, negative_count / max(1, positive_count))
    return {
        "logistic_regression": ModelArtifact(
            name="logistic_regression",
            estimator=LogisticRegression(max_iter=2000, class_weight="balanced", solver="liblinear"),
            params={},
        ),
        "random_forest": ModelArtifact(
            name="random_forest",
            estimator=RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                class_weight="balanced_subsample",
                min_samples_leaf=2,
            ),
            params={},
        ),
        "svm": ModelArtifact(
            name="svm",
            estimator=SVC(kernel="rbf", probability=True, class_weight="balanced", random_state=42),
            params={},
        ),
        "xgboost": ModelArtifact(
            name="xgboost",
            estimator=XGBClassifier(
                n_estimators=250,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                objective="binary:logistic",
                eval_metric="logloss",
                random_state=42,
                scale_pos_weight=scale_pos_weight,
                tree_method="hist",
            ),
            params={},
        ),
    }


def _model_selection_score(cv_results: dict[str, Any]) -> float:
    balanced_accuracy = float(np.nanmean(cv_results["test_balanced_accuracy"]))
    pr_auc = float(np.nanmean(cv_results["test_average_precision"]))
    roc_auc = float(np.nanmean(cv_results["test_roc_auc"]))
    return balanced_accuracy * 0.5 + pr_auc * 0.3 + roc_auc * 0.2


def _fit_and_evaluate_model(
    model_name: str,
    model: Any,
    preprocessor,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> dict[str, Any]:
    pipeline = Pipeline(
        steps=[("preprocessor", preprocessor), ("classifier", model)]
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        pipeline,
        X_train,
        y_train,
        cv=cv,
        scoring={
            "accuracy": "accuracy",
            "balanced_accuracy": "balanced_accuracy",
            "average_precision": "average_precision",
            "roc_auc": "roc_auc",
        },
        n_jobs=None,
        return_train_score=False,
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    metrics = _classification_metrics(y_test, y_pred, y_prob)
    cm = confusion_matrix(y_test, y_pred)
    return {
        "pipeline": pipeline,
        "cv_results": cv_results,
        "cv_score": _model_selection_score(cv_results),
        "test_metrics": metrics,
        "confusion_matrix": cm,
        "y_pred": y_pred,
        "y_prob": y_prob,
        "classification_report": classification_report(y_test, y_pred, zero_division=0, output_dict=True),
    }


def _best_model(results: dict[str, dict[str, Any]]) -> str:
    ranked = sorted(
        results.items(),
        key=lambda item: (
            item[1]["cv_score"],
            item[1]["test_metrics"]["balanced_accuracy"],
            item[1]["test_metrics"]["pr_auc"],
        ),
        reverse=True,
    )
    return ranked[0][0]


def _format_results_summary(results: dict[str, dict[str, Any]], selected_model: str) -> dict[str, Any]:
    return {
        name: {
            "cv_score": float(result["cv_score"]),
            "cv_metrics": {
                "accuracy": float(np.nanmean(result["cv_results"]["test_accuracy"])),
                "balanced_accuracy": float(np.nanmean(result["cv_results"]["test_balanced_accuracy"])),
                "pr_auc": float(np.nanmean(result["cv_results"]["test_average_precision"])),
                "roc_auc": float(np.nanmean(result["cv_results"]["test_roc_auc"])),
            },
            "test_metrics": {key: float(value) for key, value in result["test_metrics"].items()},
        }
        for name, result in results.items()
    } | {"selected_model": selected_model}


def _save_artifacts(
    target_name: str,
    selected_model_name: str,
    selected_model_pipeline,
    preprocessor,
    selected_result: dict[str, Any],
    feature_specs: dict[str, dict[str, Any]],
    dataset_info: dict[str, Any],
    output_root: Path,
    all_results: dict[str, dict[str, Any]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    models_dir = output_root / "models"
    reports_dir = output_root / "reports" / "model_metrics"
    figures_dir = output_root / "reports" / "figures"
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    classifier = selected_model_pipeline.named_steps["classifier"]
    joblib.dump(classifier, models_dir / f"{target_name}_model.joblib")
    joblib.dump(preprocessor, models_dir / f"preprocessing_{target_name}.joblib")

    X_test_transformed = selected_model_pipeline.named_steps["preprocessor"].transform(selected_result["X_test"])
    feature_names = list(selected_model_pipeline.named_steps["preprocessor"].get_feature_names_out())

    if hasattr(classifier, "coef_"):
        importance_values = np.abs(classifier.coef_[0])
    elif hasattr(classifier, "feature_importances_"):
        importance_values = np.abs(classifier.feature_importances_)
    else:
        importance = permutation_importance(
            selected_model_pipeline,
            selected_result["X_test"],
            selected_result["y_test"],
            n_repeats=5,
            random_state=42,
            scoring="average_precision",
        )
        importance_values = importance.importances_mean

    selected_feature_importance = _plot_feature_importance(
        feature_names,
        importance_values,
        figures_dir / f"{target_name}_feature_importance.png",
        f"{target_name.upper()} feature importance",
    )

    fpr, tpr, _ = roc_curve(selected_result["y_test"], selected_result["y_prob"])
    precision, recall, _ = precision_recall_curve(selected_result["y_test"], selected_result["y_prob"])
    _plot_curve(fpr, tpr, figures_dir / f"{target_name}_roc_curve.png", f"{target_name.upper()} ROC curve", "False positive rate", "True positive rate")
    _plot_curve(recall, precision, figures_dir / f"{target_name}_pr_curve.png", f"{target_name.upper()} precision-recall curve", "Recall", "Precision")
    _plot_confusion_matrix(selected_result["confusion_matrix"], figures_dir / f"{target_name}_confusion_matrix.png", f"{target_name.upper()} confusion matrix")
    _plot_model_comparison(target_name, all_results, figures_dir / f"{target_name}_model_comparison.png")

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": target_name,
        "selected_models": {target_name: selected_model_name},
        "selection_criterion": "Highest composite validation score using mean cross-validated balanced accuracy, PR-AUC, and ROC-AUC; tie-breakers favor balanced accuracy then PR-AUC.",
        "feature_specs": feature_specs,
        "feature_columns": list(feature_specs.keys()),
        "selected_feature_importance": selected_feature_importance,
        "thresholds": thresholds,
        "dataset_info": dataset_info,
        "model_results": _format_results_summary(all_results, selected_model_name),
    }

    return metadata


def _write_research_report(output_root: Path, combined_payload: dict[str, Any]) -> None:
    paper_dir = output_root / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Experiment Results",
        "",
        f"Generated at: {combined_payload['generated_at']}",
        "",
        "## Dataset",
        f"Number of records: {combined_payload['dataset_info']['rows']}",
        f"Features: {', '.join(combined_payload['dataset_info']['feature_columns'])}",
        f"Class distribution: {json.dumps(combined_payload['dataset_info']['class_distribution'], ensure_ascii=True)}",
        f"Missing values: {json.dumps(combined_payload['dataset_info']['missing_values'], ensure_ascii=True)}", 
        "",
        "## Training",
        f"Train size: {combined_payload['train_size']}",
        f"Test size: {combined_payload['test_size']}",
        f"Models: {', '.join(combined_payload['model_names'])}",
        "",
        "## Results",
    ]
    for target_name, target_payload in combined_payload["targets"].items():
        lines.extend([
            f"### {target_name.upper()}",
            f"Selected model: {target_payload['selected_model']}",
            f"Actual metrics: {json.dumps(target_payload['selected_metrics'], ensure_ascii=True)}",
            "",
        ])
    lines.extend([
        "Performance on the synthetic research-prototype dataset.",
        "",
        "This application is an academic research prototype for prenatal screening risk estimation. It is not a medical diagnostic tool and must not be used independently for clinical decision-making.",
    ])
    (paper_dir / "experiment_results.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    config = get_config()
    output_root = Path(".").resolve()
    raw_dir = Path(config.RAW_DATA_DIR)
    report_data_dir = Path(config.REPORT_DIR) / "data"
    report_data_dir.mkdir(parents=True, exist_ok=True)

    csv_files = discover_csv_files(raw_dir)
    if not csv_files:
        raise FileNotFoundError(f"No CSV files were found in {raw_dir}")

    summaries = []
    dataset_frames: dict[str, pd.DataFrame] = {}
    for csv_path in csv_files:
        frame = load_dataset(csv_path)
        dataset_frames[csv_path.name] = frame
        summaries.append(summarize_dataset(csv_path, frame))

    primary_dataset_name = select_primary_dataset(summaries)
    if primary_dataset_name is None:
        raise ValueError("No compatible dataset was found for the primary T21/T18 model.")

    primary_frame = dataset_frames[primary_dataset_name]
    prepared = create_binary_targets(primary_frame, "outcome")
    feature_columns = feature_columns_for_training(prepared, "outcome")
    feature_specs = infer_feature_specs(prepared, feature_columns)
    X = prepare_feature_frame(prepared, feature_columns)

    if "patient_id" in prepared.columns:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        groups = prepared["patient_id"].astype(str)
        train_indices, test_indices = next(splitter.split(X, prepared["t21_target"], groups=groups))
    else:
        train_indices, test_indices = train_test_split(
            np.arange(len(prepared)),
            test_size=0.2,
            random_state=42,
            stratify=prepared["t21_target"],
        )

    X_train = X.iloc[train_indices].reset_index(drop=True)
    X_test = X.iloc[test_indices].reset_index(drop=True)

    dataset_info = {
        "filename": primary_dataset_name,
        "rows": int(prepared.shape[0]),
        "columns": int(prepared.shape[1]),
        "feature_columns": feature_columns,
        "class_distribution": {
            "T21": int(prepared["t21_target"].sum()),
            "T18": int(prepared["t18_target"].sum()),
            "Unaffected": int((prepared["outcome"] == "Unaffected").sum()),
        },
        "missing_values": {column: int(value) for column, value in prepared.isna().sum().items()},
    }

    combined_results: dict[str, Any] = {}
    model_names: list[str] = []
    final_metadata: dict[str, Any] = {}

    for target_name, target_column in TARGETS.items():
        y = prepared[target_column].astype(int)
        y_train = y.iloc[train_indices].reset_index(drop=True)
        y_test = y.iloc[test_indices].reset_index(drop=True)
        model_names = ["logistic_regression", "random_forest", "svm", "xgboost"]
        positive_count = int(y_train.sum())
        negative_count = int(len(y_train) - y_train.sum())
        model_specs = _create_models(target_name, positive_count, negative_count)
        results: dict[str, dict[str, Any]] = {}
        for model_name, artifact in model_specs.items():
            preprocessor = build_preprocessor(feature_specs)
            results[model_name] = _fit_and_evaluate_model(
                model_name,
                artifact.estimator,
                preprocessor,
                X_train,
                y_train,
                X_test,
                y_test,
            )

        selected_model_name = _best_model(results)
        selected_result = results[selected_model_name]
        selected_pipeline = selected_result["pipeline"]
        selected_preprocessor = selected_pipeline.named_steps["preprocessor"]

        thresholds = {
            f"{target_name}_low": getattr(config, f"{target_name.upper()}_LOW_THRESHOLD"),
            f"{target_name}_high": getattr(config, f"{target_name.upper()}_HIGH_THRESHOLD"),
        }

        metadata = _save_artifacts(
            target_name=target_name,
            selected_model_name=selected_model_name,
            selected_model_pipeline=selected_pipeline,
            preprocessor=selected_preprocessor,
            selected_result={**selected_result, "X_test": X_test, "y_test": y_test},
            feature_specs=feature_specs,
            dataset_info=dataset_info,
            output_root=output_root,
            all_results=results,
            thresholds=thresholds,
        )
        if not final_metadata:
            final_metadata = metadata
        else:
            final_metadata["selected_models"].update(metadata["selected_models"])
            final_metadata["model_results"].update(metadata["model_results"])

        combined_results[target_name] = {
            "selected_model": selected_model_name,
            "selected_metrics": {key: float(value) for key, value in selected_result["test_metrics"].items()},
            "metrics_by_model": {
                model_name: {key: float(value) for key, value in result["test_metrics"].items()}
                for model_name, result in results.items()
            },
            "confusion_matrix": selected_result["confusion_matrix"].tolist(),
        }

    final_metadata["generated_at"] = datetime.now(timezone.utc).isoformat()
    final_metadata["selected_models"] = {
        "t21": combined_results["t21"]["selected_model"],
        "t18": combined_results["t18"]["selected_model"],
    }
    final_metadata["model_results"] = {
        "t21": combined_results["t21"],
        "t18": combined_results["t18"],
    }
    final_metadata["feature_columns"] = feature_columns
    final_metadata["feature_specs"] = feature_specs
    final_metadata["dataset_info"] = dataset_info
    final_metadata["thresholds"] = {
        "t21_low": config.T21_LOW_THRESHOLD,
        "t21_high": config.T21_HIGH_THRESHOLD,
        "t18_low": config.T18_LOW_THRESHOLD,
        "t18_high": config.T18_HIGH_THRESHOLD,
    }
    final_metadata["selection_criterion"] = "Highest composite validation score using mean cross-validated balanced accuracy, PR-AUC, and ROC-AUC; tie-breakers favor balanced accuracy then PR-AUC."

    models_dir = Path(config.MODEL_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)
    write_json(models_dir / "model_metadata.json", final_metadata)

    metrics_payload = {
        "generated_at": final_metadata["generated_at"],
        "dataset": dataset_info,
        "targets": combined_results,
        "selected_models": final_metadata["selected_models"],
        "feature_columns": feature_columns,
        "feature_specs": feature_specs,
        "thresholds": final_metadata["thresholds"],
        "selection_criterion": final_metadata["selection_criterion"],
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "model_names": model_names,
    }
    write_json(Path(config.REPORT_DIR) / "model_metrics" / "results.json", metrics_payload)

    inspection_path = report_data_dir / "dataset_inspection.json"
    if not inspection_path.exists():
        write_json(
            inspection_path,
            {
                "generated_at": final_metadata["generated_at"],
                "datasets": [
                    {
                        "filename": summary.filename,
                        "rows": summary.rows,
                        "columns": summary.columns,
                        "column_names": summary.column_names,
                        "missing_values": summary.missing_values,
                        "duplicate_rows": summary.duplicate_rows,
                        "class_distribution": summary.class_distribution,
                        "target_candidates": summary.target_candidates,
                    }
                    for summary in summaries
                ],
                "primary_dataset": primary_dataset_name,
            },
        )

    _write_research_report(
        output_root,
        {
            "generated_at": final_metadata["generated_at"],
            "dataset_info": dataset_info,
            "train_size": int(len(X_train)),
            "test_size": int(len(X_test)),
            "model_names": model_names,
            "targets": combined_results,
        },
    )

    print(json.dumps(metrics_payload, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
