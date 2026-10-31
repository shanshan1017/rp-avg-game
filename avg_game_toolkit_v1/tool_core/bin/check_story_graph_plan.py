#!/usr/bin/env python3
"""Zero-LLM structural checks for story_graph_plan.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


Issue = dict[str, str]


def issue(severity: str, category: str, message: str, node_id: str = "", suggestion: str = "") -> Issue:
    return {
        "severity": severity,
        "category": category,
        "node_id": node_id,
        "message": message,
        "suggestion": suggestion,
    }


def condition_mentions(condition: str | None, attr: str) -> bool:
    if not condition:
        return False
    return re.search(rf"(^|[^A-Za-z0-9_]){re.escape(attr)}([^A-Za-z0-9_]|$)", condition) is not None


def collect_incoming(nodes: list[dict[str, Any]]) -> dict[str, set[str]]:
    incoming: dict[str, set[str]] = defaultdict(set)
    for node in nodes:
        node_id = node["node_id"]
        for target in node.get("next_node_ids", []):
            incoming[target].add(node_id)
        for choice in node.get("choices", []):
            incoming[choice.get("target_node_id", "")].add(node_id)
        auto_route = node.get("auto_route") or {}
        for target in auto_route.values():
            incoming[target].add(node_id)
    return incoming


def reachable_from(entry: str, node_map: dict[str, dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque([entry])
    while queue:
        current = queue.popleft()
        if current in seen or current not in node_map:
            continue
        seen.add(current)
        node = node_map[current]
        targets = list(node.get("next_node_ids", []))
        targets.extend(choice.get("target_node_id", "") for choice in node.get("choices", []))
        targets.extend((node.get("auto_route") or {}).values())
        for target in targets:
            if target and target not in seen:
                queue.append(target)
    return seen


def check_graph(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    nodes = data.get("nodes", [])
    node_ids = [node.get("node_id", "") for node in nodes]
    duplicate_nodes = [node_id for node_id, count in Counter(node_ids).items() if count > 1]
    for node_id in duplicate_nodes:
        issues.append(issue("error", "duplicate_node", f"Duplicate node id: {node_id}", node_id))

    node_map = {node["node_id"]: node for node in nodes if node.get("node_id")}
    entry = data.get("entry_node_id", "")
    if not entry:
        issues.append(issue("error", "missing_entry", "Missing entry_node_id."))
    elif entry not in node_map:
        issues.append(issue("error", "bad_entry", f"entry_node_id '{entry}' is not a node."))

    for node in nodes:
        node_id = node["node_id"]
        for field, target in [("next_node_ids", t) for t in node.get("next_node_ids", [])]:
            if target not in node_map:
                issues.append(issue("error", "missing_target", f"{field} target '{target}' does not exist.", node_id))
        for choice in node.get("choices", []):
            target = choice.get("target_node_id")
            if target not in node_map:
                issues.append(issue("error", "missing_choice_target", f"Choice target '{target}' does not exist.", node_id))
        for target in (node.get("auto_route") or {}).values():
            if target not in node_map:
                issues.append(issue("error", "missing_auto_route_target", f"auto_route target '{target}' does not exist.", node_id))

    if entry in node_map:
        reachable = reachable_from(entry, node_map)
        for node_id in sorted(set(node_map) - reachable):
            issues.append(issue("warning", "orphan_node", f"Node '{node_id}' is not reachable from entry_node_id.", node_id))

    incoming = collect_incoming(nodes)
    for node in nodes:
        node_id = node["node_id"]
        if node_id != entry and not incoming.get(node_id):
            issues.append(issue("warning", "no_incoming_edge", f"Node '{node_id}' has no incoming edge.", node_id))
        if node.get("node_type") == "failure":
            if not incoming.get(node_id):
                issues.append(issue("error", "orphan_failure", "Failure node has no incoming cause.", node_id))
            if not node.get("failure_cause"):
                issues.append(issue("warning", "failure_without_cause", "Failure node lacks failure_cause.", node_id))

    for node in nodes:
        choices = node.get("choices", [])
        if len(choices) < 2:
            continue
        node_id = node["node_id"]
        targets = {choice.get("target_node_id") for choice in choices}
        if len(targets) == 1:
            has_value = any(choice.get("value_effects") for choice in choices)
            has_echo = any(choice.get("expected_later_echo") for choice in choices)
            if not has_value and not has_echo:
                issues.append(issue(
                    "warning",
                    "pseudo_choice",
                    "All choices point to the same target and have no value effects or expected echoes.",
                    node_id,
                    "Split into distinct intermediate nodes, add value effects, or declare later echoes.",
                ))
        next_targets = set()
        for target in targets:
            target_node = node_map.get(target or "")
            if target_node and len(target_node.get("next_node_ids", [])) == 1:
                next_targets.add(target_node["next_node_ids"][0])
        if len(targets) > 1 and len(next_targets) == 1:
            has_echo = any(choice.get("expected_later_echo") for choice in choices)
            if not has_echo:
                issues.append(issue(
                    "warning",
                    "funnel_convergence",
                    "Branch targets converge immediately and no choice declares a later echo.",
                    node_id,
                    "Declare echo points, add auto_route, or preserve branch-specific consequences.",
                ))

    return issues


def check_value_system(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    attrs = [attr["attribute_id"] for attr in data.get("value_system", {}).get("attributes", [])]
    nodes = data.get("nodes", [])
    endings = data.get("value_system", {}).get("ending_conditions", [])
    routing_rules = data.get("value_system", {}).get("routing_rules", [])
    for attr in attrs:
        used_by_choice = any(
            effect.get("attribute_id") == attr
            for node in nodes
            for choice in node.get("choices", [])
            for effect in choice.get("value_effects", [])
        )
        used_by_gate = any(
            condition_mentions(choice.get("gate_condition"), attr)
            for node in nodes
            for choice in node.get("choices", [])
        )
        used_by_ending = any(condition_mentions(end.get("condition"), attr) for end in endings)
        used_by_routing = any(condition_mentions(rule.get("condition"), attr) for rule in routing_rules)
        if not used_by_choice:
            issues.append(issue("warning", "value_attribute_no_choice_effect", f"Value attribute '{attr}' is never changed by choices."))
        if not (used_by_gate or used_by_ending or used_by_routing):
            issues.append(issue("warning", "value_attribute_never_read", f"Value attribute '{attr}' is never read by gates, routing, or endings."))

    normal_endings = [end for end in endings if end.get("ending_type") not in {"failure", "bad"}]
    if len(normal_endings) < 2:
        issues.append(issue("warning", "ending_diversity_low", "Fewer than two non-failure ending conditions are declared."))

    return issues


def check_media_hooks(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for node in data.get("nodes", []):
        node_id = node["node_id"]
        hooks = node.get("media_planning_hooks", {})
        visual = hooks.get("visual_facts_required", [])
        fallback = hooks.get("text_fallbacks_required", [])
        ui = hooks.get("ui_surface_hints", [])
        if node.get("player_must_understand") and not (visual or fallback or ui):
            issues.append(issue(
                "warning",
                "unvisualized_required_fact",
                "Node has player_must_understand facts but no visual/text/UI delivery hook.",
                node_id,
            ))
        for choice in node.get("choices", []):
            if not choice.get("player_must_know"):
                issues.append(issue("warning", "choice_without_comprehension_gate", "Choice lacks player_must_know.", node_id))
            if not choice.get("value_effects") and not choice.get("expected_later_echo") and not choice.get("is_failure"):
                issues.append(issue("warning", "choice_without_declared_consequence", "Choice has no value effect, later echo, or failure flag.", node_id))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Check story_graph_plan.json for structural planning issues.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args()

    data = json.loads(args.path.read_text(encoding="utf-8"))
    issues = []
    issues.extend(check_graph(data))
    issues.extend(check_value_system(data))
    issues.extend(check_media_hooks(data))

    summary = {
        "path": str(args.path),
        "issue_count": len(issues),
        "errors": sum(1 for item in issues if item["severity"] == "error"),
        "warnings": sum(1 for item in issues if item["severity"] == "warning"),
        "issues": issues,
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    if args.fail_on_error and summary["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
