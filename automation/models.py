"""Data shapes shared by the extractors, the dashboard and the export."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Message:
    """One incoming email or pasted message, exactly as received."""

    source: str  # short label shown in the results table
    raw: str  # full text, headers included when present


class Lead(BaseModel):
    """What gets extracted from one message. Missing details stay empty rather than guessed."""

    client_name: str = Field(description="The customer who wrote the message, not a colleague who forwarded it.")
    email: str | None = Field(description="The customer's email address, or null if none appears.")
    phone: str | None = Field(description="The customer's phone number as written, or null if none appears.")
    message_type: Literal["Inquiry", "Order", "Invoice"] = Field(
        description="Inquiry: asking about a service or reporting a problem. "
        "Order: confirming a purchase. Invoice: about an invoice or payment."
    )
    service_requested: str = Field(description="What they want, in at most eight words.")
    amount: float | None = Field(
        description="Budget, price or invoice amount as a plain number. For a range use the lower figure. "
        "Null if no amount is stated."
    )
    currency: str | None = Field(description="Three-letter currency code of the amount, or null if there is no amount.")
    urgency: Literal["High", "Medium", "Low"] = Field(
        description="High: something is broken, or a deadline within about a week, or they say it is urgent. "
        "Low: they say there is no rush or the start is months away. Medium: everything else."
    )


COLUMNS = {
    "source": "Source",
    "client_name": "Client Name",
    "email": "Email",
    "phone": "Phone",
    "message_type": "Type",
    "service_requested": "Service Requested",
    "amount": "Amount",
    "currency": "Currency",
    "urgency": "Urgency",
}
