#!/usr/bin/env python3
"""Apply hard AVG visual-asset execution rules to a prompt pack.

This script turns an agent-authored prompt pack into a stricter job file that
the Python executor can run deterministically. It does not call providers.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


CHROMA_GREEN = "#00FF00"
NO_TEXT_NEGATIVE = [
    "任何可读文字",
    "中文书法",
    "英文文字",
    "角色名标签",
    "印章",
    "水印",
    "字幕",
    "UI按钮",
    "海报排版",
]
NO_SCENE_FOR_CUTOUT = [
    "山水背景",
    "擂台背景",
    "云海背景",
    "室内背景",
    "复杂光效背景",
    "法阵背景",
    "第二个人物",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_unique(items: list[str], additions: list[str]) -> list[str]:
    seen = set(items)
    for item in additions:
        if item not in seen:
            items.append(item)
            seen.add(item)
    return items


def negative_with(existing: str | None, additions: list[str]) -> str:
    parts = [part.strip() for part in (existing or "").split(",") if part.strip()]
    return ", ".join(append_unique(parts, additions))


def ref_id_for_prompt(prompt: dict[str, Any]) -> str:
    chars = prompt.get("source_character_ids") or []
    if chars:
        return f"ref_{chars[0]}"
    asset_id = prompt.get("asset_id", "")
    for prefix in ["char_"]:
        if asset_id.startswith(prefix):
            name = asset_id[len(prefix):].split("_")
            if len(name) >= 2:
                return "ref_" + "_".join(name[:2])
    return ""


def harden_global_style(style: dict[str, Any]) -> dict[str, Any]:
    style = copy.deepcopy(style or {})
    summary = style.get("style_summary", "")
    summary = summary.replace("所有可读文字为简体中文。", "")
    summary = summary.replace("所有可读文字为简体中文", "")
    style["style_summary"] = summary.strip()
    must_include = list(style.get("must_include") or [])
    must_include = [item for item in must_include if "可读文字" not in item and "中文" not in item]
    style["must_include"] = must_include
    style["must_not_include"] = append_unique(list(style.get("must_not_include") or []), NO_TEXT_NEGATIVE)
    style["negative_prompt"] = negative_with(style.get("negative_prompt"), NO_TEXT_NEGATIVE)
    return style


def character_cutout_intro(asset_type: str) -> str:
    if asset_type == "character_reference_image":
        return (
            "硬规则: 生成单人角色主形象/人设图。纯色绿幕背景，背景颜色必须是均匀的 #00FF00。"
            "角色完整、居中、边缘清晰，适合后续自动扣图。不要场景背景、不要书法、不要标签、不要任何可读文字。"
        )
    return (
        "硬规则: 使用输入参考图保持同一角色身份、脸型、发型、服装、体型、主色和配饰。"
        "只改变本条要求的表情或小姿态，不重画成新角色。纯色绿幕背景，背景颜色必须是均匀的 #00FF00。"
        "角色完整、居中、边缘清晰，适合后续自动扣图。不要场景背景、不要书法、不要标签、不要任何可读文字。"
    )


def harden_character_prompt(prompt: dict[str, Any]) -> None:
    asset_type = prompt.get("asset_type", "")
    params = dict(prompt.get("model_parameters") or {})
    params.setdefault("size", "1024x1024")
    params.setdefault("quality", "high")
    params.setdefault("style", "natural")
    params["background_policy"] = "chroma_key_green_cutout"
    params["chroma_key"] = {
        "enabled": True,
        "color": CHROMA_GREEN,
        "tolerance": 72,
        "spill_desaturate": True,
    }
    params["hard_generation_rules"] = {
        "single_character_only": True,
        "no_text_overlay": True,
        "preserve_identity_from_input": asset_type == "character_expression_image",
        "allowed_change": "reference image only: facial expression, eye direction, minor hand/pose adjustment",
    }
    prompt["model_parameters"] = params
    prompt["negative_prompt"] = negative_with(prompt.get("negative_prompt"), NO_TEXT_NEGATIVE + NO_SCENE_FOR_CUTOUT)
    prompt["prompt"] = character_cutout_intro(asset_type) + "\n\n原始意图: " + prompt.get("prompt", "")
    runtime_use = dict(prompt.get("expected_runtime_use") or {})
    runtime_use["presentation"] = "transparent_character_cutout"
    prompt["expected_runtime_use"] = runtime_use
    if asset_type == "character_expression_image":
        prompt["capability"] = "image.reference_edit"
        if not prompt.get("input_asset_ids"):
            ref_id = ref_id_for_prompt(prompt)
            if ref_id:
                prompt["input_asset_ids"] = [ref_id]
    else:
        prompt["capability"] = "image.text_to_image"


def harden_video_first_frame(prompt: dict[str, Any]) -> None:
    params = dict(prompt.get("model_parameters") or {})
    params.setdefault("size", "1280x720")
    params["hard_generation_rules"] = {
        "must_use_character_reference": bool(prompt.get("input_asset_ids")),
        "no_text_overlay": True,
        "first_frame_for_video": True,
    }
    prompt["model_parameters"] = params
    if prompt.get("input_asset_ids"):
        prompt["capability"] = "image.reference_edit"
    prompt["negative_prompt"] = negative_with(prompt.get("negative_prompt"), NO_TEXT_NEGATIVE)
    prompt["prompt"] = (
        "硬规则: 这是视频首帧，必须保持输入角色参考图的身份、服装和配饰。"
        "允许生成场景背景，但不要任何书法、标签、字幕、水印或 UI 文字。"
        "角色必须与输入参考图可识别地属于同一人。\n\n原始意图: "
        + prompt.get("prompt", "")
    )


def harden_video_clip(prompt: dict[str, Any]) -> None:
    params = dict(prompt.get("model_parameters") or {})
    params["duration"] = max(4, int(params.get("duration") or params.get("duration_sec") or 4))
    params.setdefault("ratio", "16:9")
    params.setdefault("resolution", "720p")
    params.setdefault("generate_audio", True)
    params.setdefault("return_last_frame", True)
    params["hard_generation_rules"] = {
        "must_use_first_frame_reference": True,
        "no_text_overlay": True,
        "preserve_character_from_first_frame": True,
    }
    prompt["model_parameters"] = params
    prompt["capability"] = "video.first_frame_to_video"
    prompt["negative_prompt"] = negative_with(prompt.get("negative_prompt"), NO_TEXT_NEGATIVE)
    prompt["prompt"] = (
        "硬规则: 必须使用输入首帧作为画面构图、角色身份、服装和场景连续性的依据。"
        "不要把角色改成陌生人，不要添加字幕、标签、水印或 UI 文字。\n\n原始意图: "
        + prompt.get("prompt", "")
    )


def harden_scene_like_prompt(prompt: dict[str, Any]) -> None:
    prompt["negative_prompt"] = negative_with(prompt.get("negative_prompt"), NO_TEXT_NEGATIVE)
    if prompt.get("asset_type") in {"ui_concept_image", "ui_image"}:
        prompt["prompt"] = (
            "硬规则: UI 概念图只表达布局和气质，不要生成可读文字内容；文字应由 runtime DOM 渲染。\n\n原始意图: "
            + prompt.get("prompt", "")
        )


def harden_prompt_pack(data: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(data)
    result["global_style_bible"] = harden_global_style(result.get("global_style_bible") or {})
    for prompt in result.get("prompts") or []:
        asset_type = prompt.get("asset_type", "")
        if asset_type in {"character_reference_image", "character_expression_image"}:
            harden_character_prompt(prompt)
        elif asset_type == "video_first_frame":
            harden_video_first_frame(prompt)
        elif asset_type == "video_clip":
            harden_video_clip(prompt)
        else:
            harden_scene_like_prompt(prompt)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Harden AVG visual prompt pack for deterministic provider execution")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    hardened = harden_prompt_pack(load_json(args.input))
    write_json(args.output, hardened)
    print(json.dumps({
        "input": str(args.input),
        "output": str(args.output),
        "prompt_count": len(hardened.get("prompts") or []),
        "mode": "hard_rules",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
