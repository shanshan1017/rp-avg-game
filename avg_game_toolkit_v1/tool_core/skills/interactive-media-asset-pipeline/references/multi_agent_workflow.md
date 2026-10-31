# Multi-Agent Workflow - Coherence V1

This workflow is Planner-first. It uses the Story Graph pipeline's planning/writing/auditing discipline, but it does not make the script the highest-level artifact. Story, mechanics, art, video, UI, runtime, and QA must stay mutually aligned.

Use the role files in `../../agent_instructions/` as the canonical worker prompts. This file describes coordination; the instruction pack describes what each agent must and must not do.

## Roles

### Planner

Default owner: Codex in the current thread.

Owns:

- user requirement normalization;
- `project_intake.json`;
- `coherence_plan.json`;
- `story_graph_plan.json` approval;
- story-cell budgets and route shape;
- discipline scopes and agent handoffs;
- global constraints, runtime target, and generation budget;
- conflict resolution;
- `coherence_matrix.json` approval;
- final gate go/no-go decisions.

Must not:

- let a worker silently change another discipline's scope;
- start generation while blocker/major conflicts are unresolved;
- treat a good script as sufficient proof that the game will be coherent.

### Narrative Agent

Owns:

- hybrid script expansion;
- segmented narration/dialogue/message/choice copy;
- transitions between story cells;
- player comprehension notes;
- facts introduced and facts required before each choice.

Must report to Planner before:

- adding visible characters;
- adding locations or props;
- adding video beats;
- changing choice targets, endings, or route logic.

### Story Graph Director

Owner: Planner directly or an isolated Claude Code Director agent.

Owns:

- `story_graph_plan.json`;
- node types, branch types, route matrix, ending and failure conditions;
- value attributes, choice effects, gates, and later echoes;
- fact introduction and witness/knowledge boundaries;
- media hooks for visual facts, text fallbacks, UI surfaces, and video candidates.

Must not:

- write final prose;
- write image/video prompts;
- treat media hooks as approved generation slots without Art/UI/Video review.

### Scene Dramaturgy Agent

Owns:

- scene objectives;
- current pressure;
- active character wants;
- conflict and scene turn;
- first appearance requirements;
- segment/dialogue budgets;
- choice callback requirements;
- branch information boundaries;
- asset and video hooks before final writing.

Must block:

- scenes that only summarize facts;
- character entrances without purpose;
- choices without player comprehension;
- final writing before scene turn and callback requirements are clear.

### Character / World Agent

Owns:

- character profiles;
- relationship arcs;
- speaking style;
- visual anchors;
- knowledge boundaries;
- location and prop continuity.

Must report:

- character consistency risks;
- missing portrait/expression needs;
- facts that a character should or should not know.

### Mechanics Agent

Owns:

- choice meaning;
- state changes;
- relationship values;
- route gates;
- failure and ending conditions;
- later echoes of earlier decisions.

Must block:

- fake choices;
- choices before comprehension;
- endings decided only by the final click when earlier choices should matter.

### Art Agent

Owns:

- visual feasibility;
- character reference policy;
- background/still/prop/pose/expression slots;
- style consistency rules;
- generation prompt constraints.

Must block:

- scene assets with no runtime use;
- single-character scenes using cast-lineup references;
- unapproved group scenes;
- visuals that require unsupported model behavior.

### UI Agent

Owns:

- runtime-native information surfaces;
- dialogue/narration/phone/hint/log/profile/choice layout requirements;
- UI concept art only when useful;
- mobile readability constraints.

Must block:

- UI surfaces that hide the key visual evidence;
- story information that exists only in decorative UI art rather than runtime text.

### Video Agent

Owns:

- approved video slot expansion;
- first-frame and reference selection;
- duration, ratio, audio, watermark, and provider payload notes;
- video-vs-still justification.

Must not:

- add video clips beyond Planner budget;
- rely on video to carry facts that the player must read but runtime does not display.

### Generation Executive

Owns:

- prompt packs;
- provider payloads;
- task submission;
- local downloads;
- sanitized manifests.

Must not:

- redesign story, mechanics, art direction, or runtime fields;
- write API keys or signed URLs into game-facing files;
- generate optional assets that are not approved by Planner.

### Runtime Agent

Owns:

- compiling approved script and manifests into `runtime_game_package.json`;
- HTML/CSS/JS or Godot implementation within explicit scope;
- local smoke test and reference validation.

Must report:

- unsupported UI surfaces;
- missing runtime fields;
- asset sizes or formats that break the runtime.

Must not:

- hardcode story-specific nodes, choices, or asset paths into runtime code;
- expose developer introduction content in the default player home screen.

### Checker / Coherence Auditor

Owns independent review.

Checks:

- schema validity;
- player comprehension;
- asset-story traceability;
- mechanics-story alignment;
- visual and character consistency;
- UI readability;
- runtime references and file existence;
- no secrets or signed URLs;
- no unapproved generated assets in runtime.

Must not silently patch production outputs.

## Handoff Order

1. Planner collects or confirms `project_intake.json`.
2. Planner writes `coherence_plan.json`.
3. Planner or Story Graph Director writes `story_graph_plan.json`.
4. Planner runs `bin/check_story_graph_plan.py` and resolves graph blockers.
5. Planner prepares isolated Claude Code workspaces for Scene Dramaturgy, Narrative, Character/World, Mechanics, Art/UI/Video, Runtime, and Checker agents as needed.
6. Each Claude Code agent receives copied inbox context and writes outputs only into its own outbox.
7. Planner reads reports together and updates `coherence_matrix.json`.
8. Planner resolves conflicts and, if needed, asks targeted agents to revise.
9. Checker audits the matrix and artifacts from a separate read-only copied bundle.
10. Planner builds or asks Runtime to build `text_playtest_pack.json`.
11. CLI/MUD playtest verifies route traversal, state, gates, endings, failures, and text fallback for visual facts.
12. Planner approves generation only after blockers/major issues are resolved.
13. Generation Executive runs approved tasks.
14. Checker reviews generated assets and manifests.
15. Runtime Agent assembles `runtime_game_package.json` and loads it in the fixed runtime.
16. Checker playtests and Planner gives final acceptance.

## File Ownership

Recommended ownership:

- Planner: `project_intake.json`, `coherence_plan.json`, `story_graph_plan.json`, `coherence_matrix.json`, planning docs, handoff prompts.
- Narrative: `hybrid_script.json`, narrative report.
- Character / World: `character_design.json`, world/location/prop continuity notes.
- Mechanics: mechanics report, choice/route/state tables.
- Art/UI/Video: asset support plans, prompt constraints, provider payload notes.
- Generation: prompt packs, task records, local manifests.
- Runtime: compiled game data and runtime code.
- Checker: QA reports and coherence audit reports.
- Text Playtest: `text_playtest_pack.json` and scripted transcripts.
- Runtime Package: `runtime_game_package.json`.

If an agent needs to change a file outside its ownership, it should report the requested change instead of editing it directly.

## Gate Checklist

### G0 Project Intake

Required:

- game type and core premise;
- target player experience;
- POV, player identity, and protagonist visibility;
- main characters;
- target playtime;
- ending policy;
- interaction density;
- presentation format and runtime target;
- art direction and reference ownership;
- hard constraints;
- permission to assume, plan, execute agents, and generate paid assets.

### G1 Coherence Plan

Required:

- project promise;
- target runtime and duration;
- discipline scopes;
- budgets;
- hard constraints;
- conflict policy;
- required artifacts.

### G2 Story Graph Plan

Required:

- entry node;
- node ids, node types, acts, and links;
- branch types;
- value system, choice effects, gates, and route matrix;
- ending/failure conditions;
- facts introduced, witnesses, and expected echoes;
- media hooks for visual facts, text fallback, UI, and video candidates;
- `check_story_graph_plan.py` run with no errors.

### G3 Media Story Plan

Required:

- story cells;
- duration budgets;
- first-choice comprehension gate;
- preliminary asset/video/UI slots;
- acceptance criteria per cell.

### G3.5 Scene Dramaturgy

Required:

- every playable unit has a dramatic objective;
- first meaningful choice has establishment and comprehension;
- visible character entrances are justified;
- first appearances are specified;
- every meaningful choice has callback or echo requirements;
- segment/dialogue budgets are explicit;
- asset/video hooks are declared before prompt writing.

### G6 Coherence Matrix

Required:

- every story cell has a row;
- every choice/failure/ending has a row;
- every generated asset has a runtime or QA purpose;
- every runtime visual requirement maps to an asset or runtime-native substitute;
- blockers and major conflicts have Planner decisions.

### G8 Generation

Required:

- approved prompt packs;
- provider payload review;
- no secrets in files;
- character references approved before dependent assets.

### G7.5 Text Playtest

Required:

- all approved endings are reachable;
- all approved failures are reachable;
- locked choices show fair missing-requirement hints;
- every visual-only fact has a text or UI fallback;
- transcripts exist for representative routes;
- Checker has reviewed traversal before media generation.

### G10 Runtime

Required:

- local paths only;
- approved assets only;
- runtime fields match script and matrix;
- route traversal works.

### G11 Final QA

Required:

- player can understand the setup before choices;
- style and character consistency pass;
- mechanics have visible consequences;
- UI does not hide story evidence;
- no blocker issues remain.

## Agent Report

Every agent report should match `../../schemas/agent_report.schema.json` and include:

- scope;
- inputs reviewed;
- outputs produced;
- assumptions;
- conflicts;
- questions for Planner;
- recommended next action.
