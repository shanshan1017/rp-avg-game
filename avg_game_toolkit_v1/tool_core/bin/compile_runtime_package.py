#!/usr/bin/env python3
"""Compile authoring/playtest data into runtime_game_package.json.

The first compiler target is deliberately pragmatic: it can ingest the current
`text_playtest_pack.json` / v5 `game_data.json` cell format and emit the newer
hot-swappable runtime package format. Later compiler stages can add richer
authoring inputs without changing the runtime contract.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


POSITION_CYCLE = ["left", "center", "right"]

KNOWN_DISPLAY_NAMES = {
    "player": "你",
    "lin_cheng": "林澄",
    "tang_lingyin": "唐绫音",
    "xing_mi": "星弥",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def safe_id(text: str, fallback: str = "game") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or fallback


def as_cells(data: dict[str, Any]) -> list[dict[str, Any]]:
    cells = data.get("cells")
    if isinstance(cells, list):
        return cells
    nodes = data.get("nodes")
    if isinstance(nodes, list):
        return nodes
    raise ValueError("Input must contain a cells array or nodes array.")


def infer_asset_type(asset_id: str) -> str:
    if asset_id.startswith(("vid_", "video_", "clip_")):
        return "video"
    if asset_id.startswith(("audio_", "bgm_", "sfx_", "amb_")):
        return "audio"
    if asset_id.startswith(("ui_", "skin_")):
        return "ui"
    return "image"


def infer_asset_usage(asset_id: str) -> list[str]:
    if asset_id.startswith(("bg_", "background_")):
        return ["background"]
    if asset_id.startswith(("char_", "portrait_")):
        return ["character_portrait"]
    if asset_id.startswith(("prop_", "item_")):
        return ["prop"]
    if asset_id.startswith(("cg_", "still_", "poster_")):
        return ["story_still"]
    if asset_id.startswith(("vid_", "video_", "clip_")):
        return ["video_clip"]
    if asset_id.startswith(("bgm_", "amb_")):
        return ["audio_bgm"]
    if asset_id.startswith(("sfx_", "audio_")):
        return ["audio_sfx"]
    if asset_id.startswith(("ui_", "skin_")):
        return ["ui_skin"]
    if asset_id.startswith("cover_"):
        return ["cover"]
    return ["qa_only"]


def extension_for_type(asset_type: str) -> str:
    return {
        "image": ".png",
        "video": ".mp4",
        "audio": ".mp3",
        "ui": ".png",
        "sprite": ".png",
        "font": ".woff2",
        "data": ".json",
    }.get(asset_type, ".asset")


def asset_path(asset_id: str, asset_type: str) -> str:
    folder = {
        "image": "placeholders/images",
        "video": "placeholders/videos",
        "audio": "placeholders/audio",
        "ui": "placeholders/ui",
    }.get(asset_type, "placeholders")
    return f"{folder}/{asset_id}{extension_for_type(asset_type)}"


def collect_asset_ids(cells: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for cell in cells:
        ids.update(str(item) for item in cell.get("asset_slots") or [])
    return ids


def make_asset(asset_id: str) -> dict[str, Any]:
    asset_type = infer_asset_type(asset_id)
    return {
        "asset_id": asset_id,
        "type": asset_type,
        "path": asset_path(asset_id, asset_type),
        "usage": infer_asset_usage(asset_id),
        "required": False,
        "alt_text": asset_id.replace("_", " "),
        "source_manifest_id": None,
        "width": None,
        "height": None,
        "duration_sec": None,
    }


def location_id(cell: dict[str, Any]) -> str:
    return safe_id(str(cell.get("location_id") or cell.get("location") or "unknown_scene"), "unknown_scene")


def first_asset_with_prefix(cell: dict[str, Any], prefix: str) -> str | None:
    for asset_id in cell.get("asset_slots") or []:
        if str(asset_id).startswith(prefix):
            return str(asset_id)
    return None


def background_for_cell(cell: dict[str, Any]) -> str | None:
    return first_asset_with_prefix(cell, "bg_") or first_asset_with_prefix(cell, "background_")


def display_name(character_id: str) -> str:
    return KNOWN_DISPLAY_NAMES.get(character_id, character_id.replace("_", " ").title())


def matching_character_asset(character_id: str, asset_ids: set[str]) -> str | None:
    prefixes = [
        f"char_{character_id}_",
        f"portrait_{character_id}_",
        f"{character_id}_",
    ]
    for prefix in prefixes:
        matches = sorted(asset_id for asset_id in asset_ids if asset_id.startswith(prefix))
        if matches:
            return matches[0]
    return None


def build_assets(cells: list[dict[str, Any]], cover_asset_id: str | None = None) -> dict[str, Any]:
    asset_ids = collect_asset_ids(cells)
    if cover_asset_id:
        asset_ids.add(cover_asset_id)
    return {asset_id: make_asset(asset_id) for asset_id in sorted(asset_ids)}


def build_characters(cells: list[dict[str, Any]], assets: dict[str, Any]) -> dict[str, Any]:
    character_ids: set[str] = set()
    for cell in cells:
        character_ids.update(str(item) for item in cell.get("characters") or [])
    if not character_ids:
        character_ids.add("player")

    asset_ids = set(assets)
    characters: dict[str, Any] = {}
    for character_id in sorted(character_ids):
        portrait_asset = matching_character_asset(character_id, asset_ids)
        if not portrait_asset:
            portrait_asset = f"placeholder_portrait_{character_id}"
            assets[portrait_asset] = make_asset(portrait_asset)
            assets[portrait_asset]["usage"] = ["character_portrait"]
        characters[character_id] = {
            "character_id": character_id,
            "display_name": display_name(character_id),
            "role": "player" if character_id == "player" else "cast",
            "player_visible_profile": "Runtime placeholder profile; replace from character_world_bible when available.",
            "speech_style": "TBD from character/world bible.",
            "color": "#d8c7ff" if character_id != "player" else "#f7f0df",
            "default_expression": "default",
            "portraits": [
                {
                    "expression": "default",
                    "asset_id": portrait_asset,
                    "pose": "standing",
                }
            ],
        }
    return characters


def build_scenes(cells: list[dict[str, Any]], assets: dict[str, Any]) -> dict[str, Any]:
    scene_assets: dict[str, str | None] = {}
    scene_names: dict[str, str] = {}
    for cell in cells:
        scene_id = location_id(cell)
        scene_names.setdefault(scene_id, str(cell.get("location") or cell.get("location_id") or scene_id))
        scene_assets.setdefault(scene_id, background_for_cell(cell))
    scenes: dict[str, Any] = {}
    for scene_id, bg_asset in sorted(scene_assets.items()):
        if bg_asset and bg_asset not in assets:
            assets[bg_asset] = make_asset(bg_asset)
        scenes[scene_id] = {
            "scene_id": scene_id,
            "name": scene_names.get(scene_id, scene_id),
            "type": "major",
            "description": f"Scene compiled from authoring location `{scene_id}`.",
            "arrival": "",
            "background_asset_id": bg_asset,
            "ambient": "none",
        }
    return scenes


def segment_type_for_line(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith(("系统", "证据栏", "提示")):
        return "system"
    if stripped.startswith(("手机", "短信", "消息")):
        return "phone_message"
    return "narration"


def split_body_into_segments(cell: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    body = cell.get("body") or []
    for index, line in enumerate(body, 1):
        text = str(line).strip()
        if not text:
            continue
        segments.append(
            {
                "segment_id": f"{cell['cell_id']}_s{index:02d}",
                "segment_type": segment_type_for_line(text),
                "speaker_id": None,
                "text": text,
                "effects": [],
                "show_layers": [],
                "asset_id": None,
                "auto_advance_ms": None,
            }
        )
    return segments


def convert_requires_to_condition(requires: dict[str, Any] | None) -> Any:
    if not requires:
        return None
    conditions: list[dict[str, Any]] = []
    for key, expected in requires.items():
        if isinstance(expected, dict):
            if ">=" in expected:
                conditions.append({"var": key, "op": ">=", "value": expected[">="]})
            elif "<=" in expected:
                conditions.append({"var": key, "op": "<=", "value": expected["<="]})
            elif ">" in expected:
                conditions.append({"var": key, "op": ">", "value": expected[">"]})
            elif "<" in expected:
                conditions.append({"var": key, "op": "<", "value": expected["<"]})
            elif "!=" in expected:
                conditions.append({"var": key, "op": "!=", "value": expected["!="]})
            else:
                conditions.append({"var": key, "op": "==", "value": expected})
        else:
            conditions.append({"var": key, "op": "==", "value": expected})
    if len(conditions) == 1:
        return conditions[0]
    return {"all": conditions}


def convert_effects_to_changes(effects: dict[str, Any] | None, initial_state: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if not effects:
        return changes
    values_delta: dict[str, float] = {}
    set_variables: dict[str, Any] = {}
    add_flags: list[str] = []
    for key, value in effects.items():
        if key.startswith("flag."):
            if value:
                add_flags.append(key.removeprefix("flag."))
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool) and isinstance(initial_state.get(key), (int, float)):
            values_delta[key] = value
        else:
            set_variables[key] = value
    if values_delta:
        changes["values_delta"] = values_delta
    if set_variables:
        changes["set_variables"] = set_variables
    if add_flags:
        changes["add_flags"] = add_flags
    return changes


def character_layers_for_cell(cell: dict[str, Any], characters: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    visible_ids = [cid for cid in (cell.get("characters") or []) if cid in characters and cid != "player"]
    for index, character_id in enumerate(visible_ids):
        portrait = characters[character_id]["portraits"][0]
        layers.append(
            {
                "character_id": character_id,
                "expression": portrait["expression"],
                "asset_id": portrait["asset_id"],
                "position": POSITION_CYCLE[index % len(POSITION_CYCLE)],
                "visible": True,
                "transition": "fade",
                "z_index": 10 + index,
            }
        )
    return layers


def media_for_cell(cell: dict[str, Any], visible_character_asset_ids: set[str]) -> list[dict[str, Any]]:
    media: list[dict[str, Any]] = []
    bg_asset = background_for_cell(cell)
    for asset_id in cell.get("asset_slots") or []:
        asset_id = str(asset_id)
        asset_type = infer_asset_type(asset_id)
        if asset_id == bg_asset or asset_id in visible_character_asset_ids:
            continue
        if asset_type == "video":
            media.append({"media_type": "video", "asset_id": asset_id, "presentation": "fullscreen", "autoplay": False, "loop": False})
        elif asset_type == "audio":
            presentation = "bgm" if "audio_bgm" in infer_asset_usage(asset_id) else "sfx"
            media.append({"media_type": "audio", "asset_id": asset_id, "presentation": presentation, "autoplay": False, "loop": presentation == "bgm"})
        elif asset_type in {"image", "ui"}:
            usage = set(infer_asset_usage(asset_id))
            presentation = "overlay" if "ui_skin" in usage else "inline"
            media.append({"media_type": "image", "asset_id": asset_id, "presentation": presentation, "autoplay": False, "loop": False})
    return media


def build_nodes(
    cells: list[dict[str, Any]],
    characters: dict[str, Any],
    initial_state: dict[str, Any],
) -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    count = max(len(cells) - 1, 1)
    for index, cell in enumerate(cells):
        node_id = str(cell["cell_id"])
        mode = cell.get("mode")
        choices = []
        for choice in cell.get("choices") or []:
            choices.append(
                {
                    "choice_id": str(choice.get("choice_id") or f"{node_id}_c{len(choices) + 1:02d}"),
                    "label": str(choice["label"]),
                    "target_node_id": str(choice["leads_to"]),
                    "condition": convert_requires_to_condition(choice.get("requires")),
                    "locked_hint": str(choice.get("disabled_hint") or ""),
                    "changes": convert_effects_to_changes(choice.get("effects"), initial_state),
                    "callback_node_id": None,
                    "effects": [],
                }
            )
        is_ending = mode in {"ending", "failure"}
        ending_type = "failure" if mode == "failure" else "normal"
        body_text = "\n".join(str(line) for line in cell.get("body") or [])
        character_layers = character_layers_for_cell(cell, characters)
        visible_character_asset_ids = {
            str(layer.get("asset_id"))
            for layer in character_layers
            if layer.get("asset_id")
        }
        node = {
            "node_id": node_id,
            "title": str(cell.get("title") or node_id),
            "chapter_title": str(cell.get("chapter_title") or "Main"),
            "scene_id": location_id(cell),
            "progress": round((index / count) * 100, 2),
            "ambient": "none",
            "background_asset_id": background_for_cell(cell),
            "character_layers": character_layers,
            "media": media_for_cell(cell, visible_character_asset_ids),
            "segments": split_body_into_segments(cell),
            "choices": choices,
            "next": None if choices or is_ending else cell.get("next_cell_id"),
            "routes": [],
            "is_ending": is_ending,
            "ending": {
                "ending_type": ending_type,
                "description": str(cell.get("purpose") or cell.get("title") or ending_type),
                "closing": body_text[-240:] if body_text else str(cell.get("title") or ending_type),
                "achievement_id": None,
            }
            if is_ending
            else None,
            "qa": {
                "purpose": str(cell.get("purpose") or ""),
                "player_must_understand": list(cell.get("player_must_understand") or []),
                "choice_callback_required": bool(choices),
                "asset_trace": list(cell.get("asset_slots") or []),
            },
        }
        nodes[node_id] = node
    return nodes


def build_state(initial_state: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, float] = {}
    variables: dict[str, Any] = {}
    for key, value in initial_state.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            values[key] = value
        elif key == "flags" and isinstance(value, list):
            continue
        else:
            variables[key] = value
    return {
        "primary_value": {
            "id": "progress",
            "display_name": "推进度",
            "initial": 0,
            "min": 0,
            "max": 100,
        },
        "values": values,
        "variables": variables,
        "flags": list(initial_state.get("flags") or []) if isinstance(initial_state.get("flags"), list) else [],
    }


def compile_from_text_pack(data: dict[str, Any], asset_base_path: str, cover_asset_id: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    cells = as_cells(data)
    project_id = safe_id(str(data.get("project_id") or data.get("game_id") or "compiled_game"))
    initial_state = dict(data.get("initial_state") or {})
    assets = build_assets(cells, cover_asset_id)
    characters = build_characters(cells, assets)
    scenes = build_scenes(cells, assets)
    nodes = build_nodes(cells, characters, initial_state)

    package = {
        "package_version": "0.1.0",
        "game_id": project_id,
        "engine_contract": {
            "engine_id": "fixed_avg_runtime",
            "engine_version": "0.1.0",
            "required_features": [
                "segments",
                "choices",
                "conditional_choices",
                "save_load",
                "chapter_select",
                "endings",
                "settings",
                "play_stats",
                "background_images",
                "character_portraits",
                "expression_switching",
                "video_playback",
                "audio_playback",
                "worldline_review",
            ],
            "asset_base_path": asset_base_path,
            "load_policy": "single_json_with_local_assets",
        },
        "meta": {
            "title": str(data.get("title") or project_id),
            "subtitle": "Compiled runtime package",
            "author": "Cross-Disciplinary Coherence Tool",
            "version": "0.1.0",
            "description": "Compiled from text/playtest authoring data.",
            "language": "zh-CN",
            "target_playtime_min": [20, 30],
            "pov": "first_person",
            "story_intention_summary": {
                "core_question": "TBD from story_intention.",
                "emotional_anchor": "TBD from story_intention.",
                "core_intention": "TBD from story_intention.",
                "ending_philosophy": "branch_specific_answers",
            },
            "content_design_tags": ["avg", "compiled_from_text_playtest", "hot_swappable_package"],
            "content_notes": [],
        },
        "home": {
            "cover": {
                "label": project_id,
                "tagline": str(data.get("title") or "Compiled AVG"),
                "cover_asset_id": cover_asset_id,
            },
            "enabled_features": [
                "import_json",
                "continue",
                "new_game",
                "ending_records",
                "achievement_records",
                "chapter_select",
                "save_slots",
                "play_stats",
                "settings",
            ],
            "disabled_features": ["developer_intro"],
        },
        "settings_defaults": {
            "color_mode": "dark",
            "font_scale": 1,
            "motion": "full",
            "autoplay_ms": 0,
        },
        "start_node_id": str(data.get("entry_cell_id") or data.get("entry_node_id") or cells[0]["cell_id"]),
        "state": build_state(initial_state),
        "assets": assets,
        "characters": characters,
        "scenes": scenes,
        "achievements": {},
        "chapters": [
            {
                "chapter_id": "main",
                "title": "Main",
                "entry_node_id": str(data.get("entry_cell_id") or data.get("entry_node_id") or cells[0]["cell_id"]),
            }
        ],
        "nodes": nodes,
    }
    report = {
        "source_format": "text_playtest_pack_cells",
        "project_id": project_id,
        "cell_count": len(cells),
        "node_count": len(nodes),
        "asset_count": len(assets),
        "character_count": len(characters),
        "scene_count": len(scenes),
        "warnings": [
            "This compiler pass preserves playable structure and asset slots, but rich dramaturgy/story-intention fields should be supplied by full authoring artifacts in later stages."
        ],
    }
    return package, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile text/playtest data into runtime_game_package.json")
    parser.add_argument("--text-pack", type=Path, required=True, help="Path to text_playtest_pack.json or compatible cells JSON.")
    parser.add_argument("--output", type=Path, required=True, help="Path to write runtime_game_package.json.")
    parser.add_argument("--report", type=Path, help="Path to write compile report JSON.")
    parser.add_argument("--asset-base-path", default="./assets/", help="Runtime asset base path.")
    parser.add_argument("--cover-asset-id", default="", help="Optional cover asset id.")
    args = parser.parse_args()

    data = load_json(args.text_pack)
    package, report = compile_from_text_pack(data, args.asset_base_path, args.cover_asset_id or None)
    write_json(args.output, package)
    report["output"] = str(args.output)
    if args.report:
        write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
