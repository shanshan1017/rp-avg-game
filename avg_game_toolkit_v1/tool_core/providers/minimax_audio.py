"""MiniMax audio request payload builders."""

from __future__ import annotations

from typing import Any

from .base import sanitized_request


DEFAULT_BASE_URL = "https://api.minimaxi.com"


def endpoint(path: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return base_url.rstrip("/") + path


def build_tts_payload(prompt_item: dict[str, Any]) -> dict[str, Any]:
    params = dict(prompt_item.get("model_parameters") or {})
    return {
        "model": params.pop("model", "speech-2.8-hd"),
        "text": prompt_item["prompt"],
        "stream": params.pop("stream", False),
        "voice_setting": params.pop(
            "voice_setting",
            {
                "voice_id": params.pop("voice_id", "male-qn-qingse"),
                "speed": 1,
                "vol": 1,
                "pitch": 0,
                "emotion": "neutral",
            },
        ),
        "audio_setting": params.pop(
            "audio_setting",
            {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
            },
        ),
        "subtitle_enable": params.pop("subtitle_enable", False),
        "output_format": params.pop("output_format", "hex"),
        **params,
    }


def build_voice_design_payload(prompt_item: dict[str, Any]) -> dict[str, Any]:
    params = dict(prompt_item.get("model_parameters") or {})
    payload = {
        "prompt": prompt_item["prompt"],
        "preview_text": params.pop("preview_text", "这是一段用于试听角色音色的台词。"),
        "aigc_watermark": params.pop("aigc_watermark", False),
    }
    if "voice_id" in params:
        payload["voice_id"] = params.pop("voice_id")
    payload.update(params)
    return payload


def build_music_payload(prompt_item: dict[str, Any]) -> dict[str, Any]:
    params = dict(prompt_item.get("model_parameters") or {})
    payload = {
        "model": params.pop("model", "music-2.6"),
        "prompt": prompt_item["prompt"],
        "stream": params.pop("stream", False),
        "output_format": params.pop("output_format", "hex"),
        "is_instrumental": params.pop("is_instrumental", True),
        "audio_setting": params.pop(
            "audio_setting",
            {
                "sample_rate": 44100,
                "bitrate": 256000,
                "format": "mp3",
            },
        ),
    }
    if "lyrics" in params:
        payload["lyrics"] = params.pop("lyrics")
    payload.update(params)
    return payload


def build_request(prompt_item: dict[str, Any], base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    capability = prompt_item.get("capability")
    if capability == "audio.voice_design":
        path = "/v1/voice_design"
        payload = build_voice_design_payload(prompt_item)
    elif capability == "audio.music_generation":
        path = "/v1/music_generation"
        payload = build_music_payload(prompt_item)
    else:
        path = "/v1/t2a_v2"
        payload = build_tts_payload(prompt_item)
    return sanitized_request(
        "POST",
        endpoint(path, base_url),
        {"Authorization": "Bearer ${MINIMAX_API_KEY}", "Content-Type": "application/json"},
        payload,
    )

