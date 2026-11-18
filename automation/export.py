"""Turn extracted leads into a table, summary numbers and a formatted Excel file."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import COLUMNS, Lead

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "output" / "extracted_leads.xlsx"

URGENCY_COLORS = {"High": "F8D7DA", "Medium": "FFF3CD", "Low": "D1E7DD"}
_HEADER_FILL = PatternFill("solid", fgColor="1F2937")
_MAX_COLUMN_WIDTH = 45


def leads_to_frame(rows: list[tuple[str, Lead]]) -> pd.DataFrame:
    """One row per message, with the column names used on screen and in the export."""
    records = [{"source": source, **lead.model_dump()} for source, lead in rows]
    return pd.DataFrame(records, columns=list(COLUMNS)).rename(columns=COLUMNS)


def summarize(frame: pd.DataFrame) -> dict:
    """Numbers for the summary bar. The total covers the most common currency only."""
    amounts = frame.dropna(subset=["Amount"])
    totals = amounts.groupby("Currency")["Amount"].sum().sort_values(ascending=False)
    return {
        "processed": len(frame),
        "high_urgency": int((frame["Urgency"] == "High").sum()),
        "total_value": float(totals.iloc[0]) if len(totals) else 0.0,
        "currency": totals.index[0] if len(totals) else "USD",
        "other_currencies": list(totals.index[1:]),
    }


def build_workbook(frame: pd.DataFrame) -> bytes:
    """Excel file as bytes: styled header, frozen top row, filters, coloured urgency, sized columns."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Leads")
        sheet = writer.sheets["Leads"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(vertical="center")
        sheet.row_dimensions[1].height = 22

        headers = [cell.value for cell in sheet[1]]
        amount_column = headers.index("Amount") + 1
        urgency_column = headers.index("Urgency") + 1
        for row in sheet.iter_rows(min_row=2):
            row[amount_column - 1].number_format = "#,##0.00"
            urgency = row[urgency_column - 1]
            if urgency.value in URGENCY_COLORS:
                urgency.fill = PatternFill("solid", fgColor=URGENCY_COLORS[urgency.value])

        for index, column in enumerate(sheet.columns, start=1):
            longest = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column)
            sheet.column_dimensions[get_column_letter(index)].width = min(longest + 3, _MAX_COLUMN_WIDTH)
    return buffer.getvalue()


def save_workbook(data: bytes) -> Path:
    """Write the Excel file to the output folder. Raises OSError if it is open in Excel."""
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_bytes(data)
    return OUTPUT_FILE
