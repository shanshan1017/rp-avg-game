#!/usr/bin/env python3
"""Validate Art Agent asset planning rules before prompt hardening/execution.

This validator checks the agent-authored planning artifact itself. The prompt
hardener may add defensive execution details later, but it should not be the
only place where character references, edit dependencies, cutout policies, and
video first-frame rules exist.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


CHARACTER_TYPES = {"character_reference_image", "character_expression_image", "character_pose_image"}
CHARACTER_VARIANT_TYPES = {"character_expression_image", "character_pose_image"}
SCENE_WORDS_FOR_SPRITES = [
    "云海",
    "擂台",
    "看台",
    "内堂",
    "高台",
    "室内",
    "石阶",
    "山门",
    "山水背景",
    "场景背景",
]
TEXT_INVITE_WORDS = [
    "简体中文",
    "可读文字",
    "中文标题",
    "显示'",
    "显示“",
    "标注",
    "标签",
    "状态值",
    "代价短句",
]
NO_TEXT_TERMS = ["无可读文字", "不要任何可读文字", "不要生成可读文字", "不要生成任何可读文字", "禁止任何可读文字", "no readable text"]
CUTOUT_POLICIES = {"chroma_key_green_cutout", "transparent_cutout"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue(severity: str, asset_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "asset_id": asset_id, "message": message}


def prompt_text(asset: dict[str, Any]) -> str:
    return " ".join(
        str(part or "")
        for part in [
            asset.get("prompt_intent"),
            asset.get("prompt"),
            asset.get("negative_prompt"),
            " ".join(asset.get("must_not_include") or []),
        ]
    )


def positive_prompt_text(asset: dict[str, Any]) -> str:
    return " ".join(str(part or "") for part in [asset.get("prompt_intent"), asset.get("prompt")])


def has_cutout_policy(asset: dict[str, Any]) -> bool:
    params = asset.get("model_parameters") or {}
    chroma = params.get("chroma_key") or {}
    text = prompt_text(asset).lower()
    return (
        params.get("background_policy") in CUTOUT_POLICIES
        or chroma.get("enabled") is True
        or "#00ff00" in text
        or "绿幕" in text
        or "透明" in text
        or "transparent" in text
        or "chroma" in text
    )


def has_no_text_guard(asset: dict[str, Any]) -> bool:
    text = prompt_text(asset).lower()
    return any(term.lower() in text for term in NO_TEXT_TERMS)


def has_text_invitation(asset: dict[str, Any]) -> bool:
    text = positive_prompt_text(asset)
    if "可读文字" in text and not has_no_text_guard(asset):
        return True
    return any(word in text for word in TEXT_INVITE_WORDS if word != "可读文字")


def safe_local_path(path: str | None) -> bool:
    if path in {None, ""}:
        return False
    target = Path(path)
    return not target.is_absolute() and ".." not in target.parts


def dependency_levels(assets: list[dict[str, Any]]) -> tuple[list[list[str]], list[str]]:
    by_id = {asset.get("asset_id"): asset for asset in assets if asset.get("asset_id")}
    pending = set(by_id)
    done: set[str] = set()
    levels: list[list[str]] = []
    problems: list[str] = []
    while pending:
        ready: list[str] = []
        for asset_id in sorted(pending):
            deps = by_id[asset_id].get("input_asset_ids") or []
            missing = [dep for dep in deps if dep not in by_id]
            if missing:
                problems.extend(f"{asset_id} -> {dep}" for dep in missing)
                continue
            if all(dep in done for dep in deps):
                ready.append(asset_id)
        if not ready:
            problems.extend(f"cycle_or_unresolved:{asset_id}" for asset_id in sorted(pending))
            break
        levels.append(ready)
        done.update(ready)
        pending.difference_update(ready)
    return levels, problems


def validate_prompt_pack_consistency(
    assets_by_id: dict[str, dict[str, Any]],
    prompt_pack: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if not prompt_pack:
        return []
    findings: list[dict[str, str]] = []
    prompts = prompt_pack.get("prompts") or []
    prompts_by_id = {prompt.get("asset_id"): prompt for prompt in prompts if prompt.get("asset_id")}
    for asset_id, asset in assets_by_id.items():
        prompt = prompts_by_id.get(asset_id)
        if not prompt:
            findings.append(issue("major", asset_id, "Asset plan entry has no matching prompt_pack prompt."))
            continue
        for key in ["asset_type", "capability"]:
            if asset.get(key) != prompt.get(key):
                findings.append(issue("blocker", asset_id, f"asset_plan.{key} differs from prompt_pack.{key}."))
        asset_deps = asset.get("input_asset_ids") or []
        prompt_deps = prompt.get("input_asset_ids") or []
        if asset_deps != prompt_deps:
            findings.append(issue("blocker", asset_id, "asset_plan.input_asset_ids differs from prompt_pack.input_asset_ids."))
        asset_runtime = asset.get("runtime_usage") or {}
        prompt_runtime = prompt.get("expected_runtime_use") or {}
        if asset_runtime.get("is_used_by_runtime") != prompt_runtime.get("is_used_by_runtime"):
            findings.append(issue("major", asset_id, "Runtime usage flag differs between asset_plan and prompt_pack."))
    for asset_id in prompts_by_id:
        if asset_id not in assets_by_id:
            findings.append(issue("major", asset_id, "prompt_pack prompt has no matching asset_plan entry."))
    return findings


def validate_asset_plan(data: dict[str, Any], prompt_pack: dict[str, Any] | None = None) -> dict[str, Any]:
    assets = data.get("assets") or []
    findings: list[dict[str, str]] = []
    asset_ids = [asset.get("asset_id") for asset in assets if asset.get("asset_id")]
    duplicates = [asset_id for asset_id, count in Counter(asset_ids).items() if count > 1]
    for asset_id in duplicates:
        findings.append(issue("blocker", asset_id, "Duplicate asset_id in asset plan."))

    by_id = {asset.get("asset_id"): asset for asset in assets if asset.get("asset_id")}
    ref_by_character: dict[str, str] = {}
    for asset in assets:
        if asset.get("asset_type") == "character_reference_image":
            chars = asset.get("character_ids") or []
            if len(chars) == 1:
                ref_by_character[chars[0]] = asset.get("asset_id", "")

    for asset in assets:
        asset_id = asset.get("asset_id", "<missing>")
        asset_type = asset.get("asset_type", "")
        capability = asset.get("capability", "")
        deps = asset.get("input_asset_ids") or []
        chars = asset.get("character_ids") or []
        runtime_usage = asset.get("runtime_usage") or {}

        if not safe_local_path(asset.get("local_output_path")) and capability not in {"skip", "manual.import"}:
            findings.append(issue("blocker", asset_id, "local_output_path must be a safe relative path."))

        for dep in deps:
            if dep not in by_id:
                findings.append(issue("blocker", asset_id, f"input_asset_id does not exist: {dep}"))

        if runtime_usage.get("is_used_by_runtime"):
            if not runtime_usage.get("runtime_field"):
                findings.append(issue("major", asset_id, "Runtime-used asset must name runtime_usage.runtime_field."))
            if not runtime_usage.get("display_context"):
                findings.append(issue("major", asset_id, "Runtime-used asset must name runtime_usage.display_context."))
            if asset_type not in {"character_reference_image", "ui_concept_image", "ui_image"} and not (asset.get("node_id") or asset.get("story_unit_id")):
                findings.append(issue("major", asset_id, "Runtime-used non-global asset should name node_id or story_unit_id."))

        if asset_type == "character_reference_image":
            if capability != "image.text_to_image":
                findings.append(issue("blocker", asset_id, "Character reference must use image.text_to_image."))
            if deps:
                findings.append(issue("blocker", asset_id, "Character reference must not have input_asset_ids."))
            if not chars:
                findings.append(issue("blocker", asset_id, "Character reference must list character_ids."))
            if not has_cutout_policy(asset):
                findings.append(issue("major", asset_id, "Character reference must declare transparent/chroma-key cutout policy."))
            if not has_no_text_guard(asset):
                findings.append(issue("major", asset_id, "Character reference must explicitly forbid readable text."))

        if asset_type in CHARACTER_VARIANT_TYPES:
            if capability != "image.reference_edit":
                findings.append(issue("blocker", asset_id, "Character expression/pose variant must use image.reference_edit."))
            if not deps:
                findings.append(issue("blocker", asset_id, "Character expression/pose variant must reference an approved character asset."))
            for character_id in chars:
                expected_ref = ref_by_character.get(character_id)
                if expected_ref and expected_ref not in deps:
                    findings.append(issue("blocker", asset_id, f"Character variant must depend on {expected_ref}."))
            if not has_cutout_policy(asset):
                findings.append(issue("major", asset_id, "Character expression/pose variant must declare transparent/chroma-key cutout policy."))
            if not has_no_text_guard(asset):
                findings.append(issue("major", asset_id, "Character expression/pose variant must explicitly forbid readable text."))
            text = positive_prompt_text(asset)
            leaked = [word for word in SCENE_WORDS_FOR_SPRITES if word in text]
            if leaked:
                findings.append(issue("major", asset_id, f"Character sprite prompt contains scene/background terms: {', '.join(leaked)}"))

        if asset_type == "story_background" and chars:
            findings.append(issue("major", asset_id, "story_background should not include character_ids; use story_still/CG when characters are baked in."))

        if asset_type == "story_still" and chars:
            if capability != "image.reference_edit":
                findings.append(issue("major", asset_id, "Story still with recurring characters should use image.reference_edit."))
            for character_id in chars:
                expected_ref = ref_by_character.get(character_id)
                if expected_ref and expected_ref not in deps:
                    findings.append(issue("major", asset_id, f"Story still should depend on {expected_ref}."))

        if asset_type == "video_first_frame" and chars:
            if capability != "image.reference_edit":
                findings.append(issue("blocker", asset_id, "Character video first frame must use image.reference_edit."))
            if not deps:
                findings.append(issue("blocker", asset_id, "Character video first frame must reference character image assets."))
            for character_id in chars:
                expected_ref = ref_by_character.get(character_id)
                if expected_ref and expected_ref not in deps:
                    findings.append(issue("blocker", asset_id, f"Character video first frame must depend on {expected_ref}."))

        if asset_type == "video_clip":
            if capability != "video.first_frame_to_video":
                findings.append(issue("blocker", asset_id, "Video clip must use video.first_frame_to_video."))
            if not deps:
                findings.append(issue("blocker", asset_id, "Video clip must depend on an approved first-frame asset."))
            for dep in deps:
                dep_type = (by_id.get(dep) or {}).get("asset_type")
                if dep_type != "video_first_frame":
                    findings.append(issue("major", asset_id, f"Video clip dependency is not a video_first_frame: {dep}"))

        if asset_type in {"ui_concept_image", "ui_image"} and has_text_invitation(asset):
            findings.append(issue("major", asset_id, "UI concept/image prompt invites generated readable text; runtime DOM should render text."))

    levels, dependency_issues = dependency_levels(assets)
    for item in dependency_issues:
        findings.append(issue("blocker", "__dependency_graph__", item))

    findings.extend(validate_prompt_pack_consistency(by_id, prompt_pack))

    blocker_count = sum(1 for item in findings if item["severity"] == "blocker")
    major_count = sum(1 for item in findings if item["severity"] == "major")
    return {
        "status": "failed" if blocker_count or major_count else "passed",
        "project_id": data.get("project_id"),
        "asset_count": len(assets),
        "blockers": blocker_count,
        "majors": major_count,
        "findings": findings,
        "dependency_levels": [{"level": index + 1, "asset_ids": level} for index, level in enumerate(levels)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Art Agent media asset plan policy")
    parser.add_argument("--asset-plan", type=Path, required=True)
    parser.add_argument("--prompt-pack", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    prompt_pack = load_json(args.prompt_pack) if args.prompt_pack and args.prompt_pack.exists() else None
    report = validate_asset_plan(load_json(args.asset_plan), prompt_pack)
    if args.report:
        write_json(args.report, report)
    print(json.dumps({k: report[k] for k in ["status", "asset_count", "blockers", "majors"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
