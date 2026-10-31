# Interactive Media Asset Pipeline - Coherence V1

This is the media production entrypoint for the copied tool version `cross_disciplinary_coherence_v1`.

The pipeline converts creative input into a complete, traceable, and coherent asset/game-content package before runtime implementation. It can accept text, images, video references, audio references, style references, or mixed inputs.

## What Changed In This Version

Older versions were already moving toward hybrid text+image+video planning. This version makes the top-level goal explicit:

> The Planner controls cross-disciplinary coherence. The script is important, but it is not the only source of truth.

The Planner must balance:

- narrative depth and pacing;
- character/world consistency;
- choice and state design;
- visual asset feasibility;
- video budget and generation risk;
- UI readability;
- runtime implementation cost;
- player comprehension before decisions.

## Directory

```text
media_asset_pipeline/
  README.md
  docs/
    ARCHITECTURE.md
    STORY_GRAPH_LEARNINGS.md
    CHARACTER_DESIGN_SPEC.md
    CROSS_DISCIPLINARY_COHERENCE.md
    HYBRID_NARRATIVE_SPEC.md
    MULTI_AGENT_FRAMEWORK_V2.md
    PROJECT_INTAKE_GATE.md
    PLANNER_CONTROL_PROTOCOL.md
    STORY_GRAPH_PLANNING_GATE.md
  examples/
```

## Canonical Schemas

The copied version keeps the existing media schemas and adds top-level coherence contracts:

- `../../schemas/coherence_plan.schema.json`
- `../../schemas/project_intake.schema.json`
- `../../schemas/story_graph_plan.schema.json`
- `../../schemas/coherence_matrix.schema.json`
- `../../schemas/agent_report.schema.json`

Existing schemas are still used under those contracts:

- `../../schemas/media_project_brief.schema.json`
- `../../schemas/media_story_bible.schema.json`
- `../../schemas/media_character_design.schema.json`
- `../../schemas/media_story_plan.schema.json`
- `../../schemas/media_hybrid_script.schema.json`
- `../../schemas/media_asset_plan.schema.json`
- `../../schemas/media_generation_manifest.schema.json`

## Multi-Agent Roles

- Planner: owns coherence plan, budgets, gate decisions, and conflict resolution.
- Story Graph Director: produces or assists `story_graph_plan.json`; Planner still approves it.
- Narrative Agent: expands story cells into concrete runtime beats.
- Character / World Agent: owns character, relationship, knowledge, location, and prop constraints.
- Mechanics Agent: owns choices, state changes, branch semantics, failure, endings, and echoes.
- Art Agent: owns visual feasibility, character consistency, asset slots, and prompt constraints.
- UI Agent: owns runtime information surfaces and readability.
- Video Agent: owns video-specific beat selection and provider payload feasibility.
- Generation Executive: submits tasks and writes sanitized local manifests.
- Runtime Agent: compiles approved data/assets into HTML or Godot.
- Checker / Coherence Auditor: verifies the cross-domain matrix and blocks incoherent gates.

## Gate Rule

No generation batch should start until:

1. `project_intake.json` exists, or the current request explicitly continues an approved existing project.
2. `coherence_plan.json` exists.
3. `story_graph_plan.json` exists and passes story-graph checks.
4. `coherence_matrix.json` covers all story cells, choices, failures, endings, and generated assets.
5. Planner has resolved all blocker/major conflicts from agent reports.
6. Checker has approved the current gate.

No execution agents should launch until `project_intake.planner_permission.approved_to_start_execution=true`, except planning-only checker/director dry runs explicitly requested by the user.

No paid generation should start until `project_intake.production_preferences.paid_generation_allowed=true`.

Story-graph checks:

```bash
python ../../bin/check_story_graph_plan.py /absolute/path/to/story_graph_plan.json --fail-on-error
```

## Asset Rule

Generate only assets that are referenced by the approved runtime contract or explicit QA surface. Optional future assets stay in planning notes and do not enter the generation queue.

## Runtime Rule

Runtime integration consumes approved data. It must not silently rewrite story beats, add assets, or change branch logic. If the runtime finds a problem, it reports back to Planner.
