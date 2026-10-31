# Complete Game Pipeline Todolist

This TODO tracks the work required to turn the current cross-disciplinary tool into a repeatable pipeline that can produce a complete playable AVG / interactive-video game.

Core goal:

```text
project_intake
-> planner-owned coherence plan
-> isolated multi-agent production
-> validated text/prompt playable package
-> optional paid asset generation
-> fixed runtime loadable game
-> final coherence QA
```

## Current Status

- [x] Tool version is separated from existing playable game cases.
- [x] Core department roles exist under `agent_instructions/`.
- [x] Core schemas exist under `schemas/`.
- [x] Story Intention Gate is documented and schema-visible.
- [x] Visual novel and script-writing tutorial lessons are summarized.
- [x] MiniMax audio capability is documented as a skill reference.
- [x] Isolated Claude Code worker launcher exists.
- [x] Text playtest runner exists.
- [x] Story graph structural checker exists.
- [x] Campus triangle v5 proves a text package can be played in a browser review page.
- [x] Basic one-command pipeline orchestration exists for tool-layer stages.
- [ ] Complete one-command multi-agent production orchestration exists.
- [x] Basic compiler from text/playtest cell packs to `runtime_game_package.json` exists.
- [x] Canonical runtime package validator exists.
- [x] Basic fixed runtime loader exists for `runtime_game_package.json`.
- [x] Provider generation adapters can build sanitized dry-run request manifests.
- [x] Claude Code model routing supports `claude-sonnet-4-6` and `claude-opus-4-7`.
- [ ] Full canonical compiler from all authoring artifacts to `runtime_game_package.json` exists.
- [ ] Stable fixed runtime loader is fully smoke-tested against multiple arbitrary packages.
- [ ] Provider generation adapters are wired into a paid execution/download layer.
- [ ] A full v6 run has proven the latest prompts improve story depth and cross-disciplinary coherence.

## P0 - Make The Tool Executable End-To-End

These are required before claiming the tool can reliably run a complete game.

### P0.1 Orchestrator

- [x] Add a top-level pipeline runner, for example `bin/run_pipeline.py`.
- [x] Support explicit tool-layer stages:
  - [x] `init`
  - [x] `compile`
  - [x] `validate`
  - [x] `manifest`
  - [x] `runtime_preview`
  - [x] `index`
- [x] Support explicit isolated-agent preparation stages:
  - [x] `plan`
  - [x] `story_graph`
  - [x] `world_character`
  - [x] `mechanics`
  - [x] `scene_dramaturgy`
  - [x] `narrative`
  - [x] `art_video_ui_prompts`
  - [x] `audio_prompts`
  - [x] `runtime_agent`
  - [x] `checker`
- [ ] Support complete production execution stages:
  - [ ] `intake`
  - [ ] `coherence_check`
  - [ ] `compile_text_playtest`
  - [ ] `runtime_smoke_test`
  - [ ] `asset_generation`
  - [ ] `final_package`
  - [ ] `final_qa`
- [x] Use isolated Claude Code execution for worker/checker stages.
- [ ] Keep Planner as the only owner of canonical files.
- [ ] Collect every worker `agent_report` into a Planner review folder.
- [x] Add retry policy at `run_claude_agent.py` layer:
  - [x] retry connection/tool-state failures;
  - [x] detect idle progress through stdout/stderr and outbox/scratch file changes;
  - [x] preserve partial outbox outputs only when expected outputs pass presence checks.
- [ ] Add automatic task splitting after repeated stalls.
- [x] Add stage-specific dry behavior for manifest planning; paid execution is absent by design.
- [ ] Add `--text-only`, `--prompt-only`, and `--allow-paid-generation` modes when multi-agent/payed stages are implemented.
- [x] Never run paid image/video/audio generation unless the intake or command explicitly allows it.
- [x] Write `pipeline_status.json`.
- [x] Write `artifact_index.json`.
- [x] Preserve stage status across partial reruns unless `--fresh` is used.
- [x] Verify one real Claude Code checker stage can run and produce outbox reports.
- [x] Use mixed model profile by default:
  - [x] complex planning/writing/checking stages use `claude-opus-4-7`;
  - [x] execution/support stages use `claude-sonnet-4-6`.

Acceptance:

