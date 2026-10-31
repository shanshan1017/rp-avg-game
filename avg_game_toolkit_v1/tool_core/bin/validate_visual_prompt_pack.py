#!/usr/bin/env python3
"""Validate hard AVG visual prompt-pack rules before manifest execution."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


CHARACTER_TYPES = {"character_reference_image", "character_expression_image"}
TEXT_FORBIDDEN_HINTS = ["可读文字为简体中文", "中文书法", "角色名标签", "字幕", "水印"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue(severity: str, asset_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "asset_id": asset_id, "message": message}


def has_chroma_or_transparency(prompt: dict[str, Any]) -> bool:
    params = prompt.get("model_parameters") or {}
    chroma = params.get("chroma_key") or {}
    text = " ".join(
        str(part)
        for part in [
            params.get("background_policy", ""),
            prompt.get("prompt", ""),
            prompt.get("negative_prompt", ""),
        ]
    )
    return (
        params.get("background_policy") == "chroma_key_green_cutout"
        or chroma.get("enabled") is True
        or "#00FF00" in text
        or "透明" in text
        or "transparent" in text.lower()
    )


def dependency_levels(prompts: list[dict[str, Any]]) -> tuple[list[list[str]], list[str]]:
    by_id = {prompt.get("asset_id"): prompt for prompt in prompts if prompt.get("asset_id")}
    pending = set(by_id)
    done: set[str] = set()
    levels: list[list[str]] = []
    missing: list[str] = []
    while pending:
        ready = []
        for asset_id in sorted(pending):
            deps = by_id[asset_id].get("input_asset_ids") or []
            unknown = [dep for dep in deps if dep not in by_id]
            if unknown:
                missing.extend(f"{asset_id} -> {dep}" for dep in unknown)
                continue
            if all(dep in done for dep in deps):
                ready.append(asset_id)
        if not ready:
            missing.extend(f"cycle_or_unresolved:{asset_id}" for asset_id in sorted(pending))
            break
        levels.append(ready)
        done.update(ready)
        pending.difference_update(ready)
    return levels, missing


def validate(data: dict[str, Any]) -> dict[str, Any]:
    prompts = data.get("prompts") or []
    findings: list[dict[str, str]] = []
    asset_ids = [prompt.get("asset_id") for prompt in prompts if prompt.get("asset_id")]
    duplicates = [asset_id for asset_id, count in Counter(asset_ids).items() if count > 1]
    for asset_id in duplicates:
        findings.append(issue("blocker", asset_id, "Duplicate asset_id in prompt pack."))

    by_id = {prompt.get("asset_id"): prompt for prompt in prompts if prompt.get("asset_id")}
    style_text = json.dumps(data.get("global_style_bible") or {}, ensure_ascii=False)
    if "所有可读文字为简体中文" in style_text:
        findings.append(issue("major", "__global_style_bible__", "Global style asks generated images to contain readable Chinese text."))

    for prompt in prompts:
        asset_id = prompt.get("asset_id", "<missing>")
        asset_type = prompt.get("asset_type", "")
        capability = prompt.get("capability", "")
        deps = prompt.get("input_asset_ids") or []
        prompt_text = (prompt.get("prompt") or "") + "\n" + (prompt.get("negative_prompt") or "")

        for dep in deps:
            if dep not in by_id:
                findings.append(issue("blocker", asset_id, f"input_asset_id does not exist: {dep}"))

        if asset_type == "character_reference_image":
            if capability != "image.text_to_image":
                findings.append(issue("blocker", asset_id, "Character reference must use image.text_to_image."))
            if not has_chroma_or_transparency(prompt):
                findings.append(issue("major", asset_id, "Character reference is not marked as chroma-key or transparent cutout-ready."))

        if asset_type == "character_expression_image":
            if capability != "image.reference_edit":
                findings.append(issue("blocker", asset_id, "Character expression must use image.reference_edit."))
            if not deps:
                findings.append(issue("blocker", asset_id, "Character expression must include input_asset_ids pointing to a reference asset."))
            if not has_chroma_or_transparency(prompt):
                findings.append(issue("major", asset_id, "Character expression is not marked as chroma-key or transparent cutout-ready."))

        if asset_type in CHARACTER_TYPES:
            for forbidden in TEXT_FORBIDDEN_HINTS:
                if forbidden in prompt_text and "Must not" not in prompt_text and "不要" not in prompt_text:
                    findings.append(issue("minor", asset_id, f"Character prompt may invite readable text: {forbidden}"))

        if asset_type == "video_first_frame" and deps and capability != "image.reference_edit":
            findings.append(issue("blocker", asset_id, "Character video first frame with references must use image.reference_edit."))

        if asset_type == "video_clip":
            if capability != "video.first_frame_to_video":
                findings.append(issue("blocker", asset_id, "Video clips must use video.first_frame_to_video."))
            if not deps:
                findings.append(issue("blocker", asset_id, "Video clips must depend on a first-frame asset through input_asset_ids."))

    levels, dependency_issues = dependency_levels(prompts)
    for item in dependency_issues:
        findings.append(issue("blocker", "__dependency_graph__", item))

    blocker_count = sum(1 for item in findings if item["severity"] == "blocker")
    major_count = sum(1 for item in findings if item["severity"] == "major")
    return {
        "status": "failed" if blocker_count or major_count else "passed",
        "prompt_count": len(prompts),
        "blockers": blocker_count,
        "majors": major_count,
        "findings": findings,
        "dependency_levels": [{"level": index + 1, "asset_ids": level} for index, level in enumerate(levels)],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate hardened AVG visual prompt-pack rules")
    parser.add_argument("--prompt-pack", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(load_json(args.prompt_pack))
    if args.report:
        write_json(args.report, report)
    print(json.dumps({k: report[k] for k in ["status", "prompt_count", "blockers", "majors"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
