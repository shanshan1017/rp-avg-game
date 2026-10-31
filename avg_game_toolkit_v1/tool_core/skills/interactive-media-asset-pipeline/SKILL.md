---
name: interactive-media-asset-pipeline
description: Use when turning a premise, script, image/video reference, or mixed input into a cross-disciplinary coherent interactive media package before game implementation. Covers Planner-first coherence planning, story cells, character/world design, mechanics, image/video capability selection, UI/runtime surfaces, asset manifests, agent reports, and QA traceability.
---

# Interactive Media Asset Pipeline - Coherence V1

Use this skill before building or regenerating a game runtime. The goal is to convert loose creative input into a complete, traceable production package that balances story, art, mechanics, video, UI, runtime, and QA.

## Core Rule

The script is not the top-level authority. The Planner owns the coherence plan and resolves conflicts between disciplines.

Generate only assets that are referenced by the approved runtime contract or explicit QA surface. If the current game will not display or play an asset, keep it optional and do not batch-generate it.

## Read First

- `../../media_asset_pipeline/docs/ARCHITECTURE.md`
- `../../media_asset_pipeline/docs/CROSS_DISCIPLINARY_COHERENCE.md`
- `../../media_asset_pipeline/docs/PROJECT_INTAKE_GATE.md`
- `../../media_asset_pipeline/docs/PLANNER_CONTROL_PROTOCOL.md`
- `../../media_asset_pipeline/docs/STORY_GRAPH_PLANNING_GATE.md`
- `../../media_asset_pipeline/docs/HOT_SWAPPABLE_RUNTIME_PACKAGE.md`
- `../../media_asset_pipeline/docs/STORY_GRAPH_LEARNINGS.md`
- `../../agent_instructions/README.md`
- `references/multi_agent_workflow.md`
- `references/minimax_audio_capability.md` when standalone audio, TTS, voice design, or music generation is needed.

## Required Top-Level Artifacts

- `project_intake.json` matching `../../schemas/project_intake.schema.json`
- `coherence_plan.json` matching `../../schemas/coherence_plan.schema.json`
- `story_graph_plan.json` matching `../../schemas/story_graph_plan.schema.json`
- `scene_dramaturgy_plan.json` matching `../../schemas/scene_dramaturgy_plan.schema.json`
- `coherence_matrix.json` matching `../../schemas/coherence_matrix.schema.json`
- `runtime_game_package.json` matching `../../schemas/runtime_game_package.schema.json`
- Agent reports matching `../../schemas/agent_report.schema.json`

Existing media artifacts remain required when the project reaches those gates:

- Project brief matching `../../schemas/media_project_brief.schema.json`
- Story bible matching `../../schemas/media_story_bible.schema.json`
- Character design matching `../../schemas/media_character_design.schema.json`
- Story plan matching `../../schemas/media_story_plan.schema.json`
- Hybrid script matching `../../schemas/media_hybrid_script.schema.json`
- Asset plan matching `../../schemas/media_asset_plan.schema.json`
- Generation manifest matching `../../schemas/media_generation_manifest.schema.json`

## Multi-Agent Contract

Minimum production uses three roles: Planner, Executive, Checker. Production-quality runs should use the expanded roles:

- Planner: Codex in the main thread. Owns the coherence plan, budgets, gate decisions, and conflict resolution.
- Scene Dramaturgy Agent: turns graph nodes into playable scene plans before final writing.
- Narrative Agent: expands approved story cells into concrete runtime beats.
- Character / World Agent: defines visible characters, relationships, locations, props, speech style, visual anchors, and knowledge boundaries.
- Mechanics Agent: designs choices, route gates, state changes, failures, endings, and echoes.
- Art Agent: maps story/character/UI/video needs to feasible image assets and generation constraints.
- UI Agent: defines runtime-native surfaces, concept directions, and readability constraints.
- Video Agent: expands only approved video slots into provider-ready video plans.
- Audio Agent: plans BGM, ambience, SFX, silence, optional voice, voice-design/TTS/music-generation usage, and runtime audio mapping.
- Generation Executive: submits tasks, downloads local files, and writes sanitized manifests.
- Runtime Agent: compiles approved script and assets into HTML or Godot.
- Checker / Coherence Auditor: verifies cross-domain traceability and blocks incoherent gates.

