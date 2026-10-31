#!/usr/bin/env python3
"""Run the reusable cross-disciplinary game-production pipeline.

This orchestrator connects tool-layer stages and can prepare or run isolated
Claude Code worker stages. Agent stages default to prepare-only mode; use
`--run-agents` to invoke Claude Code. Paid generation belongs to a later
explicit execution stage after user approval.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOOL_ROOT = Path(__file__).resolve().parents[1]
BIN = TOOL_ROOT / "bin"
DEFAULT_GAMES_ROOT = TOOL_ROOT.parent.parent / "games"
RUNTIME_TEMPLATE = TOOL_ROOT / "runtime" / "fixed_avg_runtime"
AGENT_INSTRUCTIONS = TOOL_ROOT / "agent_instructions"

TOOL_STAGES = [
    "init",
    "compile",
    "runtime_enrich",
    "validate",
    "manifest",
    "generate_assets",
    "runtime_preview",
    "index",
]

AGENT_STAGE_CONFIG: dict[str, dict[str, Any]] = {
    "plan": {
        "role": "planner",
        "instruction": "planner.md",
        "agent_id": "planner",
        "expected": ["agent_report.json", "coherence_plan.json", "story_intention.json"],
        "purpose": "Create or revise the Planner-owned coherence plan and Story Intention Gate from available intake/context.",
        "schemas": ["project_intake.schema.json", "coherence_plan.schema.json", "story_intention.schema.json", "agent_report.schema.json"],
    },
    "story_graph": {
        "role": "story_graph_director",
        "instruction": "story_graph_director.md",
        "agent_id": "story_graph_director",
        "expected": ["agent_report.json", "story_graph_plan.json"],
        "purpose": "Produce the playable story graph, branch topology, route matrix, and media hooks from the approved Planner brief.",
        "schemas": ["story_graph_plan.schema.json", "story_intention.schema.json", "agent_report.schema.json"],
    },
    "world_character": {
        "role": "character_world",
        "instruction": "character_world_agent.md",
        "agent_id": "character_world",
        "expected": ["agent_report.json", "character_world_bible.json"],
        "purpose": "Produce character, location, prop, relationship, and knowledge continuity data.",
        "schemas": ["character_world_bible.schema.json", "agent_report.schema.json"],
    },
    "mechanics": {
        "role": "mechanics",
        "instruction": "mechanics_agent.md",
        "agent_id": "mechanics",
        "expected": ["agent_report.json", "mechanics_plan.json"],
        "purpose": "Define values, flags, gates, endings, failures, achievements, and visible choice echoes.",
        "schemas": ["story_graph_plan.schema.json", "runtime_game_package.schema.json", "agent_report.schema.json"],
    },
    "scene_dramaturgy": {
        "role": "scene_dramaturgy",
        "instruction": "scene_dramaturgy_agent.md",
        "agent_id": "scene_dramaturgy",
        "expected": ["agent_report.json", "scene_dramaturgy_plan.json"],
        "purpose": "Define scene-level wants, conflict, turns, segment budgets, first appearances, and callbacks.",
        "schemas": ["scene_dramaturgy_plan.schema.json", "story_graph_plan.schema.json", "agent_report.schema.json"],
    },
    "narrative": {
        "role": "narrative",
        "instruction": "narrative_writer.md",
        "agent_id": "narrative_writer",
        "expected": ["agent_report.json", "hybrid_script.json", "text_playtest_pack.json"],
        "purpose": "Write segmented player-facing prose, dialogue, messages, choice copy, endings, and text playtest cells.",
        "schemas": ["text_playtest_pack.schema.json", "media_hybrid_script.schema.json", "agent_report.schema.json"],
    },
    "art_video_ui_prompts": {
        "role": "art_video_ui",
        "instruction": "art_video_ui_agent.md",
        "agent_id": "art_video_ui",
        "expected": ["agent_report.json", "asset_plan.json", "prompt_pack.json"],
        "purpose": "Plan visual, video, and UI asset slots and provider-ready prompts without generating media.",
        "schemas": ["media_asset_plan.schema.json", "prompt_pack.schema.json", "agent_report.schema.json"],
    },
    "audio_prompts": {
        "role": "audio",
        "instruction": "audio_agent.md",
        "agent_id": "audio",
        "expected": ["agent_report.json", "audio_plan.json", "audio_prompt_pack.json"],
        "purpose": "Plan BGM, ambience, SFX, optional voice, and video-embedded audio prompt requirements.",
        "schemas": ["audio_plan.schema.json", "prompt_pack.schema.json", "agent_report.schema.json"],
    },
    "runtime_agent": {
        "role": "runtime",
        "instruction": "runtime_agent.md",
        "agent_id": "runtime",
        "expected": ["agent_report.json", "runtime_integration_plan.md"],
        "purpose": "Inspect whether approved artifacts can compile into the fixed runtime package and report runtime blockers.",
        "schemas": ["runtime_game_package.schema.json", "text_playtest_pack.schema.json", "agent_report.schema.json"],
    },
    "checker": {
        "role": "checker",
        "instruction": "checker_agent.md",
        "agent_id": "checker",
        "expected": ["agent_report.json", "coherence_audit_report.md"],
        "purpose": "Audit cross-disciplinary coherence, traceability, route/playability, player comprehension, and generation safety.",
        "schemas": ["coherence_matrix.schema.json", "runtime_game_package.schema.json", "agent_report.schema.json"],
    },
}

AGENT_STAGES = list(AGENT_STAGE_CONFIG)
ALL_STAGES = [
    "init",
    "plan",
    "story_graph",
    "world_character",
    "mechanics",
    "scene_dramaturgy",
    "narrative",
    "compile",
    "runtime_enrich",
    "validate",
    "runtime_preview",
    "runtime_agent",
    "art_video_ui_prompts",
    "audio_prompts",
    "manifest",
    "generate_assets",
    "checker",
    "index",
]

STAGE_DEPENDENCIES: dict[str, list[str]] = {
    "plan": ["init"],
    "story_graph": ["plan"],
    "world_character": ["story_graph"],
    "mechanics": ["story_graph"],
    "scene_dramaturgy": ["story_graph", "world_character", "mechanics"],
    "narrative": ["scene_dramaturgy"],
    "art_video_ui_prompts": ["narrative", "world_character"],
    "audio_prompts": ["narrative", "world_character"],
    "compile": ["narrative"],
    "runtime_enrich": ["compile", "world_character", "mechanics"],
    "validate": ["compile", "runtime_enrich"],
    "manifest": ["art_video_ui_prompts"],
    "generate_assets": ["manifest"],
    "runtime_preview": ["validate"],
    "runtime_agent": ["runtime_preview", "validate"],
    "checker": ["runtime_agent", "validate", "art_video_ui_prompts", "audio_prompts"],
}

FAST_STAGE_DEPENDENCIES: dict[str, list[str]] = {
    **STAGE_DEPENDENCIES,
    "world_character": ["plan"],
    "art_video_ui_prompts": ["scene_dramaturgy", "world_character"],
    "audio_prompts": ["scene_dramaturgy", "world_character"],
}

STANDARD_AGENT_MODEL = "claude-sonnet-4-6"
COMPLEX_AGENT_MODEL = "claude-opus-4-7"
COMPLEX_AGENT_STAGES = {
    "plan",
    "story_graph",
    "scene_dramaturgy",
    "narrative",
    "checker",
}

PROMOTION_MAP: dict[str, dict[str, str]] = {
    "plan": {
        "coherence_plan.json": "planner/coherence_plan.json",
        "story_intention.json": "planner/story_intention.json",
    },
    "story_graph": {
        "story_graph_plan.json": "authoring/story_graph_plan.json",
    },
    "world_character": {
        "character_world_bible.json": "authoring/character_world_bible.json",
    },
    "mechanics": {
        "mechanics_plan.json": "authoring/mechanics_plan.json",
    },
    "scene_dramaturgy": {
        "scene_dramaturgy_plan.json": "authoring/scene_dramaturgy_plan.json",
    },
    "narrative": {
        "hybrid_script.json": "authoring/hybrid_script.json",
        "text_playtest_pack.json": "playtest/text_playtest_pack.json",
    },
    "art_video_ui_prompts": {
        "asset_plan.json": "authoring/asset_plan.json",
        "prompt_pack.json": "prompts/prompt_pack.json",
    },
    "audio_prompts": {
        "audio_plan.json": "authoring/audio_plan.json",
        "audio_prompt_pack.json": "prompts/audio_prompt_pack.json",
    },
    "runtime_agent": {
        "runtime_integration_plan.md": "reports/runtime_integration_plan.md",
    },
    "checker": {
        "coherence_audit_report.md": "reports/coherence_audit_report.md",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def discover_provider_env_file(args: argparse.Namespace, project_root: Path) -> Path | None:
    candidates: list[Path] = []
    if args.provider_env_file:
        candidates.append(args.provider_env_file)
    candidates.extend(
        [
            args.games_root.parent / ".secrets" / "provider_keys.env",
            project_root / ".secrets" / "provider_keys.env",
            Path.cwd() / ".secrets" / "provider_keys.env",
        ]
    )
    for path in candidates:
        if path.exists():
            return path.resolve()
    return candidates[0].resolve() if args.provider_env_file else None


def model_for_stage(stage: str, args: argparse.Namespace) -> str:
    if args.claude_model:
        return args.claude_model
    if args.agent_model_profile == "opus":
        return COMPLEX_AGENT_MODEL
    if args.agent_model_profile == "sonnet":
        return STANDARD_AGENT_MODEL
    if args.agent_model_profile == "mixed" and stage in COMPLEX_AGENT_STAGES:
        return COMPLEX_AGENT_MODEL
    return STANDARD_AGENT_MODEL


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def ensure_dirs(project_root: Path) -> None:
    for dirname in [
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
        "reports/pipeline_logs",
    ]:
        (project_root / dirname).mkdir(parents=True, exist_ok=True)


def candidate_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def discover_text_pack(project_root: Path) -> Path | None:
    return candidate_existing(
        [
            project_root / "playtest" / "text_playtest_pack.json",
            project_root / "playtest" / "text_playtest_pack_v5.json",
            project_root / "authoring" / "text_playtest_pack.json",
            project_root / "runtime_preview" / "game_data.json",
        ]
    )


def discover_prompt_pack(project_root: Path) -> Path | None:
    return candidate_existing(
        [
            project_root / "prompts" / "prompt_pack.json",
            project_root / "prompts" / "prompt_pack_v5.json",
            project_root / "authoring" / "prompt_pack.json",
        ]
    )


def unique_existing(paths: list[Path]) -> list[Path]:
    seen_names: set[str] = set()
    result: list[Path] = []
    for path in paths:
        if not path.exists() or path.name in seen_names:
            continue
        seen_names.add(path.name)
        result.append(path)
    return result


class Pipeline:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.project_root = (args.games_root / args.project_id).resolve()
        self.reports = self.project_root / "reports"
        self.log_dir = self.reports / "pipeline_logs"
        self.status_path = self.reports / "pipeline_status.json"
        self.artifact_index_path = self.reports / "artifact_index.json"
        self.status_lock = threading.RLock()
        self.status: dict[str, Any] = {
            "project_id": args.project_id,
            "project_root": str(self.project_root),
            "tool_root": str(TOOL_ROOT),
            "started_at": now_iso(),
            "paid_generation_allowed": False,
            "stages": {},
        }
        if self.status_path.exists() and not args.fresh:
            existing = load_json(self.status_path)
            existing.setdefault("stages", {})
            self.status = existing
            self.status["resumed_at"] = now_iso()
        self.status["last_run_started_at"] = now_iso()
        if args.allow_paid_generation:
            self.status["paid_generation_allowed"] = True
            self.status["paid_generation_approval_seen_at"] = now_iso()
        self.status["pipeline_profile"] = args.pipeline_profile
        self.status["context_mode"] = args.context_mode

    def save_status(self) -> None:
        with self.status_lock:
            write_json(self.status_path, self.status)

    def record_stage(
        self,
        stage: str,
        *,
        status: str,
        message: str = "",
        inputs: dict[str, str] | None = None,
        outputs: dict[str, str] | None = None,
        command: list[str] | None = None,
        returncode: int | None = None,
        started_at: str | None = None,
        ended_at: str | None = None,
        stdout_log: Path | None = None,
        stderr_log: Path | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "status": status,
            "message": message,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "updated_at": now_iso(),
        }
        if command is not None:
            entry["command"] = command
        if returncode is not None:
            entry["returncode"] = returncode
        if started_at:
            entry["started_at"] = started_at
        if ended_at:
            entry["ended_at"] = ended_at
        if stdout_log:
            entry["stdout_log"] = rel(stdout_log, self.project_root)
        if stderr_log:
            entry["stderr_log"] = rel(stderr_log, self.project_root)
        with self.status_lock:
            self.status.setdefault("stages", {})[stage] = entry
            self.save_status()

    def run_command(
        self,
        stage: str,
        command: list[str],
        inputs: dict[str, str],
        outputs: dict[str, str],
    ) -> int:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        started_at = now_iso()
        stdout_log = self.log_dir / f"{stage}_stdout.txt"
        stderr_log = self.log_dir / f"{stage}_stderr.txt"
        self.record_stage(
            stage,
            status="running",
            inputs=inputs,
            outputs=outputs,
            command=command,
            started_at=started_at,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
        )
        start = time.monotonic()
        result = subprocess.run(command, text=True, capture_output=True, cwd=Path.cwd())
        stdout_log.write_text(result.stdout, encoding="utf-8")
        stderr_log.write_text(result.stderr, encoding="utf-8")
        ended_at = now_iso()
        duration = round(time.monotonic() - start, 3)
        status = "completed" if result.returncode == 0 else "failed"
        message = f"completed in {duration}s" if result.returncode == 0 else f"failed in {duration}s"
        self.record_stage(
            stage,
            status=status,
            message=message,
            inputs=inputs,
            outputs=outputs,
            command=command,
            returncode=result.returncode,
            started_at=started_at,
            ended_at=ended_at,
            stdout_log=stdout_log,
            stderr_log=stderr_log,
        )
        if result.returncode != 0 and not self.args.keep_going:
            raise SystemExit(result.returncode)
        return result.returncode

    def stage_init(self) -> None:
        ensure_dirs(self.project_root)
        command = [
            sys.executable,
            str(BIN / "init_game_case.py"),
            self.args.project_id,
            "--games-root",
            str(self.args.games_root),
        ]
        if self.args.force_init:
            command.append("--force")
        self.run_command(
            "init",
            command,
            inputs={},
            outputs={
                "project_root": str(self.project_root),
                "case_metadata": str(self.project_root / "intake" / "case_metadata.json"),
                "readme": str(self.project_root / "README.md"),
            },
        )

    def stage_compile(self) -> None:
        text_pack = self.args.text_pack or discover_text_pack(self.project_root)
        if not text_pack:
            if self.args.require_text_pack:
                self.record_stage("compile", status="failed", message="No text playtest pack found.")
                if not self.args.keep_going:
                    raise SystemExit(2)
            else:
                self.record_stage("compile", status="skipped", message="No text playtest pack found.")
            return
        output = self.project_root / "runtime_package" / "runtime_game_package.json"
        report = self.project_root / "runtime_package" / "compile_report.json"
        command = [
            sys.executable,
            str(BIN / "compile_runtime_package.py"),
            "--text-pack",
            str(text_pack),
            "--output",
            str(output),
            "--report",
            str(report),
            "--asset-base-path",
            self.args.asset_base_path or f"../assets/{self.args.project_id}/",
        ]
        if self.args.cover_asset_id:
            command.extend(["--cover-asset-id", self.args.cover_asset_id])
        self.run_command(
            "compile",
            command,
            inputs={"text_pack": str(text_pack)},
            outputs={"runtime_package": str(output), "compile_report": str(report)},
        )

    def stage_validate(self) -> None:
        package = self.args.runtime_package or self.project_root / "runtime_package" / "runtime_game_package.json"
        if not package.exists():
            self.record_stage("validate", status="skipped", message=f"Runtime package not found: {package}")
            return
        output = self.project_root / "runtime_package" / "validation_report.json"
        human = self.project_root / "runtime_package" / "validation_report.md"
        command = [
            sys.executable,
            str(BIN / "validate_runtime_package.py"),
            str(package),
            "--output",
            str(output),
            "--human-output",
            str(human),
        ]
        if self.args.assets_complete:
            command.append("--assets-complete")
        if self.args.fail_on_warning:
            command.append("--fail-on-warning")
        self.run_command(
            "validate",
            command,
            inputs={"runtime_package": str(package)},
            outputs={"validation_report": str(output), "human_report": str(human)},
        )

    def stage_runtime_enrich(self) -> None:
        package = self.args.runtime_package or self.project_root / "runtime_package" / "runtime_game_package.json"
        if not package.exists():
            self.record_stage("runtime_enrich", status="skipped", message=f"Runtime package not found: {package}")
            return
        character_world = self.project_root / "authoring" / "character_world_bible.json"
        mechanics = self.project_root / "authoring" / "mechanics_plan.json"
        report = self.project_root / "runtime_package" / "runtime_enrich_report.json"
        preview_copy = self.project_root / "runtime_preview" / "runtime_game_package.json"
        command = [
            sys.executable,
            str(BIN / "enrich_runtime_package.py"),
            "--runtime-package",
            str(package),
            "--output",
            str(package),
            "--report",
            str(report),
            "--preview-copy",
            str(preview_copy),
        ]
        if character_world.exists():
            command.extend(["--character-world", str(character_world)])
        if mechanics.exists():
            command.extend(["--mechanics-plan", str(mechanics)])
        self.run_command(
            "runtime_enrich",
            command,
            inputs={
                "runtime_package": str(package),
                "character_world": str(character_world),
                "mechanics_plan": str(mechanics),
            },
            outputs={"runtime_package": str(package), "report": str(report)},
        )

    def stage_manifest(self) -> None:
        prompt_pack = self.args.prompt_pack or discover_prompt_pack(self.project_root)
        if not prompt_pack:
            self.record_stage("manifest", status="skipped", message="No prompt_pack.json found.")
            return
        asset_plan = self.project_root / "authoring" / "asset_plan.json"
        if asset_plan.exists():
            asset_plan_report = self.project_root / "reports" / "art_asset_plan_validation.json"
            validate_asset_plan_command = [
                sys.executable,
                str(BIN / "validate_art_asset_plan.py"),
                "--asset-plan",
                str(asset_plan),
                "--prompt-pack",
                str(prompt_pack),
                "--report",
                str(asset_plan_report),
            ]
            self.run_command(
                "validate_art_asset_plan",
                validate_asset_plan_command,
                inputs={"asset_plan": str(asset_plan), "prompt_pack": str(prompt_pack)},
                outputs={"validation_report": str(asset_plan_report)},
            )
        else:
            self.record_stage(
                "validate_art_asset_plan",
                status="skipped",
                message=f"Asset plan not found: {asset_plan}",
                inputs={"prompt_pack": str(prompt_pack)},
                outputs={},
            )
        manifest_input = prompt_pack
        if not self.args.no_harden_visual_prompts:
            hardened_pack = self.project_root / "prompts" / "prompt_pack.hard_rules.json"
            harden_command = [
                sys.executable,
                str(BIN / "harden_visual_prompt_pack.py"),
                "--input",
                str(prompt_pack),
                "--output",
                str(hardened_pack),
            ]
            self.run_command(
                "harden_visual_prompts",
                harden_command,
                inputs={"prompt_pack": str(prompt_pack)},
                outputs={"hardened_prompt_pack": str(hardened_pack)},
            )
            manifest_input = hardened_pack
        validation_report = self.project_root / "reports" / "visual_prompt_pack_validation.json"
        validate_command = [
            sys.executable,
            str(BIN / "validate_visual_prompt_pack.py"),
            "--prompt-pack",
            str(manifest_input),
            "--report",
            str(validation_report),
        ]
        self.run_command(
            "validate_visual_prompts",
            validate_command,
            inputs={"prompt_pack": str(manifest_input)},
            outputs={"validation_report": str(validation_report)},
        )
        output = self.project_root / "manifests" / "generation_manifest.json"
        command = [
            sys.executable,
            str(BIN / "build_generation_manifest.py"),
            "--prompt-pack",
            str(manifest_input),
            "--output",
            str(output),
            "--asset-root",
            str(Path("assets") / self.args.project_id),
        ]
        if asset_plan.exists():
            command.extend(["--asset-plan", str(asset_plan)])
        self.run_command(
            "manifest",
            command,
            inputs={"prompt_pack": str(manifest_input), "source_prompt_pack": str(prompt_pack)},
            outputs={"generation_manifest": str(output), "validation_report": str(validation_report)},
        )
        manifest_validation = self.project_root / "reports" / "generation_manifest_validation.json"
        validate_manifest_command = [
            sys.executable,
            str(BIN / "validate_generation_manifest_execution.py"),
            "--manifest",
            str(output),
            "--report",
            str(manifest_validation),
        ]
        self.run_command(
            "validate_generation_manifest",
            validate_manifest_command,
            inputs={"generation_manifest": str(output)},
            outputs={"validation_report": str(manifest_validation)},
        )

    def stage_generate_assets(self) -> None:
        manifest = self.args.generation_manifest or self.project_root / "manifests" / "generation_manifest.json"
        if not manifest.exists():
            self.record_stage("generate_assets", status="skipped", message=f"Generation manifest not found: {manifest}")
            return
        report = self.project_root / "reports" / "asset_generation_execution_report.json"
        preflight_report = self.project_root / "reports" / "provider_preflight_report.json"
        manifest_validation = self.project_root / "reports" / "generation_manifest_execution_validation.json"
        env_file = discover_provider_env_file(self.args, self.project_root)
        if self.args.approve_generation_manifest:
            if not self.args.allow_paid_generation:
                self.record_stage(
                    "approve_generation_manifest",
                    status="failed",
                    message="--approve-generation-manifest requires --allow-paid-generation.",
                    inputs={"generation_manifest": str(manifest)},
                    outputs={},
                )
                if not self.args.keep_going:
                    raise SystemExit(2)
            approval_note = self.args.generation_approval_note or "Approved by run_pipeline --approve-generation-manifest."
            approve_command = [
                sys.executable,
                str(BIN / "approve_generation_manifest.py"),
                "--manifest",
                str(manifest),
                "--approval-note",
                approval_note,
                "--approved-by",
                "run_pipeline",
            ]
            self.run_command(
                "approve_generation_manifest",
                approve_command,
                inputs={"generation_manifest": str(manifest)},
                outputs={"generation_manifest": str(manifest)},
            )
        validate_manifest_command = [
            sys.executable,
            str(BIN / "validate_generation_manifest_execution.py"),
            "--manifest",
            str(manifest),
            "--report",
            str(manifest_validation),
        ]
        if self.args.allow_paid_generation:
            validate_manifest_command.append("--require-paid-approval")
        validation_code = self.run_command(
            "validate_generation_manifest_execution",
            validate_manifest_command,
            inputs={"generation_manifest": str(manifest)},
            outputs={"validation_report": str(manifest_validation)},
        )
        if validation_code != 0:
            write_json(report, {
                "status": "blocked",
                "blocked_reason": "Generation manifest execution validation failed; asset generation not started.",
                "generation_manifest": str(manifest),
                "manifest_validation": str(manifest_validation),
                "checked_at": now_iso(),
            })
            self.record_stage(
                "generate_assets",
                status="blocked",
                message="Generation manifest execution validation failed; asset generation not started.",
                inputs={"generation_manifest": str(manifest)},
                outputs={"execution_report": str(report), "manifest_validation": str(manifest_validation)},
            )
            if not self.args.keep_going:
                raise SystemExit(validation_code)
            return
        if not self.args.skip_provider_preflight:
            preflight_command = [
                sys.executable,
                str(BIN / "preflight_generation_providers.py"),
                "--manifest",
                str(manifest),
                "--report",
                str(preflight_report),
                "--connect-timeout",
                str(self.args.asset_connect_timeout),
            ]
            if env_file:
                preflight_command.extend(["--env-file", str(env_file)])
            preflight_code = self.run_command(
                "provider_preflight",
                preflight_command,
                inputs={"generation_manifest": str(manifest)},
                outputs={"preflight_report": str(preflight_report)},
            )
            if preflight_code != 0:
                write_json(report, {
                    "status": "blocked",
                    "blocked_reason": "Provider preflight failed; asset generation not started.",
                    "generation_manifest": str(manifest),
                    "preflight_report": str(preflight_report),
                    "checked_at": now_iso(),
                })
                self.record_stage(
                    "generate_assets",
                    status="blocked",
                    message="Provider preflight failed; asset generation not started.",
                    inputs={"generation_manifest": str(manifest), "preflight_report": str(preflight_report)},
                    outputs={"execution_report": str(report), "asset_root": str(self.project_root / "assets" / self.args.project_id)},
                )
                if not self.args.keep_going:
                    raise SystemExit(preflight_code)
                return
        command = [
            sys.executable,
            str(BIN / "execute_generation_manifest.py"),
            "--manifest",
            str(manifest),
            "--project-root",
            str(self.project_root),
            "--report",
            str(report),
            "--runtime-package",
            str(self.project_root / "runtime_package" / "runtime_game_package.json"),
            "--workers",
            str(self.args.asset_workers),
            "--video-poll-interval",
            str(self.args.video_poll_interval),
            "--video-max-polls",
            str(self.args.video_max_polls),
            "--connect-timeout",
            str(self.args.asset_connect_timeout),
            "--read-timeout",
            str(self.args.asset_read_timeout),
        ]
        if env_file:
            command.extend(["--env-file", str(env_file)])
        if self.args.allow_paid_generation:
            command.append("--allow-paid-generation")
        if self.args.skip_existing_assets:
            command.append("--skip-existing")
        if self.args.only_asset_provider:
            command.extend(["--only-provider", self.args.only_asset_provider])
        returncode = self.run_command(
            "generate_assets",
            command,
            inputs={"generation_manifest": str(manifest), "preflight_report": str(preflight_report)},
            outputs={"execution_report": str(report), "asset_root": str(self.project_root / "assets" / self.args.project_id)},
        )
        if returncode == 0 and report.exists():
            summary = load_json(report)
            report_status = str(summary.get("status") or "completed")
            if report_status != "completed":
                self.record_stage(
                    "generate_assets",
                    status=report_status,
                    message=(
                        f"{summary.get('succeeded', 0)}/{summary.get('entry_count', 0)} generated; "
                        f"{summary.get('failed', 0)} failed; {summary.get('skipped', 0)} skipped"
                    ),
                    inputs={"generation_manifest": str(manifest)},
                    outputs={"execution_report": str(report), "asset_root": str(self.project_root / "assets" / self.args.project_id)},
                    command=command,
                    returncode=returncode,
                    stdout_log=self.log_dir / "generate_assets_stdout.txt",
                    stderr_log=self.log_dir / "generate_assets_stderr.txt",
                )

    def stage_runtime_preview(self) -> None:
        package = self.args.runtime_package or self.project_root / "runtime_package" / "runtime_game_package.json"
        if not package.exists():
            self.record_stage("runtime_preview", status="skipped", message=f"Runtime package not found: {package}")
            return
        preview = self.project_root / "runtime_preview"
        preview.mkdir(parents=True, exist_ok=True)
        copied: dict[str, str] = {}
        for filename in ["index.html", "styles.css", "app.js", "README.md"]:
            source = RUNTIME_TEMPLATE / filename
            target = preview / filename
            shutil.copy2(source, target)
            copied[filename] = str(target)
        package_target = preview / "runtime_game_package.json"
        shutil.copy2(package, package_target)
        copied["runtime_game_package"] = str(package_target)
        self.record_stage(
            "runtime_preview",
            status="completed",
            message="Runtime preview files copied.",
            inputs={"runtime_package": str(package), "runtime_template": str(RUNTIME_TEMPLATE)},
            outputs=copied,
        )

    def stage_index(self) -> None:
        artifacts = self.build_artifact_index()
        write_json(self.artifact_index_path, artifacts)
        self.record_stage(
            "index",
            status="completed",
            message="Artifact index written.",
            outputs={"artifact_index": str(self.artifact_index_path)},
        )

    def discover_agent_context(self, stage: str) -> list[Path]:
        config = AGENT_STAGE_CONFIG[stage]
        if self.args.context_mode == "minimal":
            return self.discover_minimal_agent_context(stage)
        candidates: list[Path] = [
            AGENT_INSTRUCTIONS / "README.md",
            AGENT_INSTRUCTIONS / config["instruction"],
            TOOL_ROOT / "docs" / "SCRIPT_WRITING_TUTORIAL_GUIDE.md",
            TOOL_ROOT / "docs" / "VISUAL_NOVEL_TUTORIAL_GUIDE.md",
            self.project_root / "README.md",
            self.project_root / "intake" / "case_metadata.json",
            self.project_root / "intake" / "project_intake.json",
            self.project_root / "planner" / "PLANNER_BRIEF.md",
            self.project_root / "planner" / "coherence_plan.json",
            self.project_root / "planner" / "story_intention.json",
            self.project_root / "authoring" / "story_intention.json",
            self.project_root / "authoring" / "story_graph_plan.json",
            self.project_root / "authoring" / "character_world_bible.json",
            self.project_root / "authoring" / "mechanics_plan.json",
            self.project_root / "authoring" / "scene_dramaturgy_plan.json",
            self.project_root / "authoring" / "hybrid_script.json",
            self.project_root / "authoring" / "asset_plan.json",
            self.project_root / "authoring" / "audio_plan.json",
            self.project_root / "playtest" / "text_playtest_pack.json",
            self.project_root / "prompts" / "prompt_pack.json",
            self.project_root / "prompts" / "audio_prompt_pack.json",
            self.project_root / "manifests" / "generation_manifest.json",
            self.project_root / "runtime_package" / "runtime_game_package.json",
            self.project_root / "runtime_package" / "validation_report.md",
            self.artifact_index_path,
            self.status_path,
        ]
        for schema_name in config.get("schemas", []):
            candidates.append(TOOL_ROOT / "schemas" / schema_name)
        extra_root = self.project_root / "planner" / "agent_context"
        if extra_root.exists():
            candidates.extend(sorted(path for path in extra_root.iterdir() if path.is_file()))
        report_root = self.project_root / "reports" / "agents"
        if report_root.exists():
            candidates.extend(sorted(path for path in report_root.iterdir() if path.is_file()))
        return unique_existing(candidates)

    def discover_minimal_agent_context(self, stage: str) -> list[Path]:
        config = AGENT_STAGE_CONFIG[stage]
        candidates: list[Path] = [
            AGENT_INSTRUCTIONS / "README.md",
            AGENT_INSTRUCTIONS / config["instruction"],
            self.project_root / "intake" / "case_metadata.json",
            self.project_root / "intake" / "project_intake.json",
            self.project_root / "planner" / "coherence_plan.json",
            self.project_root / "planner" / "story_intention.json",
            self.status_path,
        ]
        direct_context: dict[str, list[Path]] = {
            "plan": [],
            "story_graph": [
                self.project_root / "reports" / "agents" / "plan_agent_report.json",
            ],
            "world_character": [
                self.project_root / "authoring" / "story_graph_plan.json",
                self.project_root / "reports" / "agents" / "story_graph_agent_report.json",
            ],
            "mechanics": [
                self.project_root / "authoring" / "story_graph_plan.json",
                self.project_root / "reports" / "agents" / "story_graph_agent_report.json",
            ],
            "scene_dramaturgy": [
                self.project_root / "authoring" / "story_graph_plan.json",
                self.project_root / "authoring" / "character_world_bible.json",
                self.project_root / "authoring" / "mechanics_plan.json",
            ],
            "narrative": [
                self.project_root / "authoring" / "story_graph_plan.json",
                self.project_root / "authoring" / "character_world_bible.json",
                self.project_root / "authoring" / "mechanics_plan.json",
                self.project_root / "authoring" / "scene_dramaturgy_plan.json",
            ],
            "art_video_ui_prompts": [
                self.project_root / "authoring" / "story_graph_plan.json",
                self.project_root / "authoring" / "character_world_bible.json",
                self.project_root / "authoring" / "mechanics_plan.json",
                self.project_root / "authoring" / "scene_dramaturgy_plan.json",
                self.project_root / "playtest" / "text_playtest_pack.json",
            ],
            "audio_prompts": [
                self.project_root / "authoring" / "story_graph_plan.json",
                self.project_root / "authoring" / "character_world_bible.json",
                self.project_root / "authoring" / "mechanics_plan.json",
                self.project_root / "authoring" / "scene_dramaturgy_plan.json",
                self.project_root / "playtest" / "text_playtest_pack.json",
            ],
            "runtime_agent": [
                self.project_root / "runtime_package" / "runtime_game_package.json",
                self.project_root / "runtime_package" / "validation_report.md",
                self.project_root / "authoring" / "mechanics_plan.json",
            ],
            "checker": [
                self.project_root / "runtime_package" / "runtime_game_package.json",
                self.project_root / "runtime_package" / "validation_report.md",
                self.project_root / "authoring" / "story_graph_plan.json",
                self.project_root / "authoring" / "character_world_bible.json",
                self.project_root / "authoring" / "mechanics_plan.json",
                self.project_root / "authoring" / "scene_dramaturgy_plan.json",
                self.project_root / "authoring" / "asset_plan.json",
                self.project_root / "authoring" / "audio_plan.json",
                self.project_root / "playtest" / "text_playtest_pack.json",
                self.project_root / "prompts" / "prompt_pack.json",
                self.project_root / "prompts" / "audio_prompt_pack.json",
            ],
        }
        candidates.extend(direct_context.get(stage, []))
        for schema_name in config.get("schemas", []):
            candidates.append(TOOL_ROOT / "schemas" / schema_name)
        return unique_existing(candidates)

    def write_agent_handoff(self, stage: str, context_files: list[Path]) -> Path:
        config = AGENT_STAGE_CONFIG[stage]
        handoff_dir = self.project_root / "planner" / "agent_handoffs"
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff = handoff_dir / f"{stage}_handoff.md"
        expected = "\n".join(f"- `{item}`" for item in config["expected"])
        context = "\n".join(f"- `{path}`" for path in context_files)
        target_language = "zh-CN"
        intake_path = self.project_root / "intake" / "project_intake.json"
        if intake_path.exists():
            try:
                intake = load_json(intake_path)
                target_language = (
                    ((intake.get("creative_inputs") or {}).get("target_language") or target_language)
                    if isinstance(intake, dict)
                    else target_language
                )
            except Exception:
                target_language = "zh-CN"
        mode_line = (
            "This pipeline call is preparing the isolated workspace only; Claude Code will not be invoked."
            if not self.args.run_agents
            else "This pipeline call is allowed to invoke Claude Code. Do not call paid generation APIs."
        )
        handoff.write_text(
            f"""# Agent Handoff: {stage}