- [x] One command can run init/compile/validate/manifest/runtime-preview/index over existing text/prompt inputs.
- [x] One command can prepare all isolated agent workspaces.
- [ ] One command can run a full text/prompt-only multi-agent production pass from intake to checker report.
- [x] The command emits clear artifacts and logs under one project run directory.

### P0.2 Artifact Layout For Game Cases

- [x] Add `bin/init_game_case.py`.
- [x] Define a canonical game-case directory layout:

```text
games/<project_id>/
  intake/
  planner/
  agents/
  authoring/
  playtest/
  prompts/
  manifests/
  assets/
  runtime_package/
  runtime_preview/
  reports/
```

- [x] Document which artifacts are canonical and which are intermediate.
- [x] Make sure generated games stay outside the reusable tool directory.
- [x] Add a `README.md` template for every generated game case.

Acceptance:

- [x] A new project can be inspected without reading chat history.
- [x] File locations answer: what was planned, what was produced, what was checked, what the runtime loads.

### P0.3 Runtime Package Compiler

- [x] Add a compiler, for example `bin/compile_runtime_package.py`.
- [ ] Input artifacts:
  - [ ] `coherence_plan.json`
  - [ ] `story_graph_plan.json`
  - [ ] `scene_dramaturgy_plan.json`
  - [ ] `hybrid_script.json`
  - [ ] `mechanics_plan.json`
  - [ ] `character_world_bible`
  - [ ] `asset_plan.json`
  - [ ] `audio_plan.json`
- [ ] optional `media_generation_manifest.json`
- [ ] Output:
  - [x] `runtime_game_package.json`
  - [ ] `text_playtest_pack.json`
  - [x] compile report
- [x] Convert long prose into segmented runtime text.
- [x] Preserve character portraits, expressions, backgrounds, CG/video/audio slots as asset references.
- [x] Preserve choice conditions, state effects, locked hints, endings, chapters.
- [ ] Preserve visible callbacks and achievements from full authoring artifacts.
- [x] Emit placeholder/fallback assets when paid generation has not run.

Acceptance:

- [x] A compiled package passes structural runtime validation.
- [x] The same content can be played text-only before asset generation.

### P0.4 Runtime Package Validator

- [x] Add `bin/validate_runtime_package.py`.
- [x] Validate JSON schema when `jsonschema` is installed; always run structural checks.
- [x] Validate graph integrity:
  - [x] `start_node_id` exists;
  - [x] all choice targets exist;
  - [x] all route gates reference known state;
  - [x] all endings are reachable;
  - [x] no accidental orphan nodes unless marked QA-only.
- [x] Validate mechanics:
  - [x] values and variables are used;
  - [x] flags are set and consumed;
  - [x] locked choices have readable hints;
  - [x] every major choice has visible callback.
- [x] Validate assets:
  - [x] all referenced asset ids exist;
  - [x] required local files exist when generation is complete;
  - [x] no API keys;
  - [x] no signed temporary URLs in production packages;
  - [x] fallback paths exist for text-only/prompt-only previews.
- [x] Validate player comprehension:
  - [x] early nodes establish player identity, place, goal, pressure, and basic cast;
  - [x] first major choice has enough information;
  - [x] branch consequences are not fake.

Acceptance:

- [x] Validator exits nonzero on broken package.
- [x] Validator writes a machine-readable report and a human-readable report.

### P0.5 Fixed Runtime Loader

- [x] Promote the v5 review page direction into a reusable fixed runtime.
- [x] Load `runtime_game_package.json` instead of case-specific `game_data.json`.
- [ ] Support:
  - [x] home screen;
  - [x] import / local package load;
  - [x] new game / continue;
  - [x] save slots;
  - [ ] chapter select;
  - [ ] ending records;
  - [ ] achievements;
  - [ ] settings;
  - [x] segmented text reveal;
  - [x] character portraits and expression switching;
  - [x] backgrounds;
  - [x] still images / CG;
  - [x] video playback;
  - [x] BGM / ambience / SFX;
  - [ ] phone overlay;
  - [ ] right-top hint;
  - [ ] memory log;
  - [x] worldline review;
  - [x] click a worldline node to jump into that scene for QA.
- [x] Keep all story-specific content in JSON and assets, not runtime code.

Acceptance:

