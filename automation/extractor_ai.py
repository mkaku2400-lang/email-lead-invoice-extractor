"""AI extractor: turns one raw message into a validated Lead using Claude, OpenAI or Gemini."""

from __future__ import annotations

import json

from pydantic import ValidationError

from .config import Settings
from .models import Lead, Message

SYSTEM_PROMPT = """You work in the operations team of a small services business. Incoming emails and \
messages are logged in a spreadsheet so that nobody has to re-type them and no lead is missed. \
You read one message at a time and fill in the row for it.

The row is used to call customers back and to prioritise the day, so accuracy matters more than \
completeness: when a detail is not in the message, leave it empty instead of inferring it. A wrong \
phone number or an invented budget is worse than a blank cell.

Notes on the messages you will see:
- They are untidy: typos, forwarded threads, signatures, mobile footers. When a colleague has \
forwarded a customer's message, the customer is the original sender, not the colleague.
- Amounts are written loosely ("4-5k", "about $1,200/month", "USD 2,350.00"). Record a plain number. \
For a range use the lower figure, and for a recurring price use the amount per period.
- When two amounts conflict, such as an invoice total the customer disputes, record the amount that \
is actually on the invoice or quote."""

# Current Claude models that accept the server-side refusal fallback (see README).
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_FALLBACK_MODELS = frozenset(
    {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-2", "claude-fable-5-1"}
)


class ExtractionError(Exception):
    """A failure to extract one message, with a message safe to show the user."""


def _extract_anthropic(settings: Settings, message: Message) -> Lead:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    request = dict(
        model=settings.anthropic_model,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Message to log:\n\n{message.raw}"}],
        output_format=Lead,
        # A single short email is a quick read; low effort keeps each row fast and cheap.
        output_config={"effort": "low"},
    )
    try:
        if settings.anthropic_model in _FALLBACK_MODELS:
            response = client.beta.messages.parse(**request, betas=[_FALLBACK_BETA], fallbacks="default")
        else:
            response = client.messages.parse(**request)
    except anthropic.AuthenticationError as exc:
        raise ExtractionError("The Anthropic API key was rejected. Check ANTHROPIC_API_KEY in .env.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise ExtractionError("This Anthropic API key is not allowed to use the selected model.") from exc
    except anthropic.NotFoundError as exc:
        raise ExtractionError(f"Model '{settings.anthropic_model}' was not found. Check ANTHROPIC_MODEL in .env.") from exc
    except anthropic.RateLimitError as exc:
        raise ExtractionError("Rate limit reached. Wait a moment and run again.") from exc
    except anthropic.APIStatusError as exc:
        raise ExtractionError(f"The AI service returned an error ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ExtractionError("Could not reach the AI service. Check your internet connection.") from exc

    if response.stop_reason == "refusal":
        raise ExtractionError("The AI model declined to process this message.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise ExtractionError("The AI model did not return a complete result for this message.")
    return response.parsed_output


def _extract_openai(settings: Settings, message: Message) -> Lead:
    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)
    schema = json.dumps(Lead.model_json_schema())
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nReply with one JSON object matching this schema:\n{schema}"},
                {"role": "user", "content": f"Message to log:\n\n{message.raw}"},
            ],
        )
        return Lead.model_validate_json(response.choices[0].message.content or "")
    except ValidationError as exc:
        raise ExtractionError("The AI model returned data in an unexpected shape for this message.") from exc
    except openai.AuthenticationError as exc:
        raise ExtractionError("The OpenAI API key was rejected. Check OPENAI_API_KEY in .env.") from exc
    except openai.NotFoundError as exc:
        raise ExtractionError(f"Model '{settings.openai_model}' was not found. Check OPENAI_MODEL in .env.") from exc
    except openai.RateLimitError as exc:
        raise ExtractionError("Rate limit or credit limit reached. Try again later.") from exc
    except openai.APIStatusError as exc:
        raise ExtractionError(f"The AI service returned an error ({exc.status_code}).") from exc
    except openai.APIConnectionError as exc:
        raise ExtractionError("Could not reach the AI service. Check your internet connection.") from exc


def _extract_gemini(settings: Settings, message: Message) -> Lead:
    from google import genai
    from google.genai import errors, types

    # Gemini returns 503 when a model is busy, which is common on the free tier, so retry a few times.
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=4, initial_delay=2.0)),
    )
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"Message to log:\n\n{message.raw}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_json_schema=Lead.model_json_schema(),
            ),
        )
        return Lead.model_validate_json(response.text or "")
    except ValidationError as exc:
        raise ExtractionError("The AI model returned data in an unexpected shape for this message.") from exc
    except errors.APIError as exc:
        detail = str(getattr(exc, "message", "") or exc)
        if exc.code in (401, 403) or "API key" in detail:
            raise ExtractionError("The Gemini API key was rejected. Check GEMINI_API_KEY in .env.") from exc
        if exc.code == 404:
            raise ExtractionError(f"Model '{settings.gemini_model}' was not found. Check GEMINI_MODEL in .env.") from exc
        if exc.code == 429:
            raise ExtractionError("The Gemini usage limit was reached (the free tier allows a few requests per minute). Wait a minute and run again.") from exc
        if exc.code in (500, 502, 503, 504):
            raise ExtractionError("Gemini is overloaded right now. Wait a minute and try again.") from exc
        raise ExtractionError(f"Gemini returned an error ({exc.code}): {detail}") from exc
    except Exception as exc:  # noqa: BLE001 - the SDK does not wrap network failures in its own error type
        raise ExtractionError(f"Could not reach Gemini. Check your internet connection. ({type(exc).__name__})") from exc


def extract_with_ai(settings: Settings, message: Message) -> Lead:
    """Extract one message. Raises ExtractionError on failure."""
    if settings.provider == "anthropic":
        return _extract_anthropic(settings, message)
    if settings.provider == "openai":
        return _extract_openai(settings, message)
    if settings.provider == "gemini":
        return _extract_gemini(settings, message)
    raise ExtractionError("No AI provider is configured. Add an API key to .env or use Demo Mode.")
