"""End-to-end check of extraction, export and the dashboard, with no API key needed.

Usage:  python tests/smoke_test.py
"""

from __future__ import annotations

import os
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from openpyxl import load_workbook  # noqa: E402

from automation.export import build_workbook, leads_to_frame, summarize  # noqa: E402
from automation.extractor_rules import extract_with_rules  # noqa: E402
from automation.models import Message  # noqa: E402
from automation.sample_emails import sample_messages  # noqa: E402

# (client, email, phone digits, type, amount, urgency) for each sample email, in inbox order
EXPECTED = [
    ("Dr. Priya Raman", "priya@ramandental.example", "4155550134", "Inquiry", 4500.0, "High"),
    ("Dev Okafor", "dev.okafor@brightlinelogistics.example", "3125550188", "Order", 850.0, "Low"),
    ("Elena Marsh", "accounts@hartwellbakery.example", "16465550171", "Invoice", 2350.0, "Medium"),
    ("Tom Bradley", "tom@peakoutfitters.example", "7205550119", "Inquiry", None, "High"),
    ("Laura Chen", "laura.chen@greenleafyoga.example", "5035550162", "Inquiry", 1200.0, "Low"),
]


def digits(text: str | None) -> str:
    return "".join(ch for ch in (text or "") if ch.isdigit())


def check_extraction() -> list:
    rows = []
    for message, expected in zip(sample_messages(), EXPECTED, strict=True):
        lead = extract_with_rules(message)
        actual = (lead.client_name, lead.email, digits(lead.phone), lead.message_type, lead.amount, lead.urgency)
        assert actual == expected, f"{message.source!r}:\n  expected {expected}\n  got      {actual}"
        print(f"  ok   {lead.client_name:<16} {lead.message_type:<8} {lead.urgency:<6} {lead.service_requested}")
        rows.append((message.source, lead))

    pasted = Message("Pasted message", "hi its Maria Lopez, need a quote for a new website asap. budget 3k. maria@lopezlaw.example 212-555-0147")
    lead = extract_with_rules(pasted)
    assert (lead.email, lead.amount, lead.urgency) == ("maria@lopezlaw.example", 3000.0, "High"), lead
    print("  ok   pasted free-text message")
    return rows


def check_export(rows: list) -> None:
    frame = leads_to_frame(rows)
    summary = summarize(frame)
    assert (summary["processed"], summary["high_urgency"], summary["total_value"]) == (5, 2, 8900.0), summary

    sheet = load_workbook(BytesIO(build_workbook(frame)))["Leads"]
    assert sheet.max_row == 6 and sheet.freeze_panes == "A2", (sheet.max_row, sheet.freeze_panes)
    assert [c.value for c in sheet[1]][:3] == ["Source", "Client Name", "Email"]
    print("  ok   summary numbers and Excel file (5 rows, styled header)")


def check_app() -> None:
    from streamlit.testing.v1 import AppTest

    # Force Demo Mode regardless of what is in the local .env file.
    os.environ["ANTHROPIC_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["GOOGLE_API_KEY"] = ""

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception, app.exception
    next(b for b in app.button if b.label == "Run AI Automation").click().run()
    assert not app.exception, app.exception
    assert len(app.session_state["frame"]) == 5, "expected 5 extracted rows"
    assert [m.value for m in app.metric] == ["5", "2", "$8,900"], [m.value for m in app.metric]
    print("  ok   dashboard runs, fills the table and updates the summary bar")


if __name__ == "__main__":
    check_export(check_extraction())
    check_app()
    print("All checks passed.")
