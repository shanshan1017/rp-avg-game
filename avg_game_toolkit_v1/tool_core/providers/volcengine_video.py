"""Volcengine / Ark Seedance video request payload builders."""

from __future__ import annotations

from typing import Any

from .base import merge_prompt, sanitized_request


DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seedance-2-0-260128"


def task_endpoint(base_url: str = DEFAULT_BASE_URL) -> str:
    return base_url.rstrip("/") + "/contents/generations/tasks"


def build_content(prompt_item: dict[str, Any], global_style: str) -> list[dict[str, Any]]:
    params = prompt_item.get("model_parameters") or {}
    text = merge_prompt(global_style, prompt_item["prompt"], prompt_item.get("negative_prompt"))
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    for ref in params.get("first_frame_images") or []:
        content.append({"type": "image_url", "image_url": {"url": ref}, "role": "first_frame"})
    for ref in params.get("reference_images") or []:
        content.append({"type": "image_url", "image_url": {"url": ref}, "role": "reference_image"})
    for ref in params.get("reference_videos") or []:
        content.append({"type": "video_url", "video_url": {"url": ref}, "role": "reference_video"})
    for ref in params.get("reference_audio") or []:
        content.append({"type": "audio_url", "audio_url": {"url": ref}, "role": "reference_audio"})
    return content


def build_payload(prompt_item: dict[str, Any], global_style: str, default_model: str = DEFAULT_MODEL) -> dict[str, Any]:
    params = dict(prompt_item.get("model_parameters") or {})
    params.pop("hard_generation_rules", None)
    duration = params.pop("duration", params.pop("duration_sec", 8))
    payload = {
        "model": params.pop("model", default_model),
        "content": build_content(prompt_item, global_style),
        "generate_audio": params.pop("generate_audio", True),
        "ratio": params.pop("ratio", "16:9"),
        "duration": duration,
        "resolution": params.pop("resolution", "720p"),
        "watermark": params.pop("watermark", False),
        "return_last_frame": params.pop("return_last_frame", False),
    }
    for unsupported_key in ["first_frame_images", "reference_images", "reference_videos", "reference_audio"]:
        params.pop(unsupported_key, None)
    payload.update(params)
    return payload


def build_request(prompt_item: dict[str, Any], global_style: str, base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    return sanitized_request(
        "POST",
        task_endpoint(base_url),
        {"Authorization": "Bearer ${ARK_API_KEY}", "Content-Type": "application/json"},
        build_payload(prompt_item, global_style),
    )
