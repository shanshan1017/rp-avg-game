#!/usr/bin/env python3
"""Initialize a canonical game-case workspace outside the reusable tool."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_DIRS = [
    "intake",
    "planner",
    "agents",
    "authoring",
    "playtest",
    "prompts",
    "manifests",
    "assets",
    "runtime_package",
    "runtime_preview",
    "reports",
]


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_\-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        raise ValueError("project_id cannot be empty after sanitization")
    return cleaned


def readme(project_id: str) -> str:
    return f"""# {project_id}

This game case was initialized by `cross_disciplinary_coherence_v1`.

## Canonical Folders

- `intake/`: user brief, permission boundaries, budget/generation approval.
- `planner/`: Planner-owned canonical control files and handoffs.
- `agents/`: isolated Claude Code agent workspaces and reports.
- `authoring/`: story graph, character/world bible, mechanics, scene dramaturgy, hybrid script.
- `playtest/`: text playtest packs, transcripts, duration reports.
- `prompts/`: prompt packs for image/video/audio/UI.
- `manifests/`: sanitized generation manifests and local asset manifests.
- `assets/`: downloaded/generated local assets only; no temporary signed URLs.
- `runtime_package/`: `runtime_game_package.json`, compile reports, validator reports.
- `runtime_preview/`: fixed runtime preview files for this case.
- `reports/`: final checker, Planner integration, QA, and release reports.

## Source Of Truth

Planner owns canonical files. Worker agents write to their own `agents/<agent>/workspace/outbox/`; Planner reviews and promotes accepted outputs into `authoring/`, `prompts/`, `manifests/`, or `runtime_package/`.

## Generation Policy

Paid image/video/audio generation is disabled unless explicitly approved in `intake/` and command-line execution flags. Secrets must come from environment variables and must never be written into this folder.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a game-case workspace")
    parser.add_argument("project_id")
    parser.add_argument("--games-root", type=Path, default=Path("interactive_video_game/games"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    project_id = safe_id(args.project_id)
    root = args.games_root / project_id
    root.mkdir(parents=True, exist_ok=True)
    for dirname in DEFAULT_DIRS:
        (root / dirname).mkdir(exist_ok=True)
    readme_path = root / "README.md"
    if args.force or not readme_path.exists():
        readme_path.write_text(readme(project_id), encoding="utf-8")
    metadata = {
        "project_id": project_id,
        "root": str(root),
        "directories": DEFAULT_DIRS,
        "paid_generation_allowed": False,
    }
    (root / "intake" / "case_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

