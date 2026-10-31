#!/usr/bin/env python3
"""Validate execution-ready generation manifests."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def issue(severity: str, asset_id: str, message: str) -> dict[str, str]:
    return {"severity": severity, "asset_id": asset_id, "message": message}


def dependency_levels(entries: list[dict[str, Any]]) -> tuple[list[list[str]], list[str]]:
    by_id = {entry.get("asset_id"): entry for entry in entries if entry.get("asset_id")}
    pending = set(by_id)
    done: set[str] = set()
    levels: list[list[str]] = []
    problems: list[str] = []
    while pending:
        ready = []
        for asset_id in sorted(pending):
            deps = by_id[asset_id].get("input_asset_ids") or []
            unknown = [dep for dep in deps if dep not in by_id]
            if unknown:
                problems.extend(f"{asset_id} -> missing {dep}" for dep in unknown)
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


def generation_phase_for_entry(entry: dict[str, Any]) -> int:
    try:
        return int(entry.get("generation_phase") or 0)
    except (TypeError, ValueError):
        return 0


def generation_phase_groups(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[str]] = {}
    names: dict[int, str] = {}
    for entry in entries:
        phase = generation_phase_for_entry(entry)
        grouped.setdefault(phase, []).append(str(entry.get("asset_id") or ""))
        names[phase] = str(entry.get("generation_phase_name") or "")
    return [
        {"phase": phase, "name": names.get(phase, ""), "asset_ids": sorted(asset_ids)}
        for phase, asset_ids in sorted(grouped.items())
    ]


def local_path_is_safe(path: str) -> bool:
    if not path or path.startswith("/"):
        return False
    parts = Path(path).parts
    return ".." not in parts


def validate(manifest: dict[str, Any], *, require_paid_approval: bool) -> dict[str, Any]:
    entries = manifest.get("entries") or []
    findings: list[dict[str, str]] = []
    if require_paid_approval and not (manifest.get("execution_policy") or {}).get("paid_generation_allowed"):
        findings.append(issue("blocker", "__execution_policy__", "paid_generation_allowed must be true for execution."))
    if manifest.get("entry_count") not in {None, len(entries)}:
        findings.append(issue("major", "__manifest__", "entry_count does not match entries length."))
    asset_ids = [entry.get("asset_id") for entry in entries if entry.get("asset_id")]
    for asset_id, count in Counter(asset_ids).items():
        if count > 1:
            findings.append(issue("blocker", asset_id, "Duplicate asset_id in manifest."))
    by_id = {entry.get("asset_id"): entry for entry in entries if entry.get("asset_id")}
    for entry in entries:
        asset_id = entry.get("asset_id", "<missing>")
        asset_type = entry.get("asset_type", "")
        capability = entry.get("capability", "")
        provider = entry.get("provider", "")
        request = entry.get("request") or {}
        local_output_path = entry.get("local_output_path", "")
        deps = entry.get("input_asset_ids") or []
        generation_phase = generation_phase_for_entry(entry)
        if not local_path_is_safe(local_output_path):
            findings.append(issue("blocker", asset_id, f"Unsafe local_output_path: {local_output_path}"))
        if generation_phase <= 0:
            findings.append(issue("blocker", asset_id, "generation_phase must be a positive integer."))
        for dep in deps:
            if dep not in by_id:
                findings.append(issue("blocker", asset_id, f"Missing dependency asset: {dep}"))
                continue
            dep_phase = generation_phase_for_entry(by_id[dep])
            if dep_phase >= generation_phase:
                findings.append(issue("blocker", asset_id, f"Dependency {dep} must be in an earlier generation_phase."))
        if capability.startswith("image.") and provider != "gpt_image":
            findings.append(issue("blocker", asset_id, f"Image capability must use gpt_image provider, got {provider}."))
        if capability.startswith("video.") and provider != "volcengine_video":
            findings.append(issue("blocker", asset_id, f"Video capability must use volcengine_video provider, got {provider}."))
        if provider not in {"skip", ""}:
            if request.get("method") != "POST":
                findings.append(issue("major", asset_id, "Provider request method should be POST."))
            if not request.get("url"):
                findings.append(issue("blocker", asset_id, "Provider request URL is missing."))
        if asset_type == "character_expression_image":
            if capability != "image.reference_edit":
                findings.append(issue("blocker", asset_id, "Character expression must use image.reference_edit."))
            if not deps:
                findings.append(issue("blocker", asset_id, "Character expression must depend on a character reference."))
        if asset_type == "video_first_frame" and deps and capability != "image.reference_edit":
            findings.append(issue("blocker", asset_id, "Referenced video first frame must use image.reference_edit."))
        if asset_type == "video_clip":
            if capability != "video.first_frame_to_video":
                findings.append(issue("blocker", asset_id, "Video clip must use video.first_frame_to_video."))
            if not deps:
                findings.append(issue("blocker", asset_id, "Video clip must depend on first-frame asset."))
            params = entry.get("model_parameters") or {}
            duration = params.get("duration", params.get("duration_sec"))
            try:
                if duration is not None and int(duration) <= 0:
                    findings.append(issue("major", asset_id, "Video duration must be positive."))
            except (TypeError, ValueError):
                findings.append(issue("major", asset_id, "Video duration must be numeric when present."))
    levels, dependency_problems = dependency_levels(entries)
    for problem in dependency_problems:
        findings.append(issue("blocker", "__dependency_graph__", problem))
    blockers = sum(1 for item in findings if item["severity"] == "blocker")
    majors = sum(1 for item in findings if item["severity"] == "major")
    return {
        "status": "failed" if blockers or majors else "passed",
        "entry_count": len(entries),
        "blockers": blockers,
        "majors": majors,
        "findings": findings,
        "dependency_levels": [{"level": index + 1, "asset_ids": level} for index, level in enumerate(levels)],
        "generation_phases": generation_phase_groups(entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generation manifest execution readiness")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-paid-approval", action="store_true")
    args = parser.parse_args()
    report = validate(load_json(args.manifest), require_paid_approval=args.require_paid_approval)
    if args.report:
        write_json(args.report, report)
    print(json.dumps({k: report[k] for k in ["status", "entry_count", "blockers", "majors"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
