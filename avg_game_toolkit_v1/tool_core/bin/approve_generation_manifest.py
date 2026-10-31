#!/usr/bin/env python3
"""Record explicit paid-generation approval in a generation manifest."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Set execution_policy.paid_generation_allowed=true after explicit approval")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Defaults to in-place update.")
    parser.add_argument("--approval-note", required=True, help="Human-readable approval note. Do not include secrets.")
    parser.add_argument("--approved-by", default="planner")
    args = parser.parse_args()

    if not args.approval_note.strip():
        raise SystemExit("--approval-note must not be empty")
    manifest = load_json(args.manifest)
    policy = manifest.setdefault("execution_policy", {})
    policy["paid_generation_allowed"] = True
    policy["approved_at"] = datetime.now(timezone.utc).isoformat()
    policy["approved_by"] = args.approved_by
    policy["approval_note"] = args.approval_note.strip()
    policy.setdefault("this_file_is_safe_to_commit", True)
    policy.setdefault("secrets_policy", "Secrets must be read from environment variables only during a later execution step.")
    output = args.output or args.manifest
    write_json(output, manifest)
    print(json.dumps({
        "manifest": str(output),
        "paid_generation_allowed": True,
        "approved_by": policy["approved_by"],
        "approved_at": policy["approved_at"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
