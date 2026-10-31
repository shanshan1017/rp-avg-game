"""GPT Image request payload builders."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from .base import merge_prompt, sanitized_request


DEFAULT_BASE_URL = "https://api.example.com/v1"
DEFAULT_MODEL = "gpt-image-2-c"


def normalize_base_url(base_url: str = DEFAULT_BASE_URL) -> str:
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    for suffix in ("/images/generations", "/images/edits"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def endpoint(base_url: str = DEFAULT_BASE_URL, action: str = "generations") -> str:
    path = "images/edits" if action == "edits" else "images/generations"
    return urljoin(normalize_base_url(base_url).rstrip("/") + "/", path)


def build_payload(prompt_item: dict[str, Any], global_style: str, default_model: str = DEFAULT_MODEL) -> dict[str, Any]:
    params = dict(prompt_item.get("model_parameters") or {})
    for local_only_key in ["background_policy", "chroma_key", "hard_generation_rules", "local_output_path"]:
        params.pop(local_only_key, None)
    capability = prompt_item.get("capability", "")
    payload = {
        "model": params.pop("model", default_model),
        "prompt": merge_prompt(global_style, prompt_item["prompt"], prompt_item.get("negative_prompt")),
        "n": params.pop("n", 1),
        "size": params.pop("size", "1536x1024"),
    }
    payload.update(params)
    if capability == "image.streaming":
        payload.setdefault("stream", True)
        payload.setdefault("partial_images", 2)
    return payload


def build_request(prompt_item: dict[str, Any], global_style: str, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    capability = prompt_item.get("capability", "")
    action = "edits" if capability in {"image.reference_edit", "image.mask_edit"} else "generations"
    payload = build_payload(prompt_item, global_style)
    headers = {"Authorization": "Bearer ${GPT_IMAGE_API_KEY}"}
    if action != "edits":
        headers["Content-Type"] = "application/json"
    return sanitized_request(
        "POST",
        endpoint(base_url, action),
        headers,
        payload,
    )
