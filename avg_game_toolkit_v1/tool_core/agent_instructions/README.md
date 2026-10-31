# Agent Instruction Pack V2

This folder contains role-specific instruction contracts for isolated worker agents. Each file is written like a system prompt: what the agent owns, what it must output, what it must never do, and what counts as done.

The instruction pack now absorbs two local tutorial lessons:

- `../docs/SCRIPT_WRITING_TUTORIAL_GUIDE.md`: every project needs a concrete core intention before story graph planning.
- `../docs/VISUAL_NOVEL_TUTORIAL_GUIDE.md`: visual novels are not script plus pictures; they are narrative, presentation, and interactivity working together.

## Shared Highest Principle

Every agent serves the same production promise:

> A player should be able to load one game package, quickly understand who they are and why the scene matters, make fair choices, see visible consequences, and experience art/video/UI that supports the same dramatic intention the story and mechanics depend on.

The working formula is:

```text
Visual Novel = (Narrative + Visual / Audio Presentation) x Interactivity
```

No role should produce content that only works in one discipline while breaking another. If a role finds a conflict, it reports the conflict instead of silently changing another role's output.

## Story Intention Gate

Before `story_graph_plan.json`, the Planner must define and approve a `story_intention_statement`:

```text
This is a story about [protagonist identity].
The protagonist tries [core goal].
But they face [core conflict].
The story finally discovers or embodies [core intention].
```

It must also define:

- core question;
- emotional anchor;
- central conflict;
- intended choice pressure;
- single-answer / true-ending structure, or multiple-answer equal-ending structure;
- how the gameplay expresses the intention;
- what each major character represents, challenges, or tempts.

Every downstream agent must preserve this intention unless the Planner explicitly revises it.

## Required Roles

- `planner.md`: top-level owner, intake, story intention gate, gate control, conflict resolution.
- `story_graph_director.md`: story graph, branch topology, state/ending logic, route value pressure.
- `scene_dramaturgy_agent.md`: scene-level dramatic beats before final writing.
- `narrative_writer.md`: player-facing segments, dialogue, messages, choice copy.
- `character_world_agent.md`: character bible, world, locations, props, speech, knowledge.
- `mechanics_agent.md`: values, flags, gates, echoes, endings, failures.
- `art_video_ui_agent.md`: multimodal asset slots, prompts, UI surface requirements.
- `generation_executive_agent.md`: approved provider execution, local asset download, sanitized reports, and blocker handling.
- `audio_agent.md`: BGM, ambience, SFX, voice policy, silence, and runtime audio mapping.
- `runtime_agent.md`: fixed runtime and hot-swappable game package assembly.
- `checker_agent.md`: independent coherence audit and playtest gate.

## Standard Agent Input

Each agent should receive an `inbox/` with:

- project intake and user constraints;
- approved Planner brief;
- approved `story_intention_statement` after G1.5;
- upstream artifacts relevant to the role;
- explicit write scope;
- output paths;
- questions the Planner wants answered.

## Standard Agent Output

Each agent writes only to its own `outbox/`:

- role artifact JSON/MD;
- `agent_report.json` matching `../schemas/agent_report.schema.json`;
- open questions, risks, or conflicts for Planner.

Every report should explicitly mention whether the role is aligned with:

- core intention;
- player comprehension;
- visible choice feedback;
- asset-story traceability;
- runtime package feasibility.

## Shared Prohibitions

- Do not spend paid generation credits unless the Planner explicitly marks it approved.
- Do not write API keys, signed URLs, or secrets into game-facing files.
- Do not invent visible characters, locations, props, UI surfaces, CGs, or videos without an asset/runtime slot.
- Do not change route targets, endings, or state logic outside your ownership.
- Do not treat schema validity as proof of game quality.
- Do not let characters appear only to deliver exposition.
- Do not let a choice appear before the player can understand its pressure.
- Do not let visual/video content carry required meaning without text or UI fallback.
- Do not launch a dependent worker task until the upstream worker has written a complete or blocked status into the project supervision board.

## Runtime Target

The final player-facing handoff should converge to:

```text
runtime_game_package.json
```

The fixed runtime should be able to on-load/off-load a game by loading this JSON and its local asset references. UI can improve independently, but the data contract should remain stable.