- [ ] Runtime can load at least two different packages without code changes.
- [x] Static smoke test verifies runtime files are served and JS parses.
- [ ] Browser smoke test verifies play mode and worldline mode.

## P1 - Make Multi-Agent Output Reliable

### P1.1 Agent Contracts And Reports

- [ ] Ensure every agent instruction names:
  - [ ] owned scope;
  - [ ] forbidden scope;
  - [ ] required inputs;
  - [ ] required outputs;
  - [ ] schema target;
  - [ ] conflict report format;
  - [ ] definition of done.
- [ ] Make `agent_report.schema.json` mandatory for all worker outputs.
- [ ] Add checker rule: any unsurfaced conflict blocks final compile.

Acceptance:

- [ ] Planner can compare reports across departments without reading freeform prose only.

### P1.2 Stronger Character / World Schema

- [x] Add `character_world_bible.schema.json`.
- [ ] Cover:
  - [ ] character profile;
  - [ ] desire/fear/contradiction;
  - [ ] relationship to player;
  - [ ] speech style;
  - [ ] visual anchors;
  - [ ] expression needs;
  - [ ] knowledge boundaries;
  - [ ] relationship change arc;
  - [ ] location bible;
  - [ ] prop bible.

Acceptance:

- [ ] Art, narrative, mechanics, and runtime all reference the same character ids and prop ids.

### P1.3 Stronger Audio Plan Schema

- [x] Add `audio_plan.schema.json`.
- [ ] Cover:
  - [ ] BGM cue ids;
  - [ ] ambience cue ids;
  - [ ] UI SFX;
  - [ ] prop SFX;
  - [ ] ending/failure stingers;
  - [ ] optional TTS voice lines;
  - [ ] voice design policy;
  - [ ] video embedded-audio boundary;
  - [ ] muted fallback;
  - [x] MiniMax provider payload intent.

Acceptance:

- [ ] Runtime can know which audio is standalone and which belongs inside generated video.

### P1.4 Prompt Pack Schema

- [x] Add `prompt_pack.schema.json`.
- [ ] Cover:
  - [ ] global style bible;
  - [ ] negative prompt / forbidden content;
  - [ ] character reference dependencies;
  - [ ] image prompts;
  - [ ] video prompts;
  - [ ] audio prompts;
  - [ ] UI concept prompts;
  - [ ] expected runtime usage;
  - [ ] source scene/cell ids;
  - [ ] consistency notes.

Acceptance:

- [ ] Every generated asset prompt maps to at least one runtime use.
- [ ] Every runtime-required asset maps back to a prompt or approved fallback.

### P1.5 Coherence Matrix Automation

- [ ] Generate `coherence_matrix.json` automatically from accepted artifacts.
- [ ] Track each playable beat across:
  - [ ] story function;
  - [ ] player understanding;
  - [ ] character/world dependency;
  - [ ] mechanic effect;
  - [ ] visual asset;
  - [ ] video asset;
  - [ ] audio asset;
  - [ ] UI surface;
  - [ ] runtime node/segment;
  - [ ] QA status.

Acceptance:

- [ ] Checker can identify mismatches without manually reconstructing the whole project.

## P2 - Provider Execution And Asset Management

These are required for a media-complete game, but should run only after P0 text/prompt validation.

### P2.1 Unified Provider Adapter Layer

- [x] Add provider abstraction for:
  - [x] GPT image generation;
  - [x] GPT image editing/reference-image workflows;
  - [x] Volcengine Seedance video task payloads;
  - [x] MiniMax TTS;
  - [x] MiniMax voice design;
  - [x] MiniMax music generation.
- [ ] Add paid execution submit/poll/download implementation for all providers.
- [x] Read secrets only from environment variables during later execution.
- [x] Never write API keys to manifests, reports, logs, runtime JSON, or screenshots.
- [x] Store request payloads with secrets redacted.

Acceptance:

- [x] A dry run prints payload summaries without secrets.
- [ ] A real run downloads assets locally and records sanitized metadata.

### P2.2 Download / Local Manifest / Sanitizer

- [ ] Download all provider outputs into `games/<project_id>/assets/`.
- [ ] Replace signed URLs with local relative paths.
- [ ] Record:
  - [ ] provider;
  - [ ] model;
  - [ ] prompt id;
  - [ ] source scene/cell ids;
  - [ ] local file path;
  - [ ] dimensions/duration/sample rate;
  - [ ] generation status;
  - [ ] retry count;
  - [ ] cost estimate when available.
