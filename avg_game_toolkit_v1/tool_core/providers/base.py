"""Shared provider adapter helpers."""

from __future__ import annotations

import copy
import re
from typing import Any


SECRET_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "token",
    "access_token",
    "secret",
    "key",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-api-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
]


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key.lower() in SECRET_KEYS:
                cleaned[key] = "<redacted>"
            else:
                cleaned[key] = redact(item)
        return cleaned
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        cleaned = value
        for pattern in SECRET_VALUE_PATTERNS:
            cleaned = pattern.sub("<redacted>", cleaned)
        return cleaned
    return value


def sanitized_request(method: str, url: str, headers: dict[str, Any] | None, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": method,
        "url": url,
        "headers": redact(copy.deepcopy(headers or {})),
        "payload": redact(copy.deepcopy(payload)),
    }


def merge_prompt(global_style: str, prompt: str, negative_prompt: str | None = None) -> str:
    parts = [part.strip() for part in [global_style, prompt] if part and part.strip()]
    if negative_prompt:
        parts.append(f"Negative prompt: {negative_prompt.strip()}")
    return "\n\n".join(parts)

