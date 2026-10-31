#!/usr/bin/env python3
"""Post-compile enrichment for runtime_game_package.json.

The compiler intentionally stays simple. This pass imports cross-disciplinary
metadata that agents already authored: character/world bible, mechanics flags,
chapters, achievements, primary value, and final ending gate routing.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def choice_by_id(package: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for node in (package.get("nodes") or {}).values():
        for choice in node.get("choices") or []:
            result[choice.get("choice_id", "")] = choice
    return result


def ensure_changes(choice: dict[str, Any]) -> dict[str, Any]:
    changes = choice.setdefault("changes", {})
    if changes is None:
        changes = {}
        choice["changes"] = changes
    return changes


def merge_flags(choice: dict[str, Any], flags: list[str]) -> None:
    if not flags:
        return
    changes = ensure_changes(choice)
    current = list(changes.get("add_flags") or [])
    for flag in flags:
        if flag not in current:
            current.append(flag)
    changes["add_flags"] = current


def merge_state_changes(choice: dict[str, Any], state_changes: dict[str, Any]) -> None:
    if not state_changes:
        return
    changes = ensure_changes(choice)
    values_delta = dict(changes.get("values_delta") or {})
    values_delta.update(state_changes.get("values_delta") or {})
    if values_delta:
        changes["values_delta"] = values_delta
    if "primary_value_delta" in state_changes:
        changes["primary_value_delta"] = state_changes["primary_value_delta"]
    if "primary_value_set" in state_changes:
        changes["primary_value_set"] = state_changes["primary_value_set"]
    if "set_variables" in state_changes:
        variables = dict(changes.get("set_variables") or {})
        variables.update(state_changes.get("set_variables") or {})
        changes["set_variables"] = variables


def convert_primary_value_deltas(package: dict[str, Any], primary_id: str) -> None:
    if not primary_id:
        return
    for node in (package.get("nodes") or {}).values():
        for choice in node.get("choices") or []:
            changes = ensure_changes(choice)
            values_delta = changes.get("values_delta") or {}
            if primary_id not in values_delta:
                continue
            changes["primary_value_delta"] = changes.get("primary_value_delta", 0) + values_delta[primary_id]
            del values_delta[primary_id]
            if values_delta:
                changes["values_delta"] = values_delta
            else:
                changes.pop("values_delta", None)


def enrich_characters(package: dict[str, Any], character_world: dict[str, Any]) -> int:
    assets = set((package.get("assets") or {}).keys())
    by_id = {item.get("character_id"): item for item in character_world.get("characters") or []}
    changed = 0
    for char_id, character in (package.get("characters") or {}).items():
        source = by_id.get(char_id)
        if not source:
            continue
        for key, value in [
            ("display_name", source.get("display_name")),
            ("role", source.get("role")),
            ("player_visible_profile", source.get("public_profile")),
            ("speech_style", source.get("speech_style")),
        ]:
            if value and character.get(key) != value:
                character[key] = value
                changed += 1
        portraits = list(character.get("portraits") or [])
        seen = {(item.get("expression"), item.get("asset_id")) for item in portraits}
        for need in source.get("expression_needs") or []:
            asset_id = need.get("asset_slot")
            expression = need.get("expression")
            if asset_id in assets and (expression, asset_id) not in seen:
                portraits.append({"expression": expression, "asset_id": asset_id, "pose": "standing"})
                seen.add((expression, asset_id))
                changed += 1
        if portraits:
            character["portraits"] = portraits
    return changed


def enrich_scenes(package: dict[str, Any], character_world: dict[str, Any]) -> int:
    by_id = {item.get("location_id"): item for item in character_world.get("locations") or []}
    changed = 0
    for scene_id, scene in (package.get("scenes") or {}).items():
        source = by_id.get(scene_id)
        if not source:
            continue
        updates = {
            "name": source.get("display_name"),
            "description": source.get("narrative_function"),
            "ambient": source.get("ambient_direction"),
        }
        for key, value in updates.items():
            if value and scene.get(key) != value:
                scene[key] = value
                changed += 1
    for node in (package.get("nodes") or {}).values():
        scene = (package.get("scenes") or {}).get(node.get("scene_id"))
        if scene and not node.get("background_asset_id") and scene.get("background_asset_id"):
            node["background_asset_id"] = scene["background_asset_id"]
            changed += 1
    return changed


def enrich_mechanics(package: dict[str, Any], mechanics: dict[str, Any]) -> int:
    changed = 0
    state_table = mechanics.get("state_table") or {}
    primary = state_table.get("primary_value") or {}
    if primary:
        package.setdefault("state", {})["primary_value"] = primary
        package["state"].setdefault("values", {}).pop(primary.get("id"), None)
        convert_primary_value_deltas(package, primary.get("id", ""))
        changed += 1
    if state_table.get("variables"):
        variables = package.setdefault("state", {}).setdefault("variables", {})
        for key, value in state_table["variables"].items():
            if key not in variables:
                variables[key] = value
                changed += 1

    if mechanics.get("achievement_definitions"):
        package["achievements"] = {
            item["achievement_id"]: {
                "title": item.get("title", item["achievement_id"]),
                "description": item.get("description", ""),
            }
            for item in mechanics["achievement_definitions"]
        }
        changed += 1
    if mechanics.get("chapter_definitions"):
        package["chapters"] = [
            {
                "chapter_id": item["chapter_id"],
                "title": item["title"],
                "entry_node_id": item["entry_node_id"],
            }
            for item in mechanics["chapter_definitions"]
        ]
        changed += 1

    choices = choice_by_id(package)
    for choice_point in mechanics.get("choice_table") or []:
        for option in choice_point.get("options") or []:
            choice = choices.get(option.get("choice_id"))
            if not choice:
                continue
            merge_flags(choice, option.get("set_flags") or [])
            merge_state_changes(choice, option.get("state_changes") or {})
            changed += 1

    endings = {
        item.get("ending_id"): item
        for item in ((mechanics.get("ending_gate_logic") or {}).get("endings") or [])
    }
    for ending_id, ending_def in endings.items():
        node = (package.get("nodes") or {}).get(ending_id)
        if not node or not node.get("ending"):
            continue
        node["ending"]["ending_type"] = ending_def.get("ending_type", node["ending"].get("ending_type", "normal"))
        node["ending"]["achievement_id"] = ending_def.get("achievement_id")
        changed += 1

    changed += add_final_ending_gate(package, mechanics)
    return changed


def add_final_ending_gate(package: dict[str, Any], mechanics: dict[str, Any]) -> int:
    nodes = package.get("nodes") or {}
    ending_logic = mechanics.get("ending_gate_logic") or {}
    ending_defs = ending_logic.get("endings") or []
    if not ending_defs:
        return 0
    ending_ids = {item.get("ending_id") for item in ending_defs}
    candidate_id = ""
    for node_id, node in nodes.items():
        choices = node.get("choices") or []
        if choices and all(choice.get("target_node_id") in ending_ids for choice in choices):
            candidate_id = node_id
    if not candidate_id:
        return 0
    gate_id = "n_final_ending_gate"
    if gate_id in nodes:
        return 0
    source_node = nodes[candidate_id]
    for choice in source_node.get("choices") or []:
        choice["target_node_id"] = gate_id
        changes = ensure_changes(choice)
        changes.setdefault("add_flags", [])
        if choice.get("choice_id") not in changes["add_flags"]:
            changes["add_flags"].append(choice.get("choice_id"))
    fallback = None
    routes = []
    for ending in sorted(ending_defs, key=lambda item: item.get("priority", 999)):
        ending_id = ending.get("ending_id")
        if ending.get("is_fallback"):
            fallback = ending_id
            continue
        routes.append({"condition": ending.get("condition_runtime"), "next_node_id": ending_id})
    fallback = fallback or ending_logic.get("fallback_safety", {}).get("fallback_ending") or (ending_defs[-1].get("ending_id") if ending_defs else None)
    if fallback:
        routes.append({"condition": None, "next_node_id": fallback})
    gate_node = {
        "node_id": gate_id,
        "title": "结局门:所有选择都落回自身",
        "chapter_title": source_node.get("chapter_title", ""),
        "scene_id": source_node.get("scene_id"),
        "progress": min(99, float(source_node.get("progress") or 90) + 0.5),
        "ambient": source_node.get("ambient", "none"),
        "background_asset_id": source_node.get("background_asset_id"),
        "character_layers": source_node.get("character_layers") or [],
        "media": [],
        "segments": [
            {
                "segment_id": f"{gate_id}_s01",
                "segment_type": "narration",
                "speaker_id": None,
                "text": "此前每一次选择,都在这一息里回到主角身上。",
                "effects": [],
                "show_layers": [],
                "asset_id": None,
                "auto_advance_ms": None,
            }
        ],
        "choices": [],
        "next": None,
        "routes": routes,
        "is_ending": False,
        "ending": None,
        "qa": {
            "purpose": "按 mechanics_plan 的 ending_gate_logic 执行最终结局优先级。",
            "player_must_understand": ["结局由累积状态决定"],
            "choice_callback_required": False,
            "asset_trace": [],
        },
    }
    rebuilt = {}
    for node_id, node in nodes.items():
        rebuilt[node_id] = node
        if node_id == candidate_id:
            rebuilt[gate_id] = gate_node
    package["nodes"] = rebuilt
    return 1


def convert_inline_dialogue(package: dict[str, Any]) -> int:
    speakers = {
        character.get("display_name"): char_id
        for char_id, character in (package.get("characters") or {}).items()
        if character.get("display_name")
    }
    changed = 0
    for node in (package.get("nodes") or {}).values():
        for segment in node.get("segments") or []:
            text = segment.get("text", "")
            for display_name, char_id in speakers.items():
                for sep in [":", "："]:
                    prefix = display_name + sep
                    if text.startswith(prefix):
                        segment["segment_type"] = "dialogue"
                        segment["speaker_id"] = char_id
                        segment["text"] = text[len(prefix):].strip()
                        changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich a compiled runtime package from agent artifacts")
    parser.add_argument("--runtime-package", type=Path, required=True)
    parser.add_argument("--character-world", type=Path)
    parser.add_argument("--mechanics-plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--preview-copy", type=Path)
    args = parser.parse_args()

    package = load_json(args.runtime_package)
    changes: dict[str, int] = {}
    if args.character_world and args.character_world.exists():
        character_world = load_json(args.character_world)
        changes["characters"] = enrich_characters(package, character_world)
        changes["scenes"] = enrich_scenes(package, character_world)
    if args.mechanics_plan and args.mechanics_plan.exists():
        mechanics = load_json(args.mechanics_plan)
        changes["mechanics"] = enrich_mechanics(package, mechanics)
    changes["dialogue_segments"] = convert_inline_dialogue(package)

    write_json(args.output, package)
    if args.preview_copy:
        args.preview_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.output, args.preview_copy)
    write_json(args.report, {
        "runtime_package": str(args.output),
        "changes": changes,
        "total_changes": sum(changes.values()),
    })
    print(json.dumps({"output": str(args.output), "changes": changes}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
