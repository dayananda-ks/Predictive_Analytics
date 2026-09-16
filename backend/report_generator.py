from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf_report(payload: dict[str, Any], title: str, disclaimer: str) -> BytesIO:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=title)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallBody", parent=styles["BodyText"], fontSize=9, leading=11))

    story = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Screening timestamp: {payload.get('timestamp', '')}", styles["BodyText"]),
        Paragraph(f"Selected model: {payload.get('selected_model', '')}", styles["BodyText"]),
        Spacer(1, 12),
    ]

    rows = [["Field", "Value"]]
    for key, value in payload.get("input_data", {}).items():
        rows.append([key, str(value)])
    table = Table(rows, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12))

    summary_rows = [
        ["Measure", "Value"],
        ["T21 model-estimated screening risk", f"{payload.get('t21_percentage', 0):.2f}%"],
        ["T21 prototype risk category", payload.get("t21_risk_level", "")],
        ["T18 model-estimated screening risk", f"{payload.get('t18_percentage', 0):.2f}%"],
        ["T18 prototype risk category", payload.get("t18_risk_level", "")],
    ]
    summary = Table(summary_rows, repeatRows=1)
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ffffff")),
            ]
        )
    )
    story.extend([Paragraph("Screening summary", styles["Heading2"]), summary, Spacer(1, 12)])

    story.append(Paragraph("Model feature contribution", styles["Heading2"]))
    for target_name, contributions in payload.get("feature_contributions", {}).items():
        lines = [f"{item['feature']}: {item['contribution']:.4f} ({item.get('method', '')})" for item in contributions]
        story.append(Paragraph(f"{target_name.upper()}", styles["Heading3"]))
        for line in lines:
            story.append(Paragraph(line, styles["SmallBody"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(disclaimer, styles["SmallBody"]))

    document.build(story)
    buffer.seek(0)
    return buffer
