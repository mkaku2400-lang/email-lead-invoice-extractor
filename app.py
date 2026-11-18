"""Lead & Invoice Extractor: reads messy business emails and logs them as spreadsheet rows.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from automation.config import get_settings
from automation.export import URGENCY_COLORS, build_workbook, leads_to_frame, save_workbook, summarize
from automation.extractor_ai import ExtractionError, extract_with_ai
from automation.extractor_rules import extract_with_rules
from automation.models import Message
from automation.sample_emails import inbox_rows, sample_messages

TABLE_COLUMNS = ["Urgency", "Client Name", "Type", "Service Requested", "Amount", "Currency", "Email", "Phone"]

st.set_page_config(page_title="Lead & Invoice Extractor", layout="wide")
settings = get_settings()

state = st.session_state
state.setdefault("frame", None)
state.setdefault("errors", [])
state.setdefault("saved_to", None)
state.setdefault("save_error", None)


def run_extraction(messages: list[Message], use_ai: bool) -> None:
    """Extract every message, then store the table and write the Excel file."""
    rows, errors = [], []
    progress = st.progress(0.0, text="Starting...")
    for index, message in enumerate(messages, start=1):
        progress.progress(index / len(messages), text=f"Reading {index} of {len(messages)}: {message.source}")
        try:
            lead = extract_with_ai(settings, message) if use_ai else extract_with_rules(message)
            rows.append((message.source, lead))
        except ExtractionError as exc:
            errors.append(f"{message.source}: {exc}")
            if not rows:
                # The first message failing means a setup problem (key, model, network); the rest would fail too.
                break
    progress.empty()

    state.errors = errors
    state.frame = leads_to_frame(rows) if rows else None
    state.saved_to = state.save_error = None
    if rows:
        try:
            state.saved_to = save_workbook(build_workbook(state.frame))
        except OSError:
            state.save_error = "Could not overwrite extracted_leads.xlsx. Close it in Excel and run again."


def money(value: float, currency: str) -> str:
    return f"${value:,.0f}" if currency == "USD" else f"{value:,.0f} {currency}"


# ----------------------------------------------------------------- sidebar --
with st.sidebar:
    st.subheader("Extraction engine")
    has_api_key = settings.provider is not None
    demo_mode = st.toggle(
        "Demo Mode (no API key)",
        value=not has_api_key,
        disabled=not has_api_key,
        help="Uses pattern matching instead of an AI model.",
    )
    if demo_mode:
        st.caption("Demo Mode is on: fields are found by pattern rules. Add an API key to `.env` to use an AI model.")
    else:
        st.caption(f"AI Mode: {settings.provider.title()}, model `{settings.model}`.")

    st.divider()
    st.subheader("What this replaces")
    st.caption(
        "Someone opening each email, working out who wrote and what they want, "
        "and typing it into a spreadsheet. Here each message becomes one row, "
        "and the spreadsheet is written for you."
    )

# -------------------------------------------------------------------- main --
st.title("Lead & Invoice Extractor")
st.caption("Each incoming email becomes one spreadsheet row: who wrote, what they want, how much, and how urgent.")

summary = summarize(state.frame) if state.frame is not None else None
processed, high, value = st.columns(3)
processed.metric("Total leads processed", summary["processed"] if summary else 0)
high.metric("High urgency", summary["high_urgency"] if summary else 0)
value.metric("Total estimated value", money(summary["total_value"], summary["currency"]) if summary else "$0")
if summary and summary["other_currencies"]:
    st.caption(f"The total covers {summary['currency']} only. Other currencies present: {', '.join(summary['other_currencies'])}.")

st.divider()
inbox_column, paste_column = st.columns([3, 2], gap="large")

with inbox_column:
    st.subheader("Sample inbox")
    include_samples = st.checkbox("Include these 5 emails", value=True)
    st.dataframe(
        inbox_rows(),
        hide_index=True,
        width="stretch",
        column_config={
            "From": st.column_config.TextColumn(width="medium"),
            "Subject": st.column_config.TextColumn(width="medium"),
            "Received": st.column_config.TextColumn(width="small"),
        },
    )
    with st.expander("Read the emails as they arrived"):
        for sample in sample_messages():
            st.text(sample.raw)
            st.divider()

with paste_column:
    st.subheader("Your own message")
    pasted = st.text_area(
        "Paste an email or message",
        height=215,
        placeholder="Paste any raw email, WhatsApp message or contact-form text here...",
    )

if st.button("Run AI Automation", type="primary"):
    queue = sample_messages() if include_samples else []
    if pasted.strip():
        queue.append(Message(source="Pasted message", raw=pasted.strip()))
    if queue:
        run_extraction(queue, use_ai=not demo_mode)
        st.rerun()  # redraw so the summary bar at the top shows the new numbers
    else:
        st.warning("There is nothing to process. Tick the sample emails or paste a message.")

for error in state.errors:
    st.error(error)

if state.frame is not None:
    st.subheader("Extracted data")
    # On screen, lead with what decides the next action. The export keeps every column, including Source.
    on_screen = state.frame[TABLE_COLUMNS].fillna({"Currency": "", "Email": "", "Phone": ""})
    # A missing amount should read as an empty cell, which the grid only does for text.
    on_screen["Amount"] = on_screen["Amount"].map(lambda v: "" if pd.isna(v) else f"{v:,.2f}")
    styled = on_screen.style.map(
        lambda u: f"background-color: #{URGENCY_COLORS.get(u, 'FFFFFF')}", subset=["Urgency"]
    ).set_properties(subset=["Amount"], **{"text-align": "right"})
    st.dataframe(
        styled,
        hide_index=True,
        width="stretch",
        column_config={
            **{name: st.column_config.Column(width="small") for name in ("Urgency", "Type", "Amount", "Currency")},
            "Email": st.column_config.Column(width="medium"),
        },
    )

    excel_column, csv_column, note_column = st.columns([1, 1, 4])
    excel_column.download_button(
        "Download Excel",
        data=build_workbook(state.frame),
        file_name="extracted_leads.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    csv_column.download_button(
        "Download CSV",
        data=state.frame.to_csv(index=False).encode("utf-8-sig"),
        file_name="extracted_leads.csv",
        mime="text/csv",
        width="stretch",
    )
    if state.saved_to:
        note_column.caption(f"Also saved to `{state.saved_to}`")
    if state.save_error:
        note_column.warning(state.save_error)
