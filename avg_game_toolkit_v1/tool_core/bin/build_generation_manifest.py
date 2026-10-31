#!/usr/bin/env python3
"""Build a sanitized provider generation manifest from prompt_pack.json.

This is a dry planning step. It does not call paid APIs. The output records the
exact provider request shape that an execution layer may later submit after
Planner/user approval.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from providers import gpt_image, minimax_audio, volcengine_video  # noqa: E402


GENERATION_PHASES: dict[int, str] = {
    10: "character_reference_lock",
    20: "independent_scene_prop_ui_assets",
    30: "character_reference_edits",
    40: "cg_and_video_first_frames",
    50: "video_clips",
    60: "audio_assets",
    90: "other_assets",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def request_for_prompt(prompt_item: dict[str, Any], global_style: str) -> tuple[str, dict[str, Any]]:
    capability = prompt_item.get("capability", "")
    if capability.startswith("image."):
        return "gpt_image", gpt_image.build_request(prompt_item, global_style)
    if capability.startswith("video."):
        return "volcengine_video", volcengine_video.build_request(prompt_item, global_style)
    if capability.startswith("audio."):
        return "minimax_audio", minimax_audio.build_request(prompt_item)
    return "skip", {
        "method": "SKIP",
        "url": "",
        "headers": {},
        "payload": {
            "reason": f"Capability '{capability}' does not require generation.",
            "prompt": prompt_item.get("prompt", ""),
        },
    }


def generation_phase_for_prompt(prompt_item: dict[str, Any]) -> tuple[int, str]:
    asset_type = prompt_item.get("asset_type", "")
    capability = prompt_item.get("capability", "")
    if asset_type == "character_reference_image":
        phase = 10
    elif asset_type in {"story_background", "location_reference_image", "prop_reference_image", "ui_image", "ui_concept_image"}:
        phase = 20
    elif asset_type in {"character_expression_image", "character_pose_image"}:
        phase = 30
    elif asset_type in {"story_still", "node_poster", "video_first_frame", "tail_frame"}:
        phase = 40
    elif asset_type in {"video_clip", "node_video"} or capability.startswith("video."):
        phase = 50
    elif capability.startswith("audio."):
        phase = 60
    else:
        phase = 90
    return phase, GENERATION_PHASES[phase]


def categorized_output_path(prompt_item: dict[str, Any], asset_root: str) -> str:
    asset_type = prompt_item.get("asset_type", "")
    capability = prompt_item.get("capability", "")
    if asset_type in {"character_reference_image", "character_expression_image", "character_pose_image"}:
        folder = "characters"
        ext = ".png"
    elif asset_type in {"story_background", "location_reference_image"}:
        folder = "backgrounds"
        ext = ".png"
    elif asset_type == "prop_reference_image":
        folder = "props"
        ext = ".png"
    elif asset_type in {"story_still", "node_poster"}:
        folder = "cgs"
        ext = ".png"
    elif asset_type in {"ui_image", "ui_concept_image"}:
        folder = "ui_concepts"
        ext = ".png"
    elif asset_type == "video_first_frame":
        folder = "video"
        ext = ".png"
    elif asset_type in {"video_clip", "node_video"} or capability.startswith("video."):
        folder = "video"
        ext = ".mp4"
    elif capability in {"audio.tts", "audio.voice_design", "audio.music_generation"}:
        folder = "audio"
        ext = ".mp3"
    elif capability == "skip":
        folder = "skipped"
        ext = ".skip"
    else:
        folder = "images"
        ext = ".png"
    return f"{asset_root.rstrip('/')}/{folder}/{prompt_item['asset_id']}{ext}"


def output_path_for_prompt(prompt_item: dict[str, Any], asset_root: str, asset_paths: dict[str, str] | None = None) -> str:
    params = prompt_item.get("model_parameters") or {}
    if params.get("local_output_path"):
        return params["local_output_path"]
    if asset_paths and asset_paths.get(prompt_item["asset_id"]):
        return asset_paths[prompt_item["asset_id"]]
    asset_id = prompt_item["asset_id"]
    capability = prompt_item.get("capability", "")
    if capability.startswith("video."):
        ext = ".mp4"
        folder = "videos"
    elif capability in {"audio.tts", "audio.voice_design", "audio.music_generation"}:
        ext = ".mp3"
        folder = "audio"
    elif capability == "skip":
        ext = ".skip"
        folder = "skipped"
    else:
        ext = ".png"
        folder = "images"
    return categorized_output_path(prompt_item, asset_root) if folder == "images" and ext == ".png" else f"{asset_root.rstrip('/')}/{folder}/{asset_id}{ext}"


def asset_paths_from_plan(asset_plan: dict[str, Any] | None) -> dict[str, str]:
    if not asset_plan:
        return {}
    return {
        asset["asset_id"]: asset["local_output_path"]
        for asset in asset_plan.get("assets", [])
        if asset.get("asset_id") and asset.get("local_output_path")
    }


def build_manifest(prompt_pack: dict[str, Any], asset_root: str, asset_plan: dict[str, Any] | None = None) -> dict[str, Any]:
    style = prompt_pack.get("global_style_bible") or {}
    global_style = "\n".join(
        part
        for part in [
            style.get("style_summary", ""),
            "Must include: " + "; ".join(style.get("must_include") or []),
            "Must not include: " + "; ".join(style.get("must_not_include") or []),
        ]
        if part and part.strip()
    )
    entries = []
    asset_paths = asset_paths_from_plan(asset_plan)
    for prompt_item in prompt_pack.get("prompts") or []:
        provider, request = request_for_prompt(prompt_item, global_style)
        generation_phase, generation_phase_name = generation_phase_for_prompt(prompt_item)
        entries.append(
            {
                "prompt_id": prompt_item["prompt_id"],
                "asset_id": prompt_item["asset_id"],
                "discipline": prompt_item["discipline"],
                "asset_type": prompt_item.get("asset_type"),
                "capability": prompt_item["capability"],
                "provider": provider,
                "source_unit_ids": prompt_item.get("source_unit_ids") or [],
                "source_character_ids": prompt_item.get("source_character_ids") or [],
                "input_asset_ids": prompt_item.get("input_asset_ids") or [],
                "expected_runtime_use": prompt_item.get("expected_runtime_use") or {},
                "model_parameters": prompt_item.get("model_parameters") or {},
                "generation_phase": generation_phase,
                "generation_phase_name": generation_phase_name,
                "local_output_path": output_path_for_prompt(prompt_item, asset_root, asset_paths),
                "status": "planned",
                "request": request,
            }
        )
    return {
        "project_id": prompt_pack["project_id"],
        "manifest_version": "0.1.0",
        "execution_policy": {
            "paid_generation_allowed": False,
            "this_file_is_safe_to_commit": True,
            "secrets_policy": "Secrets must be read from environment variables only during a later execution step.",
            "generation_order_policy": "Execute in generation_phase order; do not flatten all no-dependency assets into one provider batch.",
            "generation_phases": [{"phase": phase, "name": name} for phase, name in GENERATION_PHASES.items()],
        },
        "entry_count": len(entries),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sanitized media generation manifest from prompt_pack.json")
    parser.add_argument("--prompt-pack", type=Path, required=True)
    parser.add_argument("--asset-plan", type=Path, help="Optional asset_plan.json. local_output_path values win over generic category defaults.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--asset-root", default="assets")
    args = parser.parse_args()

    prompt_pack = load_json(args.prompt_pack)
    asset_plan = load_json(args.asset_plan) if args.asset_plan and args.asset_plan.exists() else None
    manifest = build_manifest(prompt_pack, args.asset_root, asset_plan)
    write_json(args.output, manifest)
    print(json.dumps({
        "project_id": manifest["project_id"],
        "entry_count": manifest["entry_count"],
        "output": str(args.output),
        "paid_generation_allowed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