Every non-Planner agent must return an `agent_report.json`. Agents may report conflicts, but they must not silently redesign another discipline's output.

Use `../../agent_instructions/` as the canonical instruction pack when launching isolated agents. Each file is a role contract in the style of a skill: scope, required outputs, must-not rules, and done criteria.

## Workflow

1. Normalize input into a project brief.
2. Planner records `project_intake.json` and confirms planning/execution/generation permissions.
3. Planner writes `coherence_plan.json`: project promise, target runtime, budgets, disciplines, constraints, gates, and conflict policy.
4. Planner runs the Story Intention Gate, then Planner or isolated Director writes `story_graph_plan.json`: node types, branch types, value effects, route matrix, ending/failure conditions, witnesses, and media hooks.
5. Run `bin/check_story_graph_plan.py` before detailed scene writing.
6. Planner or assigned agents define character/world/mechanics baselines from the approved graph.
7. Scene Dramaturgy Agent writes `scene_dramaturgy_plan.json`: wants, conflict, turn, first appearances, segment budgets, callback requirements, asset hooks.
8. Planner writes story plan with story-cell budgets, comprehension gates, and approved asset/video/UI slots.
9. Narrative Agent expands story cells into segmented hybrid script beats.
10. Art/UI/Video/Audio/Mechanics agents audit support requirements and write reports.
11. Planner builds or updates `coherence_matrix.json`.
12. Runtime Agent or Planner compiles approved content into `runtime_game_package.json`.
13. Text playtest validates story and route fun before paid generation.
14. Planner resolves all blocker/major conflicts before generation.
15. Generation Executive creates prompt packs and provider payloads only for approved assets.
16. Generate character references first, then poses/expressions, backgrounds/stills/first frames, then video. Generate standalone audio only for approved non-video runtime audio slots.
17. Runtime Agent loads the hot-swappable package into the fixed HTML or Godot runtime.
18. Checker playtests and verifies story comprehension, asset-story traceability, mechanics alignment, UI readability, runtime references, safety, and no secret leakage.

## Capability Selection

Read `references/capability_matrix.md` when deciding whether a task is text-to-image, reference-image edit, mask edit, text-to-video, first-frame video, reference-video continuation, audio-guided video, tail-frame chaining, TTS, voice design, or music generation.

Read `references/video_adapter_contract.md` before implementing Ark submit/poll/download code. API keys must come from environment variables and never be written into repo files.

Read `references/minimax_audio_capability.md` before implementing MiniMax TTS, voice design, music generation, hex decoding, or local audio manifests. API keys must come from environment variables and never be written into repo files.

## Handoff Rules

- Do not use real people, celebrities, public figures, or existing IP as visual references.
- For first-person projects, the protagonist is the camera unless the project brief explicitly says otherwise.
- Do not pass a cast lineup as a scene/poster reference unless the scene should contain the entire cast.
- Signed image/video URLs are temporary; download outputs to local assets and redact remote URLs from game-facing manifests.
- Signed or temporary audio URLs are temporary; download outputs to local assets and redact remote URLs from game-facing manifests.
- Video clips with generated audio should carry their audio intent inside the video prompt. Do not duplicate video-internal sound as standalone runtime audio unless the package needs a separate transition, loop, or replay layer.
- Runtime integration must not add unapproved assets or change branch logic.
- Checker approval is about coherence, not only file existence.
- Final player builds should load a `runtime_game_package.json`; story-specific code in the runtime is a blocker unless the Planner explicitly approves a prototype exception.
