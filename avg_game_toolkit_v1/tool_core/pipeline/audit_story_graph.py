#!/usr/bin/env python3
"""Audit a first-person interactive video story graph draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TERMINAL_TYPES = {"ending", "failure"}
REQUIRED_ARCHETYPES = {"邻家妹妹", "高冷上司姐姐", "网吧偶遇少女"}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def iter_choices(node: dict) -> list[dict]:
    return node.get("choices") or []


def audit_graph(data: dict) -> dict:
    nodes = data.get("nodes") or {}
    entry = data.get("entry_node_id")
    issues: list[dict] = []

    def add(severity: str, message: str, node_id: str = "") -> None:
        issues.append({"severity": severity, "node_id": node_id, "message": message})

    if not entry or entry not in nodes:
        add("blocker", "entry_node_id missing or not found")

    for node_id, node in nodes.items():
        duration = node.get("duration_sec")
        if not isinstance(duration, int) or duration < 8 or duration > 15:
            add("major", "duration_sec must be an integer in [8, 15]", node_id)
        if node.get("type") not in {"video", "choice", "failure", "ending"}:
            add("major", "node type must be video, choice, failure, or ending", node_id)
        for choice in iter_choices(node):
            target = choice.get("target")
            if target not in nodes:
                add("blocker", f"choice {choice.get('id')} targets missing node {target}", node_id)

    characters = data.get("characters") or {}
    archetypes = {c.get("archetype") for c in characters.values()}
    missing_archetypes = sorted(REQUIRED_ARCHETYPES - archetypes)
    if missing_archetypes:
        add("major", f"missing required archetypes: {', '.join(missing_archetypes)}")

    reachable: set[str] = set()
    terminal_paths: list[dict] = []

    def walk(node_id: str, path: list[str], total: int) -> None:
        if node_id in path:
            add("major", f"cycle detected: {' -> '.join(path + [node_id])}", node_id)
            return
        node = nodes[node_id]
        reachable.add(node_id)
        next_path = path + [node_id]
        next_total = total + int(node.get("duration_sec") or 0)
        if node.get("type") in TERMINAL_TYPES or not iter_choices(node):
            terminal_paths.append({
                "terminal_node_id": node_id,
                "terminal_type": node.get("type"),
                "duration_sec": next_total,
                "node_sequence": next_path,
            })
            return
        for choice in iter_choices(node):
            target = choice.get("target")
            if target in nodes:
                walk(target, next_path, next_total)

    if entry in nodes:
        walk(entry, [], 0)

    for node_id in nodes:
        if node_id not in reachable:
            add("minor", "node is unreachable from entry", node_id)

    for path in terminal_paths:
        if path["terminal_type"] != "ending":
            continue
        if path["duration_sec"] < 60 or path["duration_sec"] > 90:
            add(
                "minor",
                f"ending path duration {path['duration_sec']}s is outside target [60, 90]",
                path["terminal_node_id"],
            )

    terminal_types = {p["terminal_type"] for p in terminal_paths}
    if "ending" not in terminal_types:
        add("blocker", "no reachable ending")
    if "failure" not in terminal_types:
        add("major", "no reachable failure")

    return {
        "passed": not any(i["severity"] == "blocker" for i in issues),
        "issue_count": len(issues),
        "issues": issues,
        "stats": {
            "nodes": len(nodes),
            "reachable_nodes": len(reachable),
            "terminal_paths": len(terminal_paths),
            "endings": sum(1 for n in nodes.values() if n.get("type") == "ending"),
            "failures": sum(1 for n in nodes.values() if n.get("type") == "failure"),
        },
        "terminal_paths": terminal_paths,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit an interactive video story graph")
    parser.add_argument("story_graph", type=Path)
    args = parser.parse_args()
    report = audit_graph(load_json(args.story_graph))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
