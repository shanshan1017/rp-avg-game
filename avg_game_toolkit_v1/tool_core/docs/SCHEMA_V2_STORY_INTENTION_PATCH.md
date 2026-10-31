# Schema V2 Story Intention Patch

This patch makes the new agent prompt requirements schema-visible without breaking the hot-swappable runtime package model.

## What Changed

### Authoring Schemas

- Added `schemas/story_intention.schema.json`.
- Added required `coherence_plan.story_intention`.
- Added `story_graph_plan.story_intention_alignment`.
- Added scene-level `intention_function`, `presentation_mode`, and `visual_novel_triad` to `scene_dramaturgy_plan.schema.json`.

These are authoring-time contracts. They help Planner, Director, Dramaturgy, Writer, Art, Audio, Runtime, and Checker agents share the same dramatic target before runtime assembly.

### Runtime Schema

- Added optional `runtime_game_package.meta.story_intention_summary`.
- Added optional `runtime_game_package.meta.content_design_tags`.

Runtime logic must not depend on these fields. They are for review mode, library display, and QA context. The core hot-swappable runtime remains driven by nodes, segments, choices, state, assets, characters, scenes, endings, achievements, and local asset references.

### Department / Discipline Support

- Added `audio` as a first-class discipline in `coherence_plan.schema.json`.
- Added required `budgets.audio_assets`.
- Added `new_audio_slot` and `revise_audio_plan` to conflict policy enums.
- Added audio asset types and capabilities to `media_asset_plan.schema.json`.
- Added `agent_instructions/audio_agent.md`.

## Compatibility Rule

The runtime package stays flexible:

```text
runtime code + runtime_game_package.json + local assets
```

New story-intention fields are mostly authoring-side. Existing runtime loaders can ignore `meta.story_intention_summary` and still play the game as long as they already support the normal package fields.

## Why This Matters

The tool can now enforce two tutorial-derived rules:

1. A story graph must come from a core intention, not a list of events.
2. Every playable scene must connect narrative, presentation, and interactivity.

This makes multi-agent output easier to audit before spending on image or video generation.

