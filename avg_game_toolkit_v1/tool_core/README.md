# Cross-Disciplinary Coherence Tool V1

This is a copied, standalone tool version based on the current interactive media asset pipeline. It is intentionally separated from the existing playable games and generated assets.

The goal of this version is not to make the script the top-level source of truth. the Story Graph pipeline is useful because it proves that structured planning, writers, and auditors produce better narrative logic. For this tool, the top-level owner is the Planner, and the Planner balances story, art, mechanics, video, UI, runtime, cost, and player comprehension.

## Core Principle

Cross-Disciplinary Coherence means every playable beat should be coherent across disciplines:

- Story: the player understands identity, place, motivation, stakes, and consequence.
- Art: every required visual fact has an approved asset or a deliberate runtime substitute.
- Mechanics: choices, state changes, failure, endings, and route gates have real meaning.
- Video: video is reserved for beats that benefit from motion, timing, voice, or emotional payoff.
- UI: runtime surfaces expose the right information without hiding the scene.
- Production: every generated asset maps to a runtime use, and every runtime use maps back to an approved plan.

No single discipline silently dominates the others. If there is a conflict, the Planner either changes the plan, narrows an agent's scope, or sends a revision task back to the relevant agent.

## Directory Map

```text
cross_disciplinary_coherence_v1/
  README.md
  docs/                         # copied general docs
  agent_instructions/           # skill-like contracts for Planner and worker agents
  media_asset_pipeline/
    README.md
    docs/
      ARCHITECTURE.md
      STORY_GRAPH_LEARNINGS.md
      CLAUDE_CODE_ISOLATED_AGENTS.md
      CROSS_DISCIPLINARY_COHERENCE.md
      PROJECT_INTAKE_GATE.md
      PLANNER_CONTROL_PROTOCOL.md
      TEXT_PLAYTEST_CLI.md
  bin/
    run_pipeline.py              # orchestrates init/compile/validate/manifest/runtime preview
    run_claude_agent.py          # isolated Claude Code worker launcher
    init_game_case.py            # creates the canonical game-case workspace layout
    play_text_game.py            # MUD-like text playtest runner
    check_story_graph_plan.py    # zero-LLM story graph structural checker
    compile_runtime_package.py   # compiles text/cell packs into runtime_game_package.json
    validate_runtime_package.py  # validates runtime graph/state/assets/secrets/comprehension
    build_generation_manifest.py # dry-run provider payload manifest from prompt_pack.json
  providers/                    # sanitized payload builders; no secrets or paid calls
  runtime/
    fixed_avg_runtime/           # reusable HTML runtime for runtime_game_package.json
  schemas/
    project_intake.schema.json
    coherence_plan.schema.json
    story_graph_plan.schema.json
    coherence_matrix.schema.json
    scene_dramaturgy_plan.schema.json
    runtime_game_package.schema.json
    character_world_bible.schema.json
    audio_plan.schema.json
    prompt_pack.schema.json
    story_intention.schema.json
    agent_report.schema.json
    text_playtest_pack.schema.json
    media_*.schema.json          # copied current schemas
  skills/
    interactive-media-asset-pipeline/
  templates/
  pipeline/
  data/                         # empty/default reusable data slots
  legacy_reference/             # copied old game-case material, not canonical
```

Game cases should stay outside this tool version, for example:

```text
games/<project_id>/
video_engine/public/<project_id>/
video_engine/public/assets/<project_id>/
```

## Main Outputs

The new canonical planning artifacts are:

