from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from backend.config import get_config
from ml.data_utils import (
    dataset_summary_to_dict,
    discover_csv_files,
    load_dataset,
    select_primary_dataset,
    summarize_dataset,
    write_json,
)


def main() -> None:
    config = get_config()
    raw_dir = Path(config.RAW_DATA_DIR)
    report_dir = Path(config.REPORT_DIR) / "data"
    report_dir.mkdir(parents=True, exist_ok=True)

    datasets = discover_csv_files(raw_dir)
    summaries = []
    detailed_reports = []
    for path in datasets:
        df = load_dataset(path)
        summary = summarize_dataset(path, df)
        summaries.append(summary)
        detailed_reports.append(dataset_summary_to_dict(summary))

    report_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "datasets": detailed_reports,
        "primary_dataset": select_primary_dataset(summaries),
    }
    write_json(report_dir / "dataset_inspection.json", report_payload)

    markdown_lines = ["# Dataset Inspection Report", ""]
    markdown_lines.append(f"Generated at: {report_payload['generated_at']}")
    markdown_lines.append("")
    for item in detailed_reports:
        markdown_lines.extend(
            [
                f"## {item['filename']}",
                f"Rows: {item['rows']}",
                f"Columns: {item['columns']}",
                f"Duplicate rows: {item['duplicate_rows']}",
                f"Target candidates: {', '.join(item['target_candidates']) if item['target_candidates'] else 'none'}",
                "",
            ]
        )
    (report_dir / "dataset_inspection.md").write_text("\n".join(markdown_lines), encoding="utf-8")

    metadata_path = Path("data/dataset_metadata.json")
    metadata = {
        "datasets": [
            {
                "filename": item["filename"],
                "source": item.get("source", "unknown"),
                "license": item.get("license", "unknown"),
                "citation": item.get("citation", "unknown"),
                "synthetic": item.get("synthetic", False),
            }
            for item in detailed_reports
        ],
        "synthetic_data": True,
        "notes": "Synthetic research prototype dataset. Not real patient data.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report_payload, indent=2))


if __name__ == "__main__":
    main()