Project: `{self.args.project_id}`

Role: `{config['role']}`

Purpose:

{config['purpose']}

Mode:

{mode_line}

Hard boundaries:

- Treat files copied into `inbox/` as context.
- Write only to `outbox/`.
- Do not write API keys, signed URLs, or secrets.
- Do not call paid image/video/audio generation.
- Target language for all player-facing text: `{target_language}`.
- Do not leave English structural labels such as `(Narration)`, `(Dialogue)`, `(System)`, `[Routing]`, or `[If ...]` in visible runtime text.
- If the context is insufficient, write `blocker_report.md` and `agent_report.json`.
- Report cross-disciplinary conflicts instead of silently changing another role's ownership.

Expected outputs:

{expected}

Context files selected by Planner/orchestrator:

{context or "- No context files found beyond this handoff."}
""",
            encoding="utf-8",
        )
        return handoff

    def stage_agent(self, stage: str) -> None:
        config = AGENT_STAGE_CONFIG[stage]
        selected_model = model_for_stage(stage, self.args)
        context_files = self.discover_agent_context(stage)
        handoff = self.write_agent_handoff(stage, context_files)
        outputs = {
            "workspace": str(self.project_root / "agents" / config["agent_id"] / "workspace"),
            "handoff": str(handoff),
        }
        for item in config["expected"]:
            outputs[f"expected:{item}"] = str(self.project_root / "agents" / config["agent_id"] / "workspace" / "outbox" / item)
        command = [
            sys.executable,
            str(BIN / "run_claude_agent.py"),
            "--run-dir",
            str(self.project_root),
            "--role",
            config["role"],
            "--agent-id",
            config["agent_id"],
            "--handoff",
            str(handoff),
            "--model",
            selected_model,
            "--attempts",
            str(self.args.agent_attempts),
            "--timeout-sec",
            str(self.args.agent_timeout_sec),
            "--hard-timeout-sec",
            str(self.args.agent_hard_timeout_sec),
            "--permission-mode",
            self.args.agent_permission_mode,
        ]
        if self.args.agent_effort:
            command.extend(["--effort", self.args.agent_effort])
        if self.args.agent_tools:
            command.extend(["--tools", self.args.agent_tools])
        for context_file in context_files:
            command.extend(["--context", str(context_file)])
        for expected in config["expected"]:
            command.extend(["--expect", expected])
        if not self.args.run_agents:
            command.append("--dry-run")
        returncode = self.run_command(
            stage,
            command,
            inputs={
                "handoff": str(handoff),
                "context_count": str(len(context_files)),
                "agent_mode": "run" if self.args.run_agents else "prepare",
                "model": selected_model,
            },
            outputs=outputs,
        )
        if self.args.run_agents and returncode == 0:
            self.promote_agent_outputs(stage)

    def promote_agent_outputs(self, stage: str) -> None:
        config = AGENT_STAGE_CONFIG[stage]
        outbox = self.project_root / "agents" / config["agent_id"] / "workspace" / "outbox"
        promoted: dict[str, str] = {}
        report_source = outbox / "agent_report.json"
        if report_source.exists():
            report_target = self.project_root / "reports" / "agents" / f"{stage}_agent_report.json"
            report_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report_source, report_target)
            promoted["agent_report"] = str(report_target)
        for source_name, target_relative in PROMOTION_MAP.get(stage, {}).items():
            source = outbox / source_name
            if not source.exists():
                continue
            target = self.project_root / target_relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            promoted[source_name] = str(target)
        if not promoted:
            return
        with self.status_lock:
            self.status.setdefault("promotions", {})[stage] = {
                "updated_at": now_iso(),
                "from_outbox": str(outbox),
                "files": promoted,
            }
            self.save_status()

    def build_artifact_index(self) -> dict[str, Any]:
        known = [
            ("intake/case_metadata.json", "case metadata", "init", True, ["planner", "orchestrator"]),
            ("README.md", "game case readme", "init", True, ["human reviewer"]),
            ("playtest/text_playtest_pack.json", "text playtest pack", "planner/runtime", True, ["compile"]),
            ("runtime_package/runtime_game_package.json", "hot-swappable runtime package", "compile", True, ["validate", "fixed runtime"]),
            ("runtime_package/compile_report.json", "compile report", "compile", False, ["planner", "checker"]),
            ("runtime_package/validation_report.json", "machine-readable validation report", "validate", False, ["planner", "checker"]),
            ("runtime_package/validation_report.md", "human-readable validation report", "validate", False, ["human reviewer"]),
            ("prompts/prompt_pack.json", "prompt pack", "art/audio/video/ui agents", True, ["manifest"]),
            ("manifests/generation_manifest.json", "sanitized dry-run generation manifest", "manifest", True, ["future paid generation executor"]),
            ("runtime_preview/index.html", "runtime preview entry", "runtime_preview", False, ["browser"]),
            ("runtime_preview/runtime_game_package.json", "preview runtime package copy", "runtime_preview", False, ["browser"]),
            ("reports/pipeline_status.json", "pipeline state", "orchestrator", True, ["resume", "human reviewer"]),
        ]
        artifacts = []
        for relative_path, description, producer, canonical, consumers in known:
            path = self.project_root / relative_path
            artifacts.append(
                {
                    "path": relative_path,
                    "absolute_path": str(path),
                    "exists": path.exists(),
                    "description": description,
                    "producer": producer,
                    "canonical": canonical,
                    "consumers": consumers,
                }
            )
        for folder in ["authoring", "prompts", "manifests", "runtime_package", "reports"]:
            root = self.project_root / folder
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                relative_path = rel(path, self.project_root)
                if any(item["path"] == relative_path for item in artifacts):
                    continue
                artifacts.append(
                    {
                        "path": relative_path,
                        "absolute_path": str(path),
                        "exists": True,
                        "description": "discovered artifact",
                        "producer": "unknown_or_manual",
                        "canonical": False,
                        "consumers": [],
                    }
                )
        agents_root = self.project_root / "agents"
        if agents_root.exists():
            for path in sorted(agents_root.rglob("*")):
                if not path.is_file():
                    continue
                relative_path = rel(path, self.project_root)
                artifacts.append(
                    {
                        "path": relative_path,
                        "absolute_path": str(path),
                        "exists": True,
                        "description": "isolated agent workspace artifact",
                        "producer": "run_claude_agent",
                        "canonical": False,
                        "consumers": ["planner"],
                    }
                )
        return {
            "project_id": self.args.project_id,
            "project_root": str(self.project_root),
            "generated_at": now_iso(),
            "artifacts": artifacts,
        }

    def run_stage(self, stage: str) -> None:
        if stage == "init":
            self.stage_init()
        elif stage == "compile":
            self.stage_compile()
        elif stage == "runtime_enrich":
            self.stage_runtime_enrich()
        elif stage == "validate":
            self.stage_validate()
        elif stage == "manifest":
            self.stage_manifest()
        elif stage == "generate_assets":
            self.stage_generate_assets()
        elif stage == "runtime_preview":
            self.stage_runtime_preview()
        elif stage == "index":
            self.stage_index()
        elif stage in AGENT_STAGE_CONFIG:
            self.stage_agent(stage)
        else:
            self.record_stage(stage, status="skipped", message=f"Unknown stage: {stage}")

    def selected_dependencies(self, stage: str, selected: set[str]) -> set[str]:
        if stage == "index":
            return selected - {"index"}
        dependency_map = FAST_STAGE_DEPENDENCIES if self.args.pipeline_profile == "fast" else STAGE_DEPENDENCIES
        return {dep for dep in dependency_map.get(stage, []) if dep in selected}

    def run_sequential(self, stages: list[str]) -> None:
        for stage in stages:
            self.run_stage(stage)

    def run_parallel(self, stages: list[str]) -> None:
        selected = set(stages)
        completed: set[str] = set()
        failed: set[str] = set()
        pending = set(stages)
        running: dict[Any, str] = {}
        max_workers = max(1, self.args.parallelism)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while pending or running:
                runnable = [
                    stage
                    for stage in stages
                    if stage in pending and self.selected_dependencies(stage, selected).issubset(completed)
                ]
                while runnable and len(running) < max_workers:
                    stage = runnable.pop(0)
                    pending.remove(stage)
                    future = executor.submit(self.run_stage, stage)
                    running[future] = stage

                if not running:
                    blocked = ", ".join(sorted(pending))
                    raise RuntimeError(f"No runnable stages remain; check dependencies for: {blocked}")

                done, _ = wait(running.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    stage = running.pop(future)
                    try:
                        future.result()
                    except BaseException as exc:
                        failed.add(stage)
                        self.record_stage(stage, status="failed", message=f"Stage raised: {exc}")
                        if not self.args.keep_going:
                            raise
                    else:
                        stage_status = ((self.status.get("stages") or {}).get(stage) or {}).get("status")
                        if stage_status == "failed":
                            failed.add(stage)
                            if not self.args.keep_going:
                                raise RuntimeError(f"Stage failed: {stage}")
                        else:
                            completed.add(stage)

                if failed and self.args.keep_going:
                    newly_skipped = []
                    for stage in list(pending):
                        deps = self.selected_dependencies(stage, selected)
                        if deps & failed:
                            pending.remove(stage)
                            failed.add(stage)
                            newly_skipped.append(stage)
                            self.record_stage(stage, status="skipped", message=f"Skipped because dependency failed: {sorted(deps & failed)}")
                    if newly_skipped:
                        completed.update(newly_skipped)

    def run(self) -> int:
        ensure_dirs(self.project_root)
        self.save_status()
        stages = self.args.stages
        if self.args.parallelism > 1:
            self.run_parallel(stages)
        else:
            self.run_sequential(stages)
        self.status["ended_at"] = now_iso()
        self.save_status()
        return 0


def parse_stages(value: str) -> list[str]:
    if value == "all":
        return list(ALL_STAGES)
    if value == "tool":
        return list(TOOL_STAGES)
    if value == "agents":
        return list(AGENT_STAGES)
    stages = [part.strip() for part in value.split(",") if part.strip()]
    unknown = [stage for stage in stages if stage not in ALL_STAGES]
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown stage(s): {', '.join(unknown)}")
    return stages


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cross-disciplinary tool pipeline stages")
    parser.add_argument("project_id")
    parser.add_argument("--games-root", type=Path, default=DEFAULT_GAMES_ROOT)
    parser.add_argument("--stages", type=parse_stages, default=list(ALL_STAGES), help="all or comma-separated stage list")
    parser.add_argument("--text-pack", type=Path)
    parser.add_argument("--prompt-pack", type=Path)
    parser.add_argument("--runtime-package", type=Path)
    parser.add_argument("--generation-manifest", type=Path)
    parser.add_argument("--asset-base-path", default="")
    parser.add_argument("--cover-asset-id", default="")
    parser.add_argument("--require-text-pack", action="store_true")
    parser.add_argument("--assets-complete", action="store_true")
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Deprecated; resume is now the default unless --fresh is used.")
    parser.add_argument("--fresh", action="store_true", help="Start a fresh pipeline_status.json instead of preserving existing stage records.")
    parser.add_argument("--force-init", action="store_true")
    parser.add_argument("--parallelism", type=int, default=1, help="Run independent stages concurrently when dependencies allow it.")
    parser.add_argument("--pipeline-profile", choices=["safe", "fast"], default="safe", help="safe keeps conservative dependencies; fast starts independent downstream planning earlier.")
    parser.add_argument("--context-mode", choices=["full", "minimal"], default="full", help="full sends broad context to agents; minimal sends only direct dependencies and schemas.")
    parser.add_argument("--run-agents", action="store_true", help="Actually invoke Claude Code for agent stages. Default prepares isolated workspaces only.")
    parser.add_argument("--claude-model", default="", help="Override all agent stages with one Claude model id.")
    parser.add_argument(
        "--agent-model-profile",
        choices=["mixed", "sonnet", "opus"],
        default="mixed",
        help="mixed uses opus for complex planning/writing/checking stages and sonnet for execution stages.",
    )
    parser.add_argument("--agent-effort", default="")
    parser.add_argument("--agent-attempts", type=int, default=2)
    parser.add_argument("--agent-timeout-sec", type=int, default=900)
    parser.add_argument("--agent-hard-timeout-sec", type=int, default=7200)
    parser.add_argument("--agent-permission-mode", default="bypassPermissions")
    parser.add_argument("--agent-tools", default="", help="Override tools passed to run_claude_agent.py; default uses its scoped Bash,Read,LS set.")
    parser.add_argument("--allow-paid-generation", action="store_true", help="Allow generate_assets to call paid providers when the manifest also permits it.")
    parser.add_argument("--approve-generation-manifest", action="store_true", help="Record paid-generation approval into the manifest before generate_assets.")
    parser.add_argument("--generation-approval-note", default="", help="Approval note for --approve-generation-manifest. Do not include secrets.")
    parser.add_argument("--asset-workers", type=int, default=2)
    parser.add_argument("--asset-connect-timeout", type=int, default=20)
    parser.add_argument("--asset-read-timeout", type=int, default=900)
    parser.add_argument("--skip-provider-preflight", action="store_true", help="Skip provider TCP connectivity preflight before generate_assets.")
    parser.add_argument("--skip-existing-assets", action="store_true")
    parser.add_argument("--only-asset-provider", default="")
    parser.add_argument("--provider-env-file", type=Path, help="Dotenv-style provider key file; defaults to <games-root>/../.secrets/provider_keys.env when present.")
    parser.add_argument("--no-harden-visual-prompts", action="store_true", help="Do not run hard AVG visual prompt-pack rewriting before manifest generation.")
    parser.add_argument("--video-poll-interval", type=int, default=30)
    parser.add_argument("--video-max-polls", type=int, default=120)
    args = parser.parse_args()

    pipeline = Pipeline(args)
    return pipeline.run()


if __name__ == "__main__":
    raise SystemExit(main())
