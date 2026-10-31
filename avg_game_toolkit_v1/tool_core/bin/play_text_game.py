#!/usr/bin/env python3
"""MUD-like CLI runner for text-only interactive game dry runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TERMINAL_MODES = {"ending", "failure"}


def load_pack(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if "cells" not in data or "entry_cell_id" not in data:
        raise ValueError("pack must contain cells and entry_cell_id")
    return data


def index_cells(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cells = {cell["cell_id"]: cell for cell in data["cells"]}
    missing = [cell["cell_id"] for cell in data["cells"] if cell.get("next_cell_id") and cell["next_cell_id"] not in cells]
    for cell in data["cells"]:
        for choice in cell.get("choices", []):
            if choice["leads_to"] not in cells:
                missing.append(f"{cell['cell_id']} -> {choice['leads_to']}")
    if missing:
        raise ValueError("missing target cells: " + ", ".join(missing))
    return cells


def apply_effects(state: dict[str, Any], effects: dict[str, Any] | None) -> None:
    if not effects:
        return
    for key, value in effects.items():
        current = state.get(key)
        numeric_delta = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isinstance(current, (int, float))
            and not isinstance(current, bool)
        )
        if numeric_delta:
            state[key] += value
        else:
            state[key] = value


def requirement_met(state: dict[str, Any], key: str, expected: Any) -> bool:
    actual = state.get(key)
    if isinstance(expected, dict):
        if ">=" in expected:
            return actual is not None and actual >= expected[">="]
        if "<=" in expected:
            return actual is not None and actual <= expected["<="]
        if ">" in expected:
            return actual is not None and actual > expected[">"]
        if "<" in expected:
            return actual is not None and actual < expected["<"]
        if "!=" in expected:
            return actual != expected["!="]
    return actual == expected


def choice_enabled(state: dict[str, Any], choice: dict[str, Any]) -> tuple[bool, str]:
    requires = choice.get("requires") or {}
    failed: list[str] = []
    for key, expected in requires.items():
        if not requirement_met(state, key, expected):
            failed.append(key)
    if failed:
        return False, choice.get("disabled_hint") or f"missing: {', '.join(failed)}"
    return True, ""


def print_list(title: str, values: list[str]) -> None:
    if values:
        print(f"{title}:")
        for value in values:
            print(f"  - {value}")


def render_cell(cell: dict[str, Any], state: dict[str, Any], show_assets: bool) -> None:
    print()
    print(f"## {cell['title']} [{cell['cell_id']}]")
    print(f"模式: {cell.get('mode', '')}")
    if cell.get("location"):
        print(f"地点: {cell['location']}")
    if cell.get("characters"):
        print("人物: " + ", ".join(cell["characters"]))
    if cell.get("player_context"):
        print(f"玩家处境: {cell['player_context']}")
    if cell.get("purpose"):
        print(f"剧情目的: {cell['purpose']}")
    for line in cell.get("body", []):
        print(f"\n{line}")
    print_list("必须理解", cell.get("player_must_understand", []))
    print_list("画面证据", cell.get("visual_evidence", []))
    print_list("文本/UI证据", cell.get("text_evidence", []))
    print_list("UI面板", cell.get("ui_surfaces", []))
    if show_assets:
        print_list("资产槽", cell.get("asset_slots", []))

    choices = cell.get("choices") or []
    if choices:
        print("\n选择:")
        for index, choice in enumerate(choices, 1):
            enabled, hint = choice_enabled(state, choice)
            status = "可选" if enabled else f"锁定: {hint}"
            print(f"  {index}. {choice['label']} ({choice['choice_id']}) [{status}]")


def resolve_choice(cell: dict[str, Any], state: dict[str, Any], token: str) -> dict[str, Any]:
    choices = cell.get("choices") or []
    if not choices:
        raise ValueError("current cell has no choices")
    selected: dict[str, Any] | None = None
    if token.isdigit():
        index = int(token) - 1
        if 0 <= index < len(choices):
            selected = choices[index]
    else:
        selected = next((choice for choice in choices if choice["choice_id"] == token), None)
    if not selected:
        raise ValueError(f"unknown choice: {token}")
    enabled, hint = choice_enabled(state, selected)
    if not enabled:
        raise ValueError(f"choice locked: {hint}")
    return selected


def play(data: dict[str, Any], scripted_path: list[str], show_assets: bool, quiet: bool) -> tuple[str, list[str], dict[str, Any]]:
    cells = index_cells(data)
    state = dict(data.get("initial_state") or {})
    current_id = data["entry_cell_id"]
    entered: set[str] = set()
    log: list[str] = []
    path_index = 0

    print(f"# {data.get('title', data.get('project_id', 'Text Playtest'))}")
    print("输入 help 查看命令。" if not scripted_path and not quiet else "Scripted playthrough.")

    while True:
        cell = cells[current_id]
        if current_id not in entered:
            apply_effects(state, cell.get("on_enter_effects"))
            entered.add(current_id)
        if not quiet:
            render_cell(cell, state, show_assets)
        log.append(current_id)

        if cell.get("mode") in TERMINAL_MODES:
            if not quiet:
                print(f"\n终局: {cell.get('mode')}")
            return current_id, log, state

        if cell.get("choices"):
            if scripted_path:
                if path_index >= len(scripted_path):
                    raise ValueError(f"scripted path ended at choice cell {current_id}")
                token = scripted_path[path_index]
                path_index += 1
                choice = resolve_choice(cell, state, token)
                if not quiet:
                    print(f"\n> {choice['label']} ({choice['choice_id']})")
            else:
                while True:
                    command = input("\n> ").strip()
                    if command in {"quit", "q", "exit"}:
                        return current_id, log, state
                    if command == "help":
                        print("commands: look, state, log, assets, choose <n|id>, quit")
                        continue
                    if command == "look":
                        render_cell(cell, state, show_assets)
                        continue
                    if command == "state":
                        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
                        continue
                    if command == "log":
                        print(" -> ".join(log))
                        continue
                    if command == "assets":
                        print_list("资产槽", cell.get("asset_slots", []))
                        continue
                    if command.startswith("choose "):
                        token = command.split(maxsplit=1)[1]
                    else:
                        token = command
                    try:
                        choice = resolve_choice(cell, state, token)
                        break
                    except ValueError as exc:
                        print(f"无法选择: {exc}")
            apply_effects(state, choice.get("effects"))
            log.append(choice["choice_id"])
            current_id = choice["leads_to"]
            continue

        next_id = cell.get("next_cell_id")
        if not next_id:
            return current_id, log, state
        current_id = next_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Play a text-only interactive game pack")
    parser.add_argument("pack", type=Path)
    parser.add_argument("--path", default="", help="Comma-separated choice IDs or indexes for scripted play")
    parser.add_argument("--show-assets", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--transcript", type=Path)
    args = parser.parse_args()

    data = load_pack(args.pack)
    scripted = [part.strip() for part in args.path.split(",") if part.strip()]
    try:
        terminal, log, state = play(data, scripted, args.show_assets, args.quiet)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "terminal_cell_id": terminal,
        "steps": log,
        "state": state,
    }
    if args.transcript:
        args.transcript.parent.mkdir(parents=True, exist_ok=True)
        args.transcript.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.quiet:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("\n# Playtest Summary")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