- `coherence_plan.json`: Planner-owned top-level control plan.
- `project_intake.json`: user-facing fixed entry contract for new projects and permission boundaries.
- `media_project_brief.json`: normalized production brief derived from intake.
- `story_intention.json`: authoring-time G1.5 Story Intention Gate payload, usually embedded in `coherence_plan.story_intention`.
- `story_graph_plan.json`: Planner/Director-owned playable story graph with node types, branch types, value effects, knowledge boundaries, route matrix, and media hooks.
- `scene_dramaturgy_plan.json`: scene-level dramatic plan that defines wants, conflict, scene turn, first appearances, segment budgets, and callback requirements before final writing.
- `story_plan.json`: narrative structure and story-cell budgets.
- `character_design.json`: character, relationship, visual, and speech constraints.
- `hybrid_script.json`: concrete runtime beats inside each story cell.
- `character_world_bible.json`: reusable character, location, prop, relationship, and knowledge contract.
- `audio_plan.json`: standalone audio and video-embedded audio policy/cue contract.
- `prompt_pack.json`: provider-ready prompt pack with runtime traceability.
- `asset_plan.json`: approved art/video/UI/audio asset slots.
- `coherence_matrix.json`: traceability table across story, art, mechanics, video, UI, runtime, and QA.
- `runtime_game_package.json`: hot-swappable player-facing game package consumed by the fixed runtime.
- `agent_report.json`: standardized report contract for all worker/checker agents.
- `text_playtest_pack.json`: MUD-like runtime dry-run pack used before media generation.

Older schemas remain available because they are still useful, but they should be consumed under the Planner-owned coherence plan.

## Planner-First Gate Flow

```text
G0 Project Intake
G1 Coherence Plan
G1.5 Story Intention Gate
G2 Story Graph Plan
G3 World / Character / Mechanics Baseline
G4 Scene Dramaturgy Plan
G5 Media Story Plan with Cell Budgets
G6 Narrative Expansion into Segments
G7 Art / UI / Video / Audio Support Plans
G8 Coherence Matrix
G9 Planner Conflict Pass
G9.5 Text Playtest Gate
G10 Runtime Game Package Assembly
G11 Prompt Packs / Provider Payloads
G12 Generation
G13 Fixed Runtime Assembly
G14 Coherence QA + Playtest
```

The Planner may loop any gate when an agent reports a conflict. For example, if Narrative adds a new prop but Art cannot generate it consistently, Planner decides whether to simplify the scene, replace the visual evidence with UI text, or allocate a new asset slot.

`G0 Project Intake` is mandatory for new projects. The Planner must collect or explicitly assume the fixed intake fields before writing `coherence_plan.json`, and must not launch execution agents or paid generation until the intake permission fields allow it.

`G1.5 Story Intention Gate` is mandatory before story graph planning. The Planner must define the core question, emotional anchor, central conflict, intended player choice pressure, and whether the project uses a true-ending structure or multiple equal answers. This prevents the story graph from becoming a list of events without a clear dramatic soul. The full authoring data lives in `coherence_plan.story_intention` and can be validated independently with `schemas/story_intention.schema.json`; the runtime package only carries an optional short summary in `meta.story_intention_summary`.

## Execution Model

Real multi-agent production should use isolated Claude Code workspaces, not shared-context subagents. See:

- `media_asset_pipeline/docs/CLAUDE_CODE_ISOLATED_AGENTS.md`
- `bin/run_claude_agent.py`

Before image/video generation, compile a `text_playtest_pack.json` and run:

```bash
python bin/play_text_game.py /absolute/path/to/text_playtest_pack.json
```

This catches route, state, comprehension, and ending/failure issues while the project is still text-only.

To initialize a new case without mixing it into the reusable tool directory:

```bash
python bin/init_game_case.py <project_id>
```

To run the current tool-layer pipeline without launching story agents or paid generation:

```bash
python bin/run_pipeline.py <project_id> \
  --text-pack /absolute/path/to/text_playtest_pack.json \
  --stages all
```

The orchestrator writes:

```text
games/<project_id>/reports/pipeline_status.json
games/<project_id>/reports/artifact_index.json
```

Partial reruns preserve existing stage status by default. Use `--fresh` only when you want to reset the pipeline status file.

For the current usage guide, see:

- `docs/PIPELINE_USAGE_GUIDE.md`

Before narrative expansion, check the story graph:

```bash
python bin/check_story_graph_plan.py /absolute/path/to/story_graph_plan.json --fail-on-error
```

