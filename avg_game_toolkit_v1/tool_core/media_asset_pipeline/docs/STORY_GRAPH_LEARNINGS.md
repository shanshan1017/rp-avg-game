# Story Graph Pipeline Learnings

The Story Graph interactive novel pipeline is useful because it demonstrates how much stronger a project becomes when planning and writing are separated.

Relevant files:

- `<STORY_GRAPH_ROOT>/docs/pipeline.md`
- `<STORY_GRAPH_ROOT>/docs/interactive_novel_design.md`
- `<STORY_GRAPH_ROOT>/pipeline/story_graph_schema.py`
- `<STORY_GRAPH_ROOT>/pipeline/director_agent.py`
- `<STORY_GRAPH_ROOT>/pipeline/writers.py`
- `<STORY_GRAPH_ROOT>/pipeline/auditor.py`

## What To Reuse

### Structured Story Graph

The Story Graph pipeline's `StoryGraph` separates structure from prose. This is valuable:

- nodes;
- choices;
- branch types;
- endings;
- value effects;
- facts introduced;
- witnesses / knowledge boundaries.

For this tool, the story graph is now a required planning gate: `story_graph_plan.json`. It is still not the whole production truth, but every project must pass through it before media story planning.

### Local Writer Context

The Story Graph pipeline avoids handing the whole story to every writer. Each writer receives:

- world bible;
- graph summary;
- local branch details;
- style settings.

This keeps the writer focused and reduces accidental global rewrites.

### Auditor Rules

The Story Graph pipeline has good early checks:

- graph integrity;
- pseudo choices;
- funnel convergence;
- value-system usage;
- ending diversity;
- dead-end connectivity;
- narrative coverage;
- character presence;
- fact tracking.

These should become part of our broader coherence QA.

## What Not To Copy Directly

The Story Graph pipeline is script-driven. Its final product is mostly text. Our product is playable audiovisual media, so script cannot be the only top-level authority.

Direct copying would miss:

- generated image and video feasibility;
- recurring character visual consistency;
- runtime UI surfaces;
- first-person camera rules;
- asset budget and generation order;
- local manifests and provider payloads;
- visual comprehension before choices;
- video-vs-still tradeoffs.

## Adaptation

The Story Graph pipeline's `Director` becomes one part of the Planner's toolkit.

In this version:

- Planner owns the coherence plan.
- Narrative owns script expansion.
- Character/world owns visual and knowledge constraints.
- Mechanics owns choice/state/ending logic.
- Art/UI/video own production feasibility and surface design.
- Checker owns independent coherence review.

The Planner may revise the story after Art or Mechanics reports a conflict. That is the major difference from a pure script-driven pipeline.

## Tool-Level Adoption

New reusable artifacts:

- `schemas/story_graph_plan.schema.json`
- `templates/story_graph_director_contract.md`
- `templates/story_graph_plan.template.json`
- `docs/STORY_GRAPH_PLANNING_GATE.md`

These files make the Story-Graph-style Director step explicit. Future projects should not jump directly from a loose Planner brief to a list of cells. The required order is:

```text
coherence_plan.json
  -> story_graph_plan.json
  -> media_story_plan.json
  -> hybrid_script.json
```

The story graph must define branch type, value effects, route matrix, ending conditions, witness lists, and expected echo points before writers expand text or art/video agents plan assets.
