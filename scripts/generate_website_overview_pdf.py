from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "reports"
OUTPUT_FILE = REPORTS_DIR / "complete_project_flow.pdf"
DATASET_METADATA = ROOT / "data" / "dataset_metadata.json"
MODEL_METRICS = ROOT / "reports" / "model_metrics" / "results.json"
README = ROOT / "README.md"
SYSTEM = ROOT / "docs" / "SYSTEM.md"
MODEL = ROOT / "docs" / "MODEL.md"
DATASET = ROOT / "docs" / "DATASET.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def percent(value: float) -> str:
    return f"{value * 100:.2f}%" if value <= 1 else f"{value:.2f}%"


def make_bullet(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"&bull; {text}", style)


def title_block(story: list[Any], styles: dict[str, ParagraphStyle]) -> None:
    story.append(Paragraph("Prenatal AI Screening", styles["Title"]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph("Complete project flow, technology stack, training data, metrics, and run guide", styles["SubTitle"]))
    story.append(Spacer(1, 0.18 * inch))
    story.append(
        Paragraph(
            "This document summarizes the full project flow from training data to user login, screening, result generation, history storage, reporting, model quality, and local execution.",
            styles["BodyText"],
        )
    )


def section_heading(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(text, styles["Heading2"])


def table_from_rows(rows: list[list[str]], col_widths: list[float]) -> Table:
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2742")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_pdf() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = load_json(DATASET_METADATA)
    metrics = load_json(MODEL_METRICS)

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="SubTitle",
            parent=styles["BodyText"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionBody",
            parent=styles["BodyText"],
            fontSize=10,
            leading=13,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallBody",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CenteredTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
        )
    )

    story: list[Any] = []
    title_block(story, styles)
    story.append(Spacer(1, 0.18 * inch))

    story.append(section_heading("1. End-to-end project flow", styles))
    story.append(
        Paragraph(
            "The application flow is designed as a small product loop: a user creates an account, signs in, lands on a dashboard, starts a screening, submits the required health features, receives model-estimated risk percentages, and sees the result saved to their personal history. Admin users can also manage the wider site view.",
            styles["SectionBody"],
        )
    )
    story.append(
        Table(
            [
                ["Stage", "Flow", "Outcome"],
                ["1", "Login / signup", "Account access and user identity are established."],
                ["2", "Dashboard", "Shows recent activity and a single action to start a screening."],
                ["3", "Screening form", "Collects only the model features required by the trained pipeline."],
                ["4", "Validation + prediction", "The backend validates inputs, preprocesses them, and runs the trained models."],
                ["5", "Results", "Outputs T21 and T18 chance percentages, categories, and charts."],
                ["6", "History + profile", "Stores the record under the user account and allows logout / rename."],
            ],
            colWidths=[0.5 * inch, 2.4 * inch, 3.6 * inch],
        )
    )
    story[-1].setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2742")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story.append(Spacer(1, 0.15 * inch))
    story.append(section_heading("2. Technologies used", styles))
    technology_rows = [
        ["Area", "Technology"],
        ["Frontend", "Bootstrap 5, Chart.js, HTML templates, custom CSS, vanilla JavaScript"],
        ["Backend", "Flask, Flask-Login, Flask-WTF, Flask-CORS"],
        ["ML pipeline", "pandas, scikit-learn, xgboost, joblib"],
        ["Reporting", "ReportLab PDF generation"],
        ["Storage", "SQLite for users and screening history"],
        ["Deployment", "Gunicorn / Render-compatible Flask app"],
    ]
    story.append(table_from_rows(technology_rows, [1.3 * inch, 5.2 * inch]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(section_heading("3. Methods used", styles))
    method_points = [
        "Separate binary classifiers are trained for T21 and T18.",
        "A preprocessing pipeline handles missing data, scaling, and encoding.",
        "Model selection is based on a composite score using balanced accuracy, PR-AUC, and ROC-AUC.",
        "Prediction output is converted into percentage risk plus a prototype risk label.",
        "Screening history is stored per authenticated user for audit and review.",
    ]
    for point in method_points:
        story.append(make_bullet(point, styles["SectionBody"]))

    story.append(Spacer(1, 0.1 * inch))
    story.append(section_heading("4. Training data", styles))
    dataset = metrics["dataset"]
    synthetic_note = "Synthetic research prototype dataset. Not real patient data." if data.get("synthetic_data") else "Real dataset"
    story.append(
        Paragraph(
            f"The project uses the synthetic CSV dataset in data/raw/prenatal_screening_synthetic_dataset.csv. It contains {dataset['rows']} rows and {dataset['columns']} columns, with {len(dataset['feature_columns'])} model features. {synthetic_note}",
            styles["SectionBody"],
        )
    )
    story.append(
        Paragraph(
            "Class distribution: T21 = 130, T18 = 45, Unaffected = 4,825. The dataset is heavily imbalanced, so balanced accuracy and PR-AUC matter more than raw accuracy.",
            styles["SectionBody"],
        )
    )
    story.append(
        Paragraph(
            "Training flow: CSV discovery -> dataset inspection -> feature engineering -> target creation -> model training -> validation scoring -> artifact export to models/ and reports/.",
            styles["SectionBody"],
        )
    )
    feature_rows = [["Feature", "Type", "Range / values"]]
    specs = metrics["feature_specs"]
    for feature, spec in specs.items():
        if spec["type"] == "numeric":
            detail = f"{spec['minimum']:.2f} to {spec['maximum']:.2f}"
        else:
            detail = ", ".join(map(str, spec.get("options", [])))
        feature_rows.append([feature, spec["type"], detail])
    story.append(table_from_rows(feature_rows, [2.2 * inch, 1.0 * inch, 3.3 * inch]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(section_heading("5. Efficiency and model quality", styles))
    story.append(
        Paragraph(
            "The selected production models are Logistic Regression for both targets, chosen by the composite validation score. The system is lightweight and fast enough for interactive screening in a browser, with low-latency inference after the models are loaded.",
            styles["SectionBody"],
        )
    )
    performance_rows = [
        ["Target", "Selected model", "Balanced accuracy", "ROC-AUC", "PR-AUC", "Test size"],
        [
            "T21",
            metrics["selected_models"]["t21"],
            f"{metrics['targets']['t21']['selected_metrics']['balanced_accuracy']:.4f}",
            f"{metrics['targets']['t21']['selected_metrics']['roc_auc']:.4f}",
            f"{metrics['targets']['t21']['selected_metrics']['pr_auc']:.4f}",
            str(metrics["test_size"]),
        ],
        [
            "T18",
            metrics["selected_models"]["t18"],
            f"{metrics['targets']['t18']['selected_metrics']['balanced_accuracy']:.4f}",
            f"{metrics['targets']['t18']['selected_metrics']['roc_auc']:.4f}",
            f"{metrics['targets']['t18']['selected_metrics']['pr_auc']:.4f}",
            str(metrics["test_size"]),
        ],
    ]
    story.append(table_from_rows(performance_rows, [0.75 * inch, 1.4 * inch, 1.05 * inch, 0.95 * inch, 0.8 * inch, 0.7 * inch]))
    story.append(
        Paragraph(
            "Note: the synthetic dataset is imbalanced, so high accuracy alone is not a strong indicator. For this reason, the pipeline uses balanced accuracy and PR-AUC alongside ROC-AUC.",
            styles["SmallBody"],
        )
    )

    story.append(Spacer(1, 0.15 * inch))
    story.append(section_heading("6. How to run the project", styles))
    run_steps = [
        "Create or activate the virtual environment.",
        "Install dependencies: pip install -r requirements.txt.",
        "Inspect the raw dataset: python -m ml.inspect_data.",
        "Train the models: python -m ml.train.",
        "Start the web app: python app.py.",
        "Open http://127.0.0.1:5000 in the browser.",
    ]
    for step in run_steps:
        story.append(make_bullet(step, styles["SectionBody"]))

    story.append(Spacer(1, 0.1 * inch))
    story.append(section_heading("7. Useful commands", styles))
    commands_rows = [
        ["Purpose", "Command"],
        ["Install dependencies", "pip install -r requirements.txt"],
        ["Inspect data", "python -m ml.inspect_data"],
        ["Train models", "python -m ml.train"],
        ["Run app", "python app.py"],
        ["Generate PDF report from a screening", "Use the in-app PDF download button on the results page"],
    ]
    story.append(table_from_rows(commands_rows, [2.2 * inch, 4.3 * inch]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(section_heading("8. Important limitations", styles))
    limitations = [
        "The dataset is synthetic.",
        "The system is a research prototype, not a medical diagnostic tool.",
        "Results are screening estimates that must be interpreted by qualified clinicians.",
    ]
    for item in limitations:
        story.append(make_bullet(item, styles["SectionBody"]))

    story.append(Spacer(1, 0.15 * inch))
    story.append(section_heading("9. Project structure", styles))
    structure_rows = [
        ["Folder", "Role"],
        ["ml/", "dataset inspection, preprocessing, training, and prediction"],
        ["backend/", "Flask app, authentication, routes, database, and PDF generation"],
        ["frontend/", "templates, CSS, and client-side JavaScript"],
        ["reports/", "training metrics, dataset inspection outputs, and this PDF"],
        ["models/", "trained artifacts and metadata"],
    ]
    story.append(table_from_rows(structure_rows, [1.4 * inch, 5.1 * inch]))

    story.append(Spacer(1, 0.2 * inch))
    story.append(
        Paragraph(
            "Prepared from the current workspace documentation and generated training artifacts.",
            styles["SmallBody"],
        )
    )

    document = SimpleDocTemplate(
        str(OUTPUT_FILE),
        pagesize=A4,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="Prenatal AI Screening Complete Project Flow",
        author="GitHub Copilot",
    )
    document.build(story)
    return OUTPUT_FILE


if __name__ == "__main__":
    output = build_pdf()
    print(output)