This catches pseudo choices, missing targets, orphan failures, unused value attributes, weak choice consequences, and missing media delivery hooks before writers spend time expanding prose.

Before runtime implementation, compile the approved story, mechanics, and asset manifest into:

```bash
python bin/compile_runtime_package.py \
  --text-pack /absolute/path/to/text_playtest_pack.json \
  --output /absolute/path/to/runtime_game_package.json \
  --report /absolute/path/to/compile_report.json
```

matching:

```text
schemas/runtime_game_package.schema.json
```

The fixed runtime should be able to load/unload this package without story-specific code changes. UI can improve independently, but story content, branches, segments, portraits, videos, achievements, and saves should be data-driven.

Validate the package before loading it:

```bash
python bin/validate_runtime_package.py \
  /absolute/path/to/runtime_game_package.json \
  --output /absolute/path/to/validation_report.json \
  --human-output /absolute/path/to/validation_report.md
```

The reusable HTML runtime lives in:

```text
runtime/fixed_avg_runtime/
```

Copy or serve a package as `runtime_game_package.json`, or load it with:

```text
index.html?package=/path-or-url/to/runtime_game_package.json
```

Prompt/provider planning is a dry-run step until the user explicitly approves paid generation:

```bash
python bin/build_generation_manifest.py \
  --prompt-pack /absolute/path/to/prompt_pack.json \
  --output /absolute/path/to/generation_manifest.json
```

The manifest records sanitized request payloads only. API keys must come from environment variables during a later execution step and must never be written into manifests or runtime packages.

Agent prompts should come from `agent_instructions/`. These files are written as clear role contracts, similar in spirit to Story-to-game's skill instructions: what the agent owns, what it must output, what it must never do, and what counts as done.

## Story Graph Pipeline Influence

The Story Graph pipeline's strongest lesson is separation of planning and writing:

- Director creates a structured story graph.
- Writers expand local sections.
- Auditor checks graph integrity, fake choices, value-system usage, and continuity.

This version now makes that lesson explicit through `story_graph_plan.json`. The story graph is not an optional Planner habit; it is a required gate before media story planning. We still broaden the audit target beyond text: the graph must expose media hooks so the whole game production package can be checked as a playable audiovisual system.

## Story-to-game Influence

Story-to-game's strongest lesson is runtime-compatible JSON discipline:

- a fixed launcher can load a complete game if the game converges to a small state-machine package;
- player-facing writing should be segmented, not dumped in large paragraphs;
- every meaningful choice needs a visible callback, not only a hidden value change;
- home functions such as import, continue, new game, ending records, achievements, chapter select, save slots, stats, and settings should be runtime-native.

This tool keeps those lessons but extends them to multimodal AVG production through `runtime_game_package.json`: backgrounds, character portraits, expression layers, images, video clips, audio, phone overlays, right-top hints, memory logs, and local asset manifests.

## Visual Novel Tutorial Influence

The local image tutorial in `<WORKSPACE_ROOT>/tutorial/视觉小说/` has been summarized in:

- `docs/VISUAL_NOVEL_TUTORIAL_GUIDE.md`

Its key lesson is that a visual novel is not "script plus pictures"; it is `(narrative + visual/audio presentation) x interactivity`. This reinforces the need for `scene_dramaturgy_plan.json`, segmented runtime text, character portrait/expression planning, CG/video restraint, visible choice callbacks, and text playtesting before paid generation.

## Script Writing Tutorial Influence

The local image tutorial in `<WORKSPACE_ROOT>/tutorial/如何写好的剧本/` has been summarized in:

- `docs/SCRIPT_WRITING_TUTORIAL_GUIDE.md`

Its key lesson is that story production must begin from a concrete core intention, not from event lists. A project should be expressible as: "This is a story about `[protagonist identity]`; the protagonist tries `[core goal]`; but faces `[core conflict]`; and finally discovers or embodies `[core intention]`." This is now treated as a required gate before `story_graph_plan.json`.
