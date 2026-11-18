"""Demo Mode extractor: pattern matching, no AI and no API key.

Good enough to show the workflow end to end. It reads fixed patterns, so
unusual wording will trip it; the AI extractor is the one meant for real mail.
"""

from __future__ import annotations

import re

from .models import Lead, Message

_FROM_LINE = re.compile(r"(?im)^From:\s*(?:\"?([^<\"\n]*?)\"?\s*)?<?([\w.+-]+@[\w-]+(?:\.[\w-]+)+)>?\s*$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?:\+?\d|\(\d)[\d\s().-]{8,}\d")
_AMOUNT = re.compile(r"(?:USD\s?|\$\s?)(\d[\d,]*(?:\.\d+)?)\s?(k\b)?|\b(\d+(?:\.\d+)?)\s?k\b", re.I)
_CLOSING = re.compile(r"(?i)^(regards|kind regards|best|best regards|thanks|thank you|cheers|sincerely)[,!.]?$")
_PERSON_NAME = re.compile(r"^(?:Dr\.? |Mr\.? |Ms\.? |Mrs\.? )?[A-Z][a-z'-]+(?: [A-Z][a-z'-]+){1,2}$")
_GENERIC_SENDER = re.compile(r"(?i)\b(accounts?|sales|info|support|team|billing|admin|office)\b")
_SUBJECT_PREFIX = re.compile(r"(?i)^\s*((re|fw|fwd)\s*:\s*)+")

_LOW_URGENCY = re.compile(r"(?i)\b(not urgent|no (big |real )?(rush|hurry)|whenever|next quarter|no deadline)\b")
_HIGH_URGENCY = re.compile(
    r"(?i)\b(urgent|asap|immediately|emergency|right away|today|tomorrow|losing (sales|orders|money)|is down)\b"
)

_INVOICE = re.compile(r"(?i)\binvoice\s*#?\s*\d+|\b(payment|amount) (due|overdue)\b")
_ORDER = re.compile(r"(?i)\b(go ahead|place (an|the) order|(like|want) to order|add \d+ more|po number|purchase order)\b")

# First match wins, so the more specific services come first.
_SERVICES = [
    ("E-commerce checkout support", r"checkout|customers can'?t pay|store is down"),
    ("Software licenses and training", r"licen[cs]es?"),
    ("Social media management", r"social media"),
    ("SEO and Google Business Profile", r"\bseo\b"),
    ("Website redesign and online booking", r"(?s)redesign.*\bbook|\bbook.*redesign"),
    ("Website design", r"website"),
    ("Mobile app development", r"\bapp\b"),
]


def _sender(raw: str) -> tuple[str, str | None]:
    """Display name and address of the customer: the last From line, so forwards resolve to the original sender."""
    headers = _FROM_LINE.findall(raw)
    if headers:
        name, address = headers[-1]
        return name.strip(), address
    found = _EMAIL.search(raw)
    return "", found.group(0) if found else None


def _client_name(raw: str, header_name: str) -> str:
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    for previous, line in zip(lines, lines[1:]):
        if _CLOSING.match(previous) and _PERSON_NAME.match(line):
            return line
    if header_name and not _GENERIC_SENDER.search(header_name):
        return header_name
    # No usable header name: a line near the end that reads like a person's name is the signature.
    for line in lines[-6:]:
        if _PERSON_NAME.match(line):
            return line
    return header_name or "Unknown"


def _phone(raw: str) -> str | None:
    for candidate in _PHONE.findall(raw):
        if 10 <= sum(ch.isdigit() for ch in candidate) <= 13:
            return " ".join(candidate.split())
    return None


def _amount(raw: str) -> float | None:
    match = _AMOUNT.search(raw)
    if not match:
        return None
    number, thousands, bare_thousands = match.groups()
    if bare_thousands:
        return float(bare_thousands) * 1000
    value = float(number.replace(",", ""))
    return value * 1000 if thousands else value


def _urgency(raw: str) -> str:
    if _LOW_URGENCY.search(raw):
        return "Low"
    return "High" if _HIGH_URGENCY.search(raw) else "Medium"


def _message_type(raw: str) -> str:
    if _INVOICE.search(raw):
        return "Invoice"
    return "Order" if _ORDER.search(raw) else "Inquiry"


def _service(raw: str, source: str) -> str:
    for label, pattern in _SERVICES:
        if re.search(pattern, raw, re.I):
            return label
    subject = _SUBJECT_PREFIX.sub("", source).strip()
    return subject[:60] if subject else "Not identified"


def extract_with_rules(message: Message) -> Lead:
    header_name, address = _sender(message.raw)
    amount = _amount(message.raw)
    return Lead(
        client_name=_client_name(message.raw, header_name),
        email=address,
        phone=_phone(message.raw),
        message_type=_message_type(message.raw),
        service_requested=_service(message.raw, message.source),
        amount=amount,
        currency="USD" if amount is not None else None,
        urgency=_urgency(message.raw),
    )