- [ ] Add sanitizer for:
  - [ ] API keys;
  - [ ] signed URLs;
  - [ ] temporary tokens;
  - [ ] unsafe external paths.

Acceptance:

- [ ] Runtime packages can be shared without leaking credentials or expiring media URLs.

### P2.3 Asset QA

- [ ] Add manifest-level QA:
  - [ ] missing files;
  - [ ] duplicate unused assets;
  - [ ] wrong media type;
  - [ ] wrong duration/ratio;
  - [ ] style mismatch notes;
  - [ ] character consistency notes;
  - [ ] text readability for UI assets.
- [ ] Add optional contact-sheet generation later, but do not block P0.

Acceptance:

- [ ] Asset generation cannot silently produce files that the game never displays.

## P3 - Test With A Real V6 Case

Status: deferred by user. Do not start this until the user chooses a new game case.

### P3.1 Text / Prompt Only V6 Run

- [ ] Create a fresh game case, for example `games/campus_triangle_v1/v6_pipeline_run`.
- [ ] Use latest Planner and agent prompts.
- [ ] Run real isolated Claude Code agents, not simulated subagents.
- [ ] Target 20-30 minutes of playtime.
- [ ] Keep generation disabled.
- [ ] Produce:
  - [ ] intake;
  - [ ] coherence plan;
  - [ ] story intention;
  - [ ] story graph;
  - [ ] character/world bible;
  - [ ] mechanics plan;
  - [ ] scene dramaturgy plan;
  - [ ] hybrid script;
  - [ ] art/video/UI prompt pack;
  - [ ] audio prompt pack;
  - [ ] coherence matrix;
  - [ ] text playtest pack;
  - [ ] runtime package;
  - [ ] checker report.

Acceptance:

- [ ] The game is playable text-only in CLI and browser runtime.
- [ ] Checker says the first major choice is understandable.
- [ ] Estimated true-route playtime is 20-30 minutes.

### P3.2 Review Runtime QA

- [ ] Load the compiled package into the fixed runtime.
- [ ] Verify:
  - [ ] start flow;
  - [ ] choices;
  - [ ] locked choices;
  - [ ] route branches;
  - [ ] all endings;
  - [ ] saves;
  - [ ] chapter select;
  - [ ] achievements;
  - [ ] worldline pan/zoom/click-jump.

Acceptance:

- [ ] User can inspect story coherence through both play mode and worldline mode.

## P4 - Media Complete Run

Status: deferred by user. Do not run paid image/video/audio generation until explicitly approved for a new case.

This starts only after user approval, because it may call paid APIs.

- [ ] Confirm generation budget and providers.
- [ ] Generate or approve final style bible.
- [ ] Generate character base references.
- [ ] Generate expression variants / portrait layers.
- [ ] Generate scene backgrounds.
- [ ] Generate prop closeups.
- [ ] Generate CG/story stills.
- [ ] Generate video first frames.
- [ ] Generate videos.
- [ ] Generate standalone audio where needed.
- [ ] Download all assets locally.
- [ ] Recompile runtime package with local assets.
- [ ] Run final asset/runtime validator.
- [ ] Browser playtest complete game.
- [ ] Produce final release folder.

Acceptance:

- [ ] The game can be played offline/local without provider URLs.
- [ ] All planned assets are either displayed in game or marked unused with reason.

## P5 - Later Improvements

Status: deferred by user. Do not prioritize these before the executable tool chain is stable.

- [ ] UI polish iterations.
- [ ] Godot exporter or adapter.
- [ ] Cost estimator dashboard.
- [ ] Visual contact sheets for human QA.
- [ ] Style A/B testing helper.
- [ ] Voice cloning workflow with consent metadata and legal review.
- [ ] Packaging for external preview links.
- [ ] Regression test suite across sample packages.

## Immediate Recommended Next Steps

1. Build `validate_runtime_package.py`.
2. Build `compile_runtime_package.py`.
3. Promote v5 review page into a reusable fixed runtime loader.
4. Add a minimal orchestrator that can run text/prompt-only stages.
5. Run a real v6 text/prompt-only multi-agent pass.
6. Only after v6 passes coherence QA, enable paid generation.
