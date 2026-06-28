"""Shared runtime configuration helpers."""

from __future__ import annotations

import os


def normalize_groq_api_key() -> None:
    """Allow the common GROK_API_KEY typo as an alias for Groq's SDK env var."""
    if os.getenv("GROQ_API_KEY"):
        return
    grok_key = os.getenv("GROK_API_KEY")
    if grok_key:
        os.environ["GROQ_API_KEY"] = grok_key


def has_groq_api_key() -> bool:
    normalize_groq_api_key()
    return bool(os.getenv("GROQ_API_KEY"))
