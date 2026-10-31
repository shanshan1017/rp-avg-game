# Cross-Disciplinary Coherence

Cross-Disciplinary Coherence is the quality target for this tool version. It asks whether the game package works as one system, not whether any single document looks good in isolation.

## Definition

A project is coherent when:

- the story explains enough for the player to make meaningful decisions;
- the visuals show or support the facts the story relies on;
- the mechanics create consequences that match the story stakes;
- video is used where motion, timing, voice, or reveal matters;
- UI surfaces clarify information without replacing missing story logic;
- runtime data references only approved assets and approved beats;
- QA can trace every player-facing element back to a planned purpose.

## Difference From Schema and Manifest

Schema answers: is the file shaped correctly?

Manifest answers: where are the generated files and what is their status?

Coherence answers: do the story, assets, mechanics, UI, and runtime actually support the same player experience?

Schema and manifest are necessary, but they are below this layer.

## Traceability Row

Every important story cell, choice, failure, and ending should have one row in the coherence matrix:

```text
story_cell_id
story_purpose
player_must_understand
characters_present
knowledge_boundaries
dialogue_requirements
visual_evidence_required
assets_required
ui_surfaces_required
mechanics_and_state_changes
video_requirement
runtime_fields
qa_acceptance
open_conflicts
planner_resolution
```

The upstream source for these rows is `story_graph_plan.json`, not an improvised prose outline. `media_story_plan.json` and `hybrid_script.json` may add production detail, but they should not erase graph decisions such as branch type, choice effect, knowledge boundary, or ending condition.

## Acceptance Rules

### Player Comprehension

Before a meaningful choice, the matrix must prove that the player knows:

- who they are;
- where they are;
- who is asking or pressuring them;
- what each option means emotionally or mechanically;
- what risk or cost is plausible.

### Asset-Story Traceability

Each generated asset must be referenced by at least one runtime beat or QA-only review surface. Each runtime visual requirement must point to an approved asset slot or an explicit runtime-native substitute.

### Mechanics-Story Alignment

Choices should not be merely decorative. They need at least one of:

- route change;
- state change;
- unlock/lock condition;
- later echo;
- failure/ending consequence;
- visible relationship or knowledge change.

These consequences should first be declared in the story graph through `branch_type`, `value_effects`, `gate_condition`, `route_matrix`, and `echo_points_required`.

### Art Consistency

Recurring visible characters must be generated from approved character references, with role-specific pose/expression slots. Group scenes require explicit approval because they raise consistency risk.

### Video Budget Discipline

A video slot should justify why it cannot be equally clear as text+image. Use video for:

- emotional turning points;
- time-sensitive reveals;
- physical action;
- first-person embodied moments;
- ending payoff.

Use text+image for:

- exposition;
- internal thought;
- message exchanges;
- clue review;
- low-motion transitions.

## Planner Conflict Loop

When a row fails coherence, the Planner chooses one of four actions:

1. Revise story: rewrite or add a story cell.
2. Revise asset plan: add, remove, merge, or change an asset slot.
3. Revise mechanic/UI: alter choice timing, state feedback, or display surface.
4. Defer: mark the issue as accepted risk with a clear reason.

Worker agents should report conflicts. They should not silently redesign another discipline's output.
