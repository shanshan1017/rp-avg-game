# Story Graph Planning Gate

This gate prevents every new project from relying on ad hoc Planner instinct. It turns the Story Graph pipeline lesson into a reusable tool step.

## Position In The Tool

The story graph sits between the top-level coherence plan and the media story plan:

```text
coherence_plan.json
  -> story_graph_plan.json
  -> media_story_plan.json
  -> hybrid_script.json
  -> asset_plan.json
  -> coherence_matrix.json
```

`coherence_plan.json` owns the whole production promise. `story_graph_plan.json` owns the playable narrative system. `media_story_plan.json` translates that system into text/image/video/UI production units.

## Why This Exists

The Story Graph pipeline is strong because its Director creates a structured graph before writers expand prose. That graph defines choices, branches, endings, value effects, facts, and knowledge boundaries. Writers cannot accidentally redesign the whole story while writing a local scene.

Our tool needs the same story rigor, but it also has to serve art, video, UI, runtime, cost, and player comprehension. The story graph therefore includes media hooks, but does not become the only source of truth.

## Required Output

The Planner or a dedicated Director agent must produce:

- `story_graph_plan.json`
- valid against `schemas/story_graph_plan.schema.json`
- optionally seeded from `templates/story_graph_director_contract.md`

Then run:

```bash
python bin/check_story_graph_plan.py /absolute/path/to/story_graph_plan.json --fail-on-error
```

## Required Contents

The graph must include:

- node ids, node types, acts, branches, and next-node links;
- branch types: `pearl_string`, `strong`, `value_based`;
- value attributes and ending conditions;
- choice effects, gate conditions, and expected later echoes;
- fact introduction and witness lists;
- route matrix for true, character/good, neutral/bad, failure, and hidden routes as applicable;
- media planning hooks for visual facts, text fallbacks, asset hints, UI hints, and video candidates.

## Anti-Pattern Checks

Before Narrative expansion, the graph should be checked for:

- pseudo choices;
- funnel convergence without later echo;
- unused value system;
- endings decided only by the final choice;
- failure nodes without causal entry;
- orphan nodes;
- character knowledge leaks;
- required facts that cannot be shown, said, or surfaced in UI.

## Agent Boundaries

The Director/Planner may decide graph structure.

Narrative agents may expand scenes, but should not change:

- node ids;
- node type;
- branch type;
- target nodes;
- ending conditions;
- value attributes;
- witnesses;
- required echo points.

Mechanics agents may report that a choice is fake or a gate is weak, but must not silently rewrite the graph.

Art/UI/Video agents may report that a required media hook is too expensive, risky, or unclear. Planner then revises the graph or media plan.

Checker agents review graph, media plan, and script together.

## Gate Exit Criteria

The project may proceed to `media_story_plan.json` when:

- every meaningful choice has at least one consequence path: state, route, gate, echo, failure, or ending;
- every ending has a distinct condition or route rationale;
- every failure is fair and causally connected;
- every major fact has an introduction node and witness boundary;
- every required visual fact has a media hook or text/UI fallback;
- the true route duration budget is plausible before prose expansion.
