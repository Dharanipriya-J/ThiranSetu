"""Google Gemini API client with response caching and clean deterministic fallback."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger("thiransetu.gemini")

_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL_SECONDS = 300.0
_MAX_CACHE_ENTRIES = 128

_LANG_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "mr": "Marathi",
}


def language_name(code: str) -> str:
    return _LANG_NAMES.get(code, "English")


def generate_text(prompt: str, system_instruction: str = "") -> tuple[str | None, str]:
    """Call Gemini generateContent API.

    Returns (text, mode) where mode is 'gemini' on success or 'deterministic' when
    the key is missing, disabled, or the upstream call fails.
    """
    settings = get_settings()
    if not settings.llm_available:
        return None, "deterministic"

    cache_key = hashlib.sha256(f"{settings.gemini_model}:{system_instruction}:{prompt}".encode()).hexdigest()
    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1], "gemini"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.35, "maxOutputTokens": 700},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    try:
        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            resp = client.post(url, params={"key": settings.gemini_api_key}, json=payload)
            resp.raise_for_status()
            data = resp.json()
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            logger.warning("Gemini returned empty response; falling back to deterministic mode.")
            return None, "deterministic"
        if len(_CACHE) >= _MAX_CACHE_ENTRIES:
            oldest = min(_CACHE.items(), key=lambda item: item[1][0])[0]
            del _CACHE[oldest]
        _CACHE[cache_key] = (now, text)
        return text, "gemini"
    except Exception as exc:
        logger.warning("Gemini request failed (%s); falling back to deterministic mode.", type(exc).__name__)
        return None, "deterministic"
