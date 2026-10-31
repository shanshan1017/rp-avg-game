#!/usr/bin/env python3
"""Validate the Codex subagent supervision board without external packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


VALID_STATUSES = {"launched", "running", "completed", "blocked", "failed", "closed"}
REQUIRED_ROOT = {"project_id", "protocol", "updated_at", "agents"}
REQUIRED_AGENT = {
    "agent_id",
    "nickname",
    "role",
    "task",
    "owned_paths",
    "forbidden_paths",
    "status",
    "started_at",
    "last_checked_at",
    "completed_at",
    "result_summary",
    "result_files",
    "next_action",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(data: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    missing_root = sorted(REQUIRED_ROOT - set(data))
    for key in missing_root:
        findings.append({"severity": "blocker", "path": key, "message": "Missing root field."})
    extra_root = sorted(set(data) - REQUIRED_ROOT)
    for key in extra_root:
        findings.append({"severity": "major", "path": key, "message": "Unexpected root field."})
    agents = data.get("agents")
    if not isinstance(agents, list):
        findings.append({"severity": "blocker", "path": "agents", "message": "agents must be an array."})
        agents = []
    seen: set[str] = set()
    for index, agent in enumerate(agents):
        prefix = f"agents[{index}]"
        if not isinstance(agent, dict):
            findings.append({"severity": "blocker", "path": prefix, "message": "agent must be an object."})
            continue
        missing = sorted(REQUIRED_AGENT - set(agent))
        for key in missing:
            findings.append({"severity": "blocker", "path": f"{prefix}.{key}", "message": "Missing agent field."})
        extra = sorted(set(agent) - REQUIRED_AGENT)
        for key in extra:
            findings.append({"severity": "major", "path": f"{prefix}.{key}", "message": "Unexpected agent field."})
        agent_id = str(agent.get("agent_id") or "")
        if agent_id in seen:
            findings.append({"severity": "blocker", "path": f"{prefix}.agent_id", "message": "Duplicate agent_id."})
        seen.add(agent_id)
        status = agent.get("status")
        if status not in VALID_STATUSES:
            findings.append({"severity": "blocker", "path": f"{prefix}.status", "message": f"Invalid status: {status}"})
        for key in ["owned_paths", "forbidden_paths", "result_files"]:
            if key in agent and not isinstance(agent[key], list):
                findings.append({"severity": "blocker", "path": f"{prefix}.{key}", "message": "Field must be an array."})
    blockers = sum(1 for finding in findings if finding["severity"] == "blocker")
    majors = sum(1 for finding in findings if finding["severity"] == "major")
    return {
        "status": "failed" if blockers or majors else "passed",
        "agent_count": len(agents),
        "blockers": blockers,
        "majors": majors,
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate reports/codex_agent_supervision.json")
    parser.add_argument("board", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(load_json(args.board))
    if args.report:
        write_json(args.report, report)
    print(json.dumps({k: report[k] for k in ["status", "agent_count", "blockers", "majors"]}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
