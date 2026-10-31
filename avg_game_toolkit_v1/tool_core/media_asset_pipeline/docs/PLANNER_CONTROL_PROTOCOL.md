# Planner Control Protocol

The Planner is the only role allowed to change the cross-disciplinary plan. Other agents may propose changes, report blockers, or produce scoped outputs, but they should not silently move the project goalposts.

## Planner Responsibilities

- collect or approve `project_intake.json` before starting a new project;
- define the project promise and target experience;
- set target runtime, route depth, video budget, image budget, UI surfaces, and generation constraints;
- assign agent scopes;
- create or approve `story_graph_plan.json` before any writer expands prose;
- define story cells and acceptance criteria;
- approve character, world, mechanics, art, UI, and video baselines;
- maintain the coherence matrix;
- resolve conflicts after agent reports;
- decide whether to continue, revise, regenerate, or stop.

## Planner Does Not Mean Script Dictatorship

The Story Graph pipeline is Director/StoryGraph driven. This version borrows its rigor but avoids making script the top-level authority.

In this tool:

- Narrative can say a scene needs more setup.
- Art can say a planned visual is too risky or too expensive.
- Mechanics can say a choice is fake or too early.
- UI can say a phone overlay should replace a generated image.
- Runtime can say a surface is hard to support cleanly.
- Checker can block the gate if the player cannot understand the result.

Planner then resolves the conflict and updates the plan.

## Mandatory Intake Gate

For a new project, Planner must start from `project_intake.json` or the user-facing questionnaire in `templates/project_intake_questionnaire.md`.

Planner must ask before proceeding when missing information affects:

- runtime target;
- target duration;
- protagonist POV or visibility;
- main cast;
- ending count;
- interaction density;
- art style or reference ownership;
- safety/IP constraints;
- whether agents may execute;
- whether paid image/video generation is allowed.

If the user allows assumptions, Planner may fill conservative defaults and record them. If not, Planner asks short follow-up questions before writing `coherence_plan.json`.

## Mandatory Story Graph Gate

Planner must not jump from a loose brief directly to prose cells. Each project needs a `story_graph_plan.json` that records:

- node types and branch types;
- choices, value effects, gates, and route matrix;
- ending/failure conditions;
- facts introduced and witnesses;
- expected later echoes;
- media hooks for visual facts, text fallbacks, UI surfaces, and video candidates.

This file may be produced directly by Planner or by an isolated Director agent using `templates/story_graph_director_contract.md`. Either way, Planner owns approval and conflict resolution.

Narrative agents may expand local scenes from the graph. They may not silently change node ids, target links, branch types, value attributes, ending conditions, witnesses, or required echoes.

Mechanics, Art, UI, Video, and Runtime agents may challenge the graph, but their challenge returns to Planner as a conflict report.

## Agent Report Flow

Each agent returns `agent_report.json` with:

- what it changed or produced;
- assumptions it made;
- dependencies it requires;
- conflicts it found;
- questions for Planner;
- recommended next action.

Planner reads all reports together and writes a conflict pass:

```text
conflict_id
reported_by
affected_story_cells
affected_assets
affected_mechanics
severity
planner_decision
required_followup
owner
status
```

## Conflict Severity

- `blocker`: cannot proceed without Planner decision.
- `major`: can draft, but generation/runtime should wait.
- `minor`: acceptable for draft, must be noted for QA.
- `accepted_risk`: Planner explicitly accepts the tradeoff.

## Revision Pattern

Use small controlled loops:

1. Planner updates only the affected rows/files.
2. Relevant agent reruns only its bounded task.
3. Coherence auditor rechecks affected rows.
4. Planner either approves or loops again.

Avoid full rewrites unless the conflict exposes a foundation problem.

## Example

Narrative adds a moment where the player notices a cracked stage-light crystal.

Art reports that the existing asset plan has no prop slot for it.

Mechanics reports that the cracked crystal is needed to justify a later blame choice.

Planner decision:

- add `prop_stage_light_crystal` as a required asset;
- add visual evidence row to the earlier story cell;
- keep the later choice locked until this evidence cell is shown;
- ask Art to generate prop reference and ask Runtime to display it in the memory log.
