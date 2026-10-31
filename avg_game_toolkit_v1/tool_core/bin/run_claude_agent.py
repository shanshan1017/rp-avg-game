#!/usr/bin/env python3
"""Run one Claude Code agent in an isolated file workspace.

The Planner owns canonical files. This wrapper copies handoff/context files into
an agent-specific workspace, invokes `claude --bare --print`, and leaves all
deliverables in the agent outbox.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_TOOLS = "Bash,Read,LS"


ROLE_CONTRACT = """You are a scoped Claude Code worker inside an isolated workspace.

Hard rules:
- Treat ./inbox as read-only context.
- Write deliverables only under ./outbox.
- Use ./scratch only for temporary notes.
- Do not ask to read or edit files outside this workspace.
- If you use Bash, only write under ./outbox or ./scratch. Do not inspect
  directories outside this workspace.
- Do not redesign other disciplines. Report cross-discipline conflicts instead.
- Do not include secrets, API keys, provider signed URLs, or unrelated project data.
- For long tasks, append brief progress checkpoints to ./scratch/progress.md
  after each major section so the launcher can distinguish active work from a
  stalled process.
- End with a concise list of files written.

If the task is impossible with the inbox context, write an outbox/blocker_report.md
explaining the missing dependency and stop.
"""


def copy_context_file(source: Path, inbox: Path) -> Path:
    if not source.exists():
        raise FileNotFoundError(source)
    target = inbox / source.name
    shutil.copy2(source, target)
    return target


def build_task(
    role: str,
    copied_files: list[Path],
    expected_outputs: list[str],
    attempt: int = 1,
    attempts: int = 1,
    retry_reason: str = "",
) -> str:
    lines = [
        f"# Task: {role}",
        "",
        "Read the files in `./inbox` and produce the requested deliverables.",
        "Write all deliverables into `./outbox`.",
        "",
        "## Inbox Files",
    ]
    for file_path in copied_files:
        lines.append(f"- `inbox/{file_path.name}`")
    if expected_outputs:
        lines.extend(["", "## Expected Outbox Files"])
        for output in expected_outputs:
            lines.append(f"- `outbox/{output}`")
    lines.extend(
        [
            "",
            "## Execution Attempt",
            "",
            f"- Attempt: {attempt} of {attempts}",
        ]
    )
    if retry_reason:
        lines.append(f"- Previous attempt issue: {retry_reason}")
        lines.append("- Reuse any valid partial work already present in `./outbox` only if it is correct and complete.")
    lines.extend(
        [
            "",
            "## Reporting",
            "",
            "Your outbox must include an agent report describing assumptions, produced files, conflicts, missing dependencies, and requested Planner decisions.",
            "",
            "## Long Task Heartbeat",
            "",
            "If the task is large, update `scratch/progress.md` after each major section or write partial deliverables under `outbox`. The launcher treats stdout/stderr output and changes under `outbox` or `scratch` as progress.",
        ]
    )
    return "\n".join(lines)


def output_status(outbox: Path, expected_outputs: list[str]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for output in expected_outputs:
        path = outbox / output
        if not path.exists():
            missing.append(f"{output} (missing)")
        elif path.is_file() and path.stat().st_size == 0:
            missing.append(f"{output} (empty)")
    return not missing, missing


def latest_file_mtime(roots: list[Path]) -> float:
    latest = 0.0
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            try:
                if path.is_file():
                    latest = max(latest, path.stat().st_mtime)
            except OSError:
                continue
    return latest


def kill_process_group(process: subprocess.Popen[str], sig: signal.Signals) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def reader_thread(stream, stream_name: str, events: "queue.Queue[tuple[str, str | None]]") -> None:
    try:
        for line in iter(stream.readline, ""):
            events.put((stream_name, line))
    finally:
        events.put((stream_name, None))


def write_progress_event(progress_log: Path, event: dict) -> None:
    with progress_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_command(
    command: list[str],
    cwd: Path,
    idle_timeout_sec: int,
    hard_timeout_sec: int,
    progress_roots: list[Path],
    progress_log: Path,
    expected_outbox: Path | None = None,
    expected_outputs: list[str] | None = None,
    completion_stable_sec: int = 15,
) -> tuple[int, str, str, bool, str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        start_new_session=True,
    )
    assert process.stdout is not None
    assert process.stderr is not None

    events: "queue.Queue[tuple[str, str | None]]" = queue.Queue()
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    threads = [
        threading.Thread(target=reader_thread, args=(process.stdout, "stdout", events), daemon=True),
        threading.Thread(target=reader_thread, args=(process.stderr, "stderr", events), daemon=True),
    ]
    for thread in threads:
        thread.start()

    start = time.monotonic()
    last_progress = start
    last_scan = start
    last_mtime = latest_file_mtime(progress_roots)
    timeout_reason = ""
    early_complete_reason = ""
    outputs_complete_since = 0.0
    write_progress_event(
        progress_log,
        {
            "type": "started",
            "at": datetime.now(timezone.utc).isoformat(),
            "idle_timeout_sec": idle_timeout_sec,
            "hard_timeout_sec": hard_timeout_sec,
        },
    )

    while True:
        now = time.monotonic()
        try:
            stream_name, line = events.get(timeout=1)
            if line is not None:
                if stream_name == "stdout":
                    stdout_parts.append(line)
                else:
                    stderr_parts.append(line)
                last_progress = time.monotonic()
                write_progress_event(
                    progress_log,
                    {
                        "type": stream_name,
                        "at": datetime.now(timezone.utc).isoformat(),
                        "bytes": len(line.encode("utf-8")),
                    },
                )
        except queue.Empty:
            pass

        now = time.monotonic()
        if now - last_scan >= 5:
            current_mtime = latest_file_mtime(progress_roots)
            if current_mtime > last_mtime:
                last_mtime = current_mtime
                last_progress = now
                outputs_complete_since = 0.0
                write_progress_event(
                    progress_log,
                    {
                        "type": "filesystem_progress",
                        "at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            if expected_outbox and expected_outputs:
                outputs_ok, _ = output_status(expected_outbox, expected_outputs)
                if outputs_ok:
                    if not outputs_complete_since:
                        outputs_complete_since = now
                    elif now - outputs_complete_since >= completion_stable_sec:
                        early_complete_reason = f"expected outputs complete and stable for {completion_stable_sec}s"
                        break
                else:
                    outputs_complete_since = 0.0
            last_scan = now

        if process.poll() is not None:
            break
        if hard_timeout_sec > 0 and now - start > hard_timeout_sec:
            timeout_reason = f"hard timeout after {hard_timeout_sec}s"
            break
        if idle_timeout_sec > 0 and now - last_progress > idle_timeout_sec:
            timeout_reason = f"idle timeout after {idle_timeout_sec}s without stdout/stderr or outbox/scratch changes"
            break

    if timeout_reason:
        kill_process_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kill_process_group(process, signal.SIGKILL)
            process.wait()
        write_progress_event(
            progress_log,
            {
                "type": "timeout",
                "at": datetime.now(timezone.utc).isoformat(),
                "reason": timeout_reason,
            },
        )
    elif early_complete_reason and process.poll() is None:
        kill_process_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kill_process_group(process, signal.SIGKILL)
            process.wait()
        write_progress_event(
            progress_log,
            {
                "type": "early_complete",
                "at": datetime.now(timezone.utc).isoformat(),
                "reason": early_complete_reason,
            },
        )

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            stream_name, line = events.get_nowait()
        except queue.Empty:
            break
        if line is None:
            continue
        if stream_name == "stdout":
            stdout_parts.append(line)
        else:
            stderr_parts.append(line)

    for thread in threads:
        thread.join(timeout=1)

    while True:
        try:
            stream_name, line = events.get_nowait()
        except queue.Empty:
            break
        if line is None:
            continue
        if stream_name == "stdout":
            stdout_parts.append(line)
        else:
            stderr_parts.append(line)

    stdout = "".join(stdout_parts)
    stderr = "".join(stderr_parts)
    if timeout_reason:
        return 124, stdout, stderr, True, timeout_reason
    if early_complete_reason:
        return 0, stdout, stderr, False, early_complete_reason
    return process.returncode or 0, stdout, stderr, False, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a scoped Claude Code agent")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--role", required=True)
    parser.add_argument("--agent-id", default="")
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--context", action="append", default=[], type=Path)
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default="")
    parser.add_argument("--max-budget-usd", default="")
    parser.add_argument("--tools", default=DEFAULT_TOOLS)
    parser.add_argument("--permission-mode", default="bypassPermissions")
    parser.add_argument("--attempts", default=2, type=int)
    parser.add_argument(
        "--timeout-sec",
        default=900,
        type=int,
        help="Idle timeout. The process may run longer if stdout/stderr or outbox/scratch files keep changing.",
    )
    parser.add_argument(
        "--idle-timeout-sec",
        default=0,
        type=int,
        help="Override idle timeout. Defaults to --timeout-sec for backward-compatible command lines.",
    )
    parser.add_argument(
        "--hard-timeout-sec",
        default=7200,
        type=int,
        help="Wall-clock safety cap. Use 0 to disable.",
    )
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    agent_name = args.agent_id or args.role
    root = args.run_dir / "agents" / agent_name / "workspace"
    inbox = root / "inbox"
    outbox = root / "outbox"
    scratch = root / "scratch"
    logs = root / "logs"
    for directory in (inbox, outbox, scratch, logs):
        directory.mkdir(parents=True, exist_ok=True)

    copied: list[Path] = []
    copied.append(copy_context_file(args.handoff, inbox))
    for context in args.context:
        copied.append(copy_context_file(context, inbox))

    contract_path = root / "ROLE_CONTRACT.md"
    task_path = root / "TASK.md"
    contract_path.write_text(ROLE_CONTRACT, encoding="utf-8")
    task_path.write_text(
        build_task(args.role, copied, args.expect, attempts=max(args.attempts, 1)),
        encoding="utf-8",
    )

    metadata = {
        "role": args.role,
        "agent_id": agent_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "workspace": str(root),
        "handoff": str(args.handoff),
        "context": [str(path) for path in args.context],
        "expected_outputs": args.expect,
        "attempts": args.attempts,
        "idle_timeout_sec": args.idle_timeout_sec or args.timeout_sec,
        "hard_timeout_sec": args.hard_timeout_sec,
        "tools": args.tools,
        "permission_mode": args.permission_mode,
    }
    (logs / "run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.dry_run:
        print(f"Prepared workspace: {root}")
        print(f"Task file: {task_path}")
        print("Dry run only; Claude Code was not invoked.")
        return 0

    attempts = max(args.attempts, 1)
    attempt_records: list[dict] = []
    retry_reason = ""
    for attempt in range(1, attempts + 1):
        already_ok, already_missing = output_status(outbox, args.expect)
        if args.expect and already_ok:
            print(f"Expected outputs already present in {outbox}; skipping attempt {attempt}.")
            (logs / "attempt_summary.json").write_text(
                json.dumps(attempt_records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return 0

        task_text = build_task(args.role, copied, args.expect, attempt, attempts, retry_reason)
        task_path.write_text(task_text, encoding="utf-8")

        command = [
            args.claude_bin,
            "--bare",
            "--print",
            "--no-session-persistence",
            "--permission-mode",
            args.permission_mode,
            "--tools",
            args.tools,
            "--model",
            args.model,
        ]
        if args.effort:
            command.extend(["--effort", args.effort])
        if args.max_budget_usd:
            command.extend(["--max-budget-usd", args.max_budget_usd])
        command.extend(["--append-system-prompt", ROLE_CONTRACT, task_text])

        idle_timeout_sec = args.idle_timeout_sec or args.timeout_sec
        returncode, stdout, stderr, timed_out, timeout_reason = run_command(
            command,
            root,
            idle_timeout_sec,
            args.hard_timeout_sec,
            [outbox, scratch],
            logs / f"attempt_{attempt}_progress.jsonl",
            outbox,
            args.expect,
        )
        (logs / f"attempt_{attempt}_stdout.txt").write_text(stdout, encoding="utf-8")
        (logs / f"attempt_{attempt}_stderr.txt").write_text(stderr, encoding="utf-8")

        outputs_ok, missing = output_status(outbox, args.expect)
        success = returncode == 0 and (outputs_ok or not args.expect)
        record = {
            "attempt": attempt,
            "returncode": returncode,
            "timed_out": timed_out,
            "timeout_reason": timeout_reason,
            "outputs_ok": outputs_ok,
            "missing_outputs": missing,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        attempt_records.append(record)
        (logs / "attempt_summary.json").write_text(
            json.dumps(attempt_records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        if success:
            (logs / "stdout.txt").write_text(stdout, encoding="utf-8")
            (logs / "stderr.txt").write_text(stderr, encoding="utf-8")
            print(stdout)
            return 0

        if timed_out:
            retry_reason = f"attempt {attempt} timed out: {timeout_reason}"
        elif returncode != 0:
            retry_reason = f"attempt {attempt} exited with code {returncode}"
        else:
            retry_reason = f"attempt {attempt} did not produce expected outputs: {', '.join(missing)}"

        print(f"Attempt {attempt} failed: {retry_reason}", file=sys.stderr)

    final_ok, final_missing = output_status(outbox, args.expect)
    if args.expect and final_ok:
        return 0
    print(
        f"Agent {agent_name} failed after {attempts} attempt(s). Missing outputs: {', '.join(final_missing) or 'none'}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
