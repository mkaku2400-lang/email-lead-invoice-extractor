"""Settings loaded from the .env file / environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Values people leave in .env by accident; treated the same as "no key".
_PLACEHOLDER_MARKERS = ("your", "xxx", "changeme", "replace")


def _clean_key(value: str | None) -> str:
    value = (value or "").strip().strip('"').strip("'")
    if not value or any(marker in value.lower() for marker in _PLACEHOLDER_MARKERS):
        return ""
    return value


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    openai_api_key: str
    gemini_api_key: str
    preferred_provider: str
    anthropic_model: str
    openai_model: str
    gemini_model: str

    @property
    def provider(self) -> str | None:
        """The AI provider to use, or None when no API key is configured."""
        keys = {"anthropic": self.anthropic_api_key, "openai": self.openai_api_key, "gemini": self.gemini_api_key}
        if keys.get(self.preferred_provider):
            return self.preferred_provider
        return next((name for name, key in keys.items() if key), None)

    @property
    def model(self) -> str:
        models = {"openai": self.openai_model, "gemini": self.gemini_model}
        return models.get(self.provider, self.anthropic_model)


def get_settings() -> Settings:
    return Settings(
        anthropic_api_key=_clean_key(os.getenv("ANTHROPIC_API_KEY")),
        openai_api_key=_clean_key(os.getenv("OPENAI_API_KEY")),
        gemini_api_key=_clean_key(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        preferred_provider=os.getenv("LLM_PROVIDER", "anthropic").strip().lower(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip(),
    )
