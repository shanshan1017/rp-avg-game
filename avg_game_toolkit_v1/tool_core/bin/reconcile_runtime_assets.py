#!/usr/bin/env python3
"""Bind generated manifest assets into a runtime_game_package.

Generation can produce canonical assets while the runtime package still
contains semantic aliases, for example `char_lu_xueqi_after_duel_wait` pointing
at the same generated image as `char_lu_xueqi_understanding_close`. This pass
keeps those aliases but rewrites their paths from placeholders or old flat
folders to the manifest's categorized local output paths.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def manifest_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("entries")
    if isinstance(entries, list):
        return entries
    if isinstance(manifest, list):
        return manifest
    raise ValueError("Generation manifest must contain an entries array.")


def infer_type(entry: dict[str, Any], relative_path: str) -> str:
    suffix = Path(relative_path).suffix.lower()
    if suffix in {".mp4", ".webm", ".mov"}:
        return "video"
    if (entry.get("asset_type") or "").startswith("ui_") or entry.get("discipline") == "ui":
        return "ui"
    return "image"


def infer_usage(entry: dict[str, Any]) -> list[str]:
    asset_type = entry.get("asset_type") or ""
    field = ((entry.get("expected_runtime_use") or {}).get("runtime_field") or "").strip()
    if asset_type == "character_reference_image":
        return ["character_portrait"]
    if asset_type == "character_expression_image":
        return ["character_expression"]
    if asset_type == "story_background":
        return ["background"]
    if asset_type == "prop_reference_image":
        return ["prop"]
    if asset_type == "story_still":
        return ["story_still"]
    if asset_type == "video_first_frame":
        return ["story_still", "video_first_frame"]
    if asset_type == "video_clip":
        return ["video_clip"]
    if asset_type == "ui_concept_image":
        return ["ui_concept"]
    return [field] if field else ["generated_asset"]


def relative_to_asset_root(local_output_path: str, asset_root: Path, project_root: Path) -> tuple[str, Path] | tuple[None, Path]:
    raw_path = Path(local_output_path)
    absolute = raw_path if raw_path.is_absolute() else project_root / raw_path
    absolute = absolute.resolve()
    try:
        return str(absolute.relative_to(asset_root.resolve())), absolute
    except ValueError:
        return None, absolute


def collect_targets(assets: dict[str, Any], entry: dict[str, Any]) -> list[tuple[str, dict[str, Any], bool]]:
    asset_id = entry.get("asset_id")
    prompt_id = entry.get("prompt_id")
    targets: list[tuple[str, dict[str, Any], bool]] = []
    seen: set[str] = set()
    if asset_id in assets:
        targets.append((asset_id, assets[asset_id], False))
        seen.add(asset_id)
    if prompt_id:
        for runtime_asset_id, asset in assets.items():
            if runtime_asset_id in seen:
                continue
            if asset.get("source_manifest_id") == prompt_id:
                targets.append((runtime_asset_id, asset, runtime_asset_id != asset_id))
                seen.add(runtime_asset_id)
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile generated manifest assets into a runtime package")
    parser.add_argument("--runtime-package", type=Path, required=True)
    parser.add_argument("--generation-manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview-copy", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--add-manifest-assets", action="store_true")
    args = parser.parse_args()

    package = load_json(args.runtime_package)
    manifest = load_json(args.generation_manifest)
    assets = package.setdefault("assets", {})
    base = ((package.get("engine_contract") or {}).get("asset_base_path") or "").strip()
    asset_root = ((args.runtime_package.parent / base).resolve() if base else args.project_root.resolve())

    changed = 0
    added = 0
    alias_updates = 0
    missing_outputs: list[dict[str, str]] = []
    updated_assets: list[dict[str, str]] = []
    for entry in manifest_entries(manifest):
        asset_id = entry.get("asset_id")
        local_output_path = entry.get("local_output_path")
        if not asset_id or not local_output_path:
            continue
        relative, absolute = relative_to_asset_root(local_output_path, asset_root, args.project_root)
        if not relative or not absolute.exists():
            missing_outputs.append({
                "asset_id": str(asset_id),
                "prompt_id": str(entry.get("prompt_id") or ""),
                "expected_path": str(absolute),
            })
            continue

        targets = collect_targets(assets, entry)
        if not targets and args.add_manifest_assets:
            assets[asset_id] = {
                "asset_id": asset_id,
                "type": infer_type(entry, relative),
                "path": relative,
                "usage": infer_usage(entry),
                "required": False,
                "alt_text": str(asset_id).replace("_", " "),
                "source_manifest_id": entry.get("prompt_id"),
                "width": None,
                "height": None,
                "duration_sec": None,
            }
            added += 1
            changed += 1
            updated_assets.append({"asset_id": str(asset_id), "path": relative, "mode": "added"})
            continue

        for runtime_asset_id, asset, is_alias in targets:
            before = dict(asset)
            asset["path"] = relative
            asset["source_manifest_id"] = entry.get("prompt_id")
            asset["type"] = infer_type(entry, relative) if asset.get("type") in {None, "image", "video", "ui"} else asset.get("type")
            asset.setdefault("usage", infer_usage(entry))
            asset.setdefault("required", False)
            asset.setdefault("alt_text", runtime_asset_id.replace("_", " "))
            asset.setdefault("width", None)
            asset.setdefault("height", None)
            asset.setdefault("duration_sec", None)
            asset.pop("alias_of", None)
            if is_alias:
                alias_updates += 1
            if asset != before:
                changed += 1
                item = {"asset_id": runtime_asset_id, "path": relative, "mode": "alias" if is_alias else "direct"}
                if is_alias:
                    item["canonical_asset_id"] = str(asset_id)
                updated_assets.append(item)

    package.setdefault("meta", {}).pop("runtime_asset_patch", None)
    patch_summary = {
        "patched_at": datetime.now(timezone.utc).isoformat(),
        "generation_manifest": str(args.generation_manifest),
        "asset_root": str(asset_root),
        "changed_assets": changed,
        "added_manifest_assets": added,
        "alias_updates": alias_updates,
        "missing_outputs": len(missing_outputs),
    }
    write_json(args.output, package)
    if args.preview_copy:
        args.preview_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.output, args.preview_copy)
    write_json(args.report, {
        "runtime_package": str(args.output),
        "generation_manifest": str(args.generation_manifest),
        "asset_root": str(asset_root),
        "changed_assets": changed,
        "added_manifest_assets": added,
        "alias_updates": alias_updates,
        "patch_summary": patch_summary,
        "missing_outputs": missing_outputs,
        "updated_assets": updated_assets,
    })
    print(json.dumps({
        "changed_assets": changed,
        "added_manifest_assets": added,
        "alias_updates": alias_updates,
        "missing_outputs": len(missing_outputs),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
