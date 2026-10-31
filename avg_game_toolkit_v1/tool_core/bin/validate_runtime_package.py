#!/usr/bin/env python3
"""Validate a hot-swappable AVG runtime package.

This checker intentionally does more than JSON shape validation. It verifies the
runtime contract that matters to production: graph reachability, state usage,
asset traceability, local-file readiness, and secret/signed URL hygiene.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


Issue = dict[str, Any]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-api-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"AKLT[A-Za-z0-9_\-]{12,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}", re.IGNORECASE),
]

SIGNED_URL_PATTERNS = [
    re.compile(r"X-Tos-Signature=", re.IGNORECASE),
    re.compile(r"X-Amz-Signature=", re.IGNORECASE),
    re.compile(r"X-Tos-Credential=", re.IGNORECASE),
    re.compile(r"X-Amz-Credential=", re.IGNORECASE),
]

PLAYER_TEXT_LABEL_PATTERNS = [
    re.compile(r"\((Narration|Dialogue|System|Right-top hint|Video\s*/\s*fallback)[^)]*\)", re.IGNORECASE),
    re.compile(r"\[(Routing|If)\b", re.IGNORECASE),
]

ENGLISH_WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z'\-]{2,}\b")
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def make_issue(
    severity: str,
    category: str,
    message: str,
    path: str = "",
    suggestion: str = "",
) -> Issue:
    return {
        "severity": severity,
        "category": category,
        "path": path,
        "message": message,
        "suggestion": suggestion,
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def json_path(parts: list[str | int]) -> str:
    text = "$"
    for part in parts:
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += f".{part}"
    return text


def walk_strings(value: Any, parts: list[str | int] | None = None):
    parts = parts or []
    if isinstance(value, str):
        yield json_path(parts), value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, parts + [index])
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from walk_strings(item, parts + [str(key)])


def validate_schema_if_available(data: dict[str, Any], schema_path: Path | None) -> list[Issue]:
    if not schema_path:
        return []
    try:
        import jsonschema  # type: ignore
    except Exception:
        return [
            make_issue(
                "info",
                "schema_validator_unavailable",
                "Python package 'jsonschema' is not installed; skipped full JSON Schema validation.",
                suggestion="Install jsonschema or rely on this tool's structural checks.",
            )
        ]
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    issues: list[Issue] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        issues.append(make_issue("error", "schema", error.message, path))
    return issues


def required_shape_checks(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    required = [
        "package_version",
        "game_id",
        "engine_contract",
        "meta",
        "home",
        "start_node_id",
        "state",
        "assets",
        "characters",
        "scenes",
        "nodes",
    ]
    for key in required:
        if key not in data:
            issues.append(make_issue("error", "missing_required", f"Missing top-level key '{key}'.", f"$.{key}"))
    for key in ["assets", "characters", "scenes", "nodes"]:
        if key in data and not isinstance(data[key], dict):
            issues.append(make_issue("error", "bad_type", f"'{key}' must be an object keyed by id.", f"$.{key}"))
    return issues


def collect_targets(node: dict[str, Any]) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    if node.get("next"):
        targets.append(("next", node["next"]))
    for index, choice in enumerate(node.get("choices") or []):
        targets.append((f"choices[{index}].target_node_id", choice.get("target_node_id", "")))
        callback = choice.get("callback_node_id")
        if callback:
            targets.append((f"choices[{index}].callback_node_id", callback))
    for index, route in enumerate(node.get("routes") or []):
        targets.append((f"routes[{index}].next_node_id", route.get("next_node_id", "")))
    return targets


def reachable_nodes(start: str, nodes: dict[str, Any]) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        if current in seen or current not in nodes:
            continue
        seen.add(current)
        for _, target in collect_targets(nodes[current]):
            if target and target not in seen:
                queue.append(target)
    return seen


def validate_graph(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    nodes: dict[str, Any] = data.get("nodes") or {}
    start = data.get("start_node_id", "")
    if not nodes:
        return [make_issue("error", "empty_graph", "Package has no nodes.", "$.nodes")]
    if start not in nodes:
        issues.append(make_issue("error", "bad_start_node", f"start_node_id '{start}' does not exist.", "$.start_node_id"))

    for key, node in nodes.items():
        node_id = node.get("node_id")
        if node_id != key:
            issues.append(make_issue("warning", "node_id_key_mismatch", f"Node key '{key}' has node_id '{node_id}'.", f"$.nodes.{key}.node_id"))
        for field, target in collect_targets(node):
            if not target:
                issues.append(make_issue("error", "empty_target", f"Empty target in {field}.", f"$.nodes.{key}.{field}"))
            elif target not in nodes:
                issues.append(make_issue("error", "missing_target", f"Target '{target}' does not exist.", f"$.nodes.{key}.{field}"))
        if node.get("is_ending") and not node.get("ending"):
            issues.append(make_issue("warning", "ending_without_payload", "Ending node lacks ending payload.", f"$.nodes.{key}.ending"))
        if node.get("choices") and node.get("next"):
            issues.append(make_issue("warning", "choice_node_has_next", "Node has both choices and next; runtime should prefer choices.", f"$.nodes.{key}"))

    if start in nodes:
        reachable = reachable_nodes(start, nodes)
        for node_id in sorted(set(nodes) - reachable):
            issues.append(make_issue("warning", "unreachable_node", f"Node '{node_id}' is not reachable from start_node_id.", f"$.nodes.{node_id}"))
        ending_ids = [node_id for node_id, node in nodes.items() if node.get("is_ending") or node.get("ending")]
        reachable_endings = [node_id for node_id in ending_ids if node_id in reachable]
        if not ending_ids:
            issues.append(make_issue("error", "no_endings", "Package has no ending nodes.", "$.nodes"))
        elif not reachable_endings:
            issues.append(make_issue("error", "no_reachable_endings", "Package has endings but none are reachable from start_node_id.", "$.nodes"))

    incoming: dict[str, set[str]] = defaultdict(set)
    for node_id, node in nodes.items():
        for _, target in collect_targets(node):
            incoming[target].add(node_id)
    for node_id, node in nodes.items():
        if node_id != start and not incoming.get(node_id):
            severity = "warning" if node.get("is_ending") else "warning"
            issues.append(make_issue(severity, "no_incoming_edge", f"Node '{node_id}' has no incoming edge.", f"$.nodes.{node_id}"))

    return issues


def collect_condition_refs(condition: Any, refs: dict[str, set[str]]) -> None:
    if condition is None:
        return
    if isinstance(condition, str):
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", condition):
            refs["string_tokens"].add(token)
        return
    if not isinstance(condition, dict):
        return
    if "flag" in condition:
        refs["flags_read"].add(str(condition["flag"]))
    if "var" in condition:
        refs["vars_read"].add(str(condition["var"]))
    for key in ["all", "any"]:
        for item in condition.get(key) or []:
            collect_condition_refs(item, refs)
    if "not" in condition:
        collect_condition_refs(condition["not"], refs)


def validate_state_usage(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    state = data.get("state") or {}
    values = set((state.get("values") or {}).keys())
    variables = set((state.get("variables") or {}).keys())
    initial_flags = set(state.get("flags") or [])
    primary_value_id = ((state.get("primary_value") or {}).get("id") or "")

    refs: dict[str, set[str]] = defaultdict(set)
    achievements = set((data.get("achievements") or {}).keys())

    for node_id, node in (data.get("nodes") or {}).items():
        for route in node.get("routes") or []:
            collect_condition_refs(route.get("condition"), refs)
        for choice_index, choice in enumerate(node.get("choices") or []):
            collect_condition_refs(choice.get("condition"), refs)
            changes = choice.get("changes") or {}
            if "primary_value_delta" in changes or "primary_value_set" in changes:
                refs["primary_value_written"].add(primary_value_id)
            for key in (changes.get("values_delta") or {}):
                refs["values_written"].add(key)
                if key not in values:
                    issues.append(make_issue("warning", "unknown_value_write", f"Choice writes unknown value '{key}'.", f"$.nodes.{node_id}.choices[{choice_index}].changes.values_delta.{key}"))
            for key in (changes.get("set_variables") or {}):
                refs["vars_written"].add(key)
            for flag in changes.get("add_flags") or []:
                refs["flags_written"].add(flag)
            for flag in changes.get("remove_flags") or []:
                refs["flags_written"].add(flag)
            for ach in changes.get("unlock_achievements") or []:
                if ach not in achievements:
                    issues.append(make_issue("warning", "unknown_achievement", f"Choice unlocks unknown achievement '{ach}'.", f"$.nodes.{node_id}.choices[{choice_index}.changes.unlock_achievements]"))
            if choice.get("locked_hint") and not choice.get("condition"):
                issues.append(make_issue("warning", "locked_hint_without_condition", "Choice has locked_hint but no condition.", f"$.nodes.{node_id}.choices[{choice_index}]"))
            if len(node.get("choices") or []) > 1 and not (choice.get("changes") or choice.get("callback_node_id") or choice.get("effects")):
                issues.append(make_issue("warning", "choice_without_visible_consequence", "Choice has no changes, callback node, or effects.", f"$.nodes.{node_id}.choices[{choice_index}]"))

    unknown_vars = refs["vars_read"] - variables - values - {primary_value_id}
    for key in sorted(unknown_vars):
        issues.append(make_issue("warning", "unknown_condition_variable", f"Condition reads unknown variable/value '{key}'."))

    read_flags = refs["flags_read"]
    written_flags = refs["flags_written"] | initial_flags
    for flag in sorted(read_flags - written_flags):
        issues.append(make_issue("warning", "flag_read_never_written", f"Flag '{flag}' is read but never initialized or written."))
    for flag in sorted(refs["flags_written"] - read_flags):
        issues.append(make_issue("warning", "flag_written_never_read", f"Flag '{flag}' is written but never read by a condition."))

    for key in sorted(values - refs["values_written"] - refs["vars_read"]):
        issues.append(make_issue("warning", "value_unused", f"Value '{key}' is initialized but not clearly written/read by choices or conditions."))

    return issues


def asset_refs_from_package(data: dict[str, Any]) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    cover = ((data.get("home") or {}).get("cover") or {}).get("cover_asset_id")
    if cover:
        refs.append(("$.home.cover.cover_asset_id", cover))
    for scene_id, scene in (data.get("scenes") or {}).items():
        if scene.get("background_asset_id"):
            refs.append((f"$.scenes.{scene_id}.background_asset_id", scene["background_asset_id"]))
    for char_id, char in (data.get("characters") or {}).items():
        for index, portrait in enumerate(char.get("portraits") or []):
            if portrait.get("asset_id"):
                refs.append((f"$.characters.{char_id}.portraits[{index}].asset_id", portrait["asset_id"]))
    for node_id, node in (data.get("nodes") or {}).items():
        if node.get("background_asset_id"):
            refs.append((f"$.nodes.{node_id}.background_asset_id", node["background_asset_id"]))
        for index, layer in enumerate(node.get("character_layers") or []):
            if layer.get("asset_id"):
                refs.append((f"$.nodes.{node_id}.character_layers[{index}].asset_id", layer["asset_id"]))
        for index, media in enumerate(node.get("media") or []):
            if media.get("asset_id"):
                refs.append((f"$.nodes.{node_id}.media[{index}].asset_id", media["asset_id"]))
        for index, segment in enumerate(node.get("segments") or []):
            if segment.get("asset_id"):
                refs.append((f"$.nodes.{node_id}.segments[{index}].asset_id", segment["asset_id"]))
            for layer_index, layer in enumerate(segment.get("show_layers") or []):
                if layer.get("asset_id"):
                    refs.append((f"$.nodes.{node_id}.segments[{index}].show_layers[{layer_index}].asset_id", layer["asset_id"]))
    return refs


def validate_assets(data: dict[str, Any], package_path: Path, assets_complete: bool) -> list[Issue]:
    issues: list[Issue] = []
    assets = data.get("assets") or {}
    asset_base = (((data.get("engine_contract") or {}).get("asset_base_path")) or "").strip()
    base_path = Path(asset_base)
    if not base_path.is_absolute():
        base_path = package_path.parent / base_path

    for key, asset in assets.items():
        if asset.get("asset_id") != key:
            issues.append(make_issue("warning", "asset_id_key_mismatch", f"Asset key '{key}' has asset_id '{asset.get('asset_id')}'.", f"$.assets.{key}.asset_id"))
        path = str(asset.get("path") or "")
        if path.startswith("http://") or path.startswith("https://"):
            issues.append(make_issue("warning", "remote_asset_path", f"Asset '{key}' uses a remote URL; production packages should use local paths.", f"$.assets.{key}.path"))
        if asset.get("required") and assets_complete and path and not path.startswith(("http://", "https://")):
            candidate = base_path / path
            if not candidate.exists():
                issues.append(make_issue("error", "missing_required_asset_file", f"Required asset file does not exist: {candidate}", f"$.assets.{key}.path"))

    for path, asset_id in asset_refs_from_package(data):
        if asset_id not in assets:
            issues.append(make_issue("error", "missing_asset_reference", f"Referenced asset '{asset_id}' is not declared in assets.", path))

    used_assets = {asset_id for _, asset_id in asset_refs_from_package(data)}
    for asset_id, asset in assets.items():
        usage = set(asset.get("usage") or [])
        if asset_id not in used_assets and "qa_only" not in usage:
            issues.append(make_issue("warning", "unused_asset", f"Asset '{asset_id}' is declared but not referenced by runtime package.", f"$.assets.{asset_id}"))

    return issues


def validate_secret_hygiene(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for path, text in walk_strings(data):
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                issues.append(make_issue("error", "secret_leak", "Possible API key or bearer token found in package string.", path))
                break
        for pattern in SIGNED_URL_PATTERNS:
            if pattern.search(text):
                issues.append(make_issue("error", "signed_url", "Signed temporary provider URL found; download locally and replace with relative path.", path))
                break
    return issues


def visible_text_fields(data: dict[str, Any]):
    meta = data.get("meta") or {}
    for key in ["title", "subtitle", "tagline", "description"]:
        value = meta.get(key)
        if isinstance(value, str):
            yield f"$.meta.{key}", value

    home = data.get("home") or {}
    for key in ["title", "subtitle", "start_label", "continue_label"]:
        value = home.get(key)
        if isinstance(value, str):
            yield f"$.home.{key}", value

    for node_id, node in (data.get("nodes") or {}).items():
        for key in ["title", "chapter_title"]:
            value = node.get(key)
            if isinstance(value, str):
                yield f"$.nodes.{node_id}.{key}", value
        for segment_index, segment in enumerate(node.get("segments") or []):
            value = segment.get("text")
            if isinstance(value, str):
                yield f"$.nodes.{node_id}.segments[{segment_index}].text", value
        for choice_index, choice in enumerate(node.get("choices") or []):
            for key in ["label", "disabled_hint"]:
                value = choice.get(key)
                if isinstance(value, str):
                    yield f"$.nodes.{node_id}.choices[{choice_index}].{key}", value
        ending = node.get("ending") or {}
        if isinstance(ending, dict):
            for key in ["title", "subtitle", "body", "cta_label"]:
                value = ending.get(key)
                if isinstance(value, str):
                    yield f"$.nodes.{node_id}.ending.{key}", value


def validate_language_hygiene(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    language = ((data.get("meta") or {}).get("language") or "").lower()
    if not language.startswith("zh"):
        return issues

    english_heavy: list[tuple[str, str, int, int]] = []
    for path, text in visible_text_fields(data):
        if not text.strip():
            continue
        for pattern in PLAYER_TEXT_LABEL_PATTERNS:
            if pattern.search(text):
                issues.append(
                    make_issue(
                        "error",
                        "player_text_label_leak",
                        "Player-facing text contains structural/debug labels; move these into runtime fields.",
                        path,
                        "Remove labels like (Narration), (Dialogue), (System), [Routing], and [If ...] from visible text.",
                    )
                )
                break
        english_words = ENGLISH_WORD_PATTERN.findall(text)
        cjk_chars = CJK_PATTERN.findall(text)
        if len(english_words) >= 4 and len(english_words) > len(cjk_chars):
            english_heavy.append((path, text, len(english_words), len(cjk_chars)))

    if english_heavy:
        sample_paths = ", ".join(path for path, *_ in english_heavy[:5])
        issues.append(
            make_issue(
                "error",
                "target_language_mismatch",
                f"Package language is zh-CN but {len(english_heavy)} player-facing fields appear to be primarily English. Examples: {sample_paths}",
                "$.meta.language",
                "Localize visible runtime text before publishing or previewing this package.",
            )
        )
    return issues


def shortest_path_to_first_choice(start: str, nodes: dict[str, Any]) -> list[str]:
    queue: deque[tuple[str, list[str]]] = deque([(start, [])])
    seen: set[str] = set()
    while queue:
        current, path = queue.popleft()
        if current in seen or current not in nodes:
            continue
        seen.add(current)
        new_path = path + [current]
        if nodes[current].get("choices"):
            return new_path
        for _, target in collect_targets(nodes[current]):
            if target and target not in seen:
                queue.append((target, new_path))
    return []


def validate_comprehension(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    nodes = data.get("nodes") or {}
    start = data.get("start_node_id", "")
    path = shortest_path_to_first_choice(start, nodes)
    if not path:
        return issues
    choice_node = nodes[path[-1]]
    prior_text = ""
    understandings: list[str] = []
    visible_characters: set[str] = set()
    for node_id in path:
        node = nodes[node_id]
        for segment in node.get("segments") or []:
            prior_text += segment.get("text", "") + "\n"
            if segment.get("speaker_id"):
                visible_characters.add(segment["speaker_id"])
        for layer in node.get("character_layers") or []:
            if layer.get("visible"):
                visible_characters.add(layer.get("character_id", ""))
        understandings.extend(((node.get("qa") or {}).get("player_must_understand")) or [])
    if len(prior_text) < 350:
        issues.append(make_issue("warning", "thin_opening_before_first_choice", "First choice may arrive before enough setup text.", f"$.nodes.{path[-1]}", "Ensure player identity, place, goal, cast, and pressure are clear before the first major choice."))
    if len(understandings) < 3:
        issues.append(make_issue("warning", "weak_understanding_before_first_choice", "Few player_must_understand facts are declared before first choice.", f"$.nodes.{path[-1]}"))
    if len(choice_node.get("choices") or []) > 1:
        for index, choice in enumerate(choice_node.get("choices") or []):
            if not (choice.get("changes") or choice.get("callback_node_id") or choice.get("effects")):
                issues.append(make_issue("warning", "first_choice_lacks_feedback", "A first major choice lacks visible callback/effect.", f"$.nodes.{path[-1]}.choices[{index}]"))
    return issues


def write_human_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Runtime Package Validation Report",
        "",
        f"- Package: `{report['package_path']}`",
        f"- Errors: {report['summary']['errors']}",
        f"- Warnings: {report['summary']['warnings']}",
        "",
    ]
    grouped: dict[str, list[Issue]] = defaultdict(list)
    for item in report["issues"]:
        grouped[item["severity"]].append(item)
    for severity in ["error", "warning", "info"]:
        items = grouped.get(severity, [])
        if not items:
            continue
        lines.append(f"## {severity.title()}s")
        lines.append("")
        for item in items:
            where = f" `{item['path']}`" if item.get("path") else ""
            lines.append(f"- **{item['category']}**{where}: {item['message']}")
            if item.get("suggestion"):
                lines.append(f"  Suggestion: {item['suggestion']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate runtime_game_package.json")
    parser.add_argument("package", type=Path)
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "schemas" / "runtime_game_package.schema.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--human-output", type=Path)
    parser.add_argument("--assets-complete", action="store_true", help="Require required local asset files to exist.")
    parser.add_argument("--fail-on-warning", action="store_true")
    args = parser.parse_args()

    try:
        data = load_json(args.package)
    except Exception as exc:
        print(f"ERROR: failed to read package: {exc}", file=sys.stderr)
        return 1

    issues: list[Issue] = []
    issues.extend(validate_schema_if_available(data, args.schema if args.schema.exists() else None))
    issues.extend(required_shape_checks(data))
    issues.extend(validate_graph(data))
    issues.extend(validate_state_usage(data))
    issues.extend(validate_assets(data, args.package, args.assets_complete))
    issues.extend(validate_secret_hygiene(data))
    issues.extend(validate_language_hygiene(data))
    issues.extend(validate_comprehension(data))

    summary = {
        "errors": sum(1 for item in issues if item["severity"] == "error"),
        "warnings": sum(1 for item in issues if item["severity"] == "warning"),
        "issue_count": len(issues),
    }
    report = {
        "package_path": str(args.package),
        "schema_path": str(args.schema),
        "assets_complete": args.assets_complete,
        "summary": summary,
        "issues": issues,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    if args.human_output:
        args.human_output.parent.mkdir(parents=True, exist_ok=True)
        args.human_output.write_text(write_human_report(report), encoding="utf-8")
    print(text)
    if summary["errors"] or (args.fail_on_warning and summary["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
