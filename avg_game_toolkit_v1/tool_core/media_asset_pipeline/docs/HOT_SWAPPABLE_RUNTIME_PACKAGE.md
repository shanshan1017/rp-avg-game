# Hot-swappable Runtime Package

The fixed runtime should behave like the Story-to-game launcher, but with multimodal AVG support. A game should load by importing one JSON package plus local assets, not by changing runtime code.

## Target File

```text
runtime_game_package.json
```

Schema:

```text
schemas/runtime_game_package.schema.json
```

## Why This Exists

Story-to-game feels compatible because its JSON is already the runtime contract. The launcher does not need to understand the writer's private outline; it only needs nodes, segments, choices, state changes, routes, and endings.

Our runtime package keeps that lightweight state-machine idea, but adds multimodal surfaces:

- background images;
- character portraits and expression switching;
- phone/message overlays;
- right-top hints;
- memory logs;
- images, videos, and audio;
- local asset manifest;
- achievements, endings, chapters, save slots, settings, play stats.

## Runtime Home Features

The default player home should support:

- import JSON;
- local library/cache;
- continue;
- new game;
- ending records;
- achievement records;
- chapter select;
- save slots;
- play stats;
- settings.

Default player builds should not include developer introduction content. Dev tools can exist behind a QA flag, but not as a normal home feature.

## Node Loop

The fixed runtime should implement this loop:

```text
load package
-> start_node_id
-> apply scene/background/character layers/media
-> display segments one by one
-> show choices when segments end
-> apply choice changes
-> jump to callback/target node
-> evaluate routes when needed
-> reach ending/failure
```

## Segment Rhythm

Runtime text must be segmented. A segment is one playable beat:

- one narration sentence;
- one dialogue line;
- one phone message;
- one hint/log/profile note;
- one short system line.

This preserves rhythm and allows character portraits or expressions to change between lines.

## Character Portraits

Recurring visible characters should be defined in `characters` with:

- display name;
- speech style;
- default expression;
- portrait assets per expression;
- optional color/accent.

Nodes and segments can update `character_layers`, so the runtime can show or change:

- who is on screen;
- expression;
- position;
- transition;
- z-index.

## Asset Policy

Production packages should reference local files under `asset_base_path`. Signed remote provider URLs should stay only in generation manifests, not in game-facing runtime data.

Every asset has:

- type;
- path;
- usage;
- required flag;
- alt text;
- optional source manifest id.

Missing required assets should block release. Missing optional assets may degrade gracefully.

## Relationship To Other Artifacts

`runtime_game_package.json` is a compiled delivery artifact, not the only planning artifact.

Upstream planning remains:

```text
project_intake.json
-> coherence_plan.json
-> story_graph_plan.json
-> scene_dramaturgy_plan.json
-> hybrid_script.json
-> asset_plan.json
-> coherence_matrix.json
-> runtime_game_package.json
```

The package is what the fixed runtime loads. The upstream artifacts are what agents and Checker use to prove the package is coherent.
