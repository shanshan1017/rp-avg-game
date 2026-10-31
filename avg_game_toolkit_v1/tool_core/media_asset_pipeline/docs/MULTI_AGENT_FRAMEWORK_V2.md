# Multi-Agent Framework V2

> Coherence V1 note: this copied version keeps the V2 framework for continuity, but the authoritative control model is now Planner-first. Read `ARCHITECTURE.md`, `CROSS_DISCIPLINARY_COHERENCE.md`, and `PLANNER_CONTROL_PROTOCOL.md` before using this file. In conflicts, Planner decisions and `coherence_matrix.json` override individual agent preferences.

This framework separates reusable tool work from a single game case. A game can be used to test the tool, but the tool must not depend on that game's characters, story, or folders.

## Agents

### 1. Planning Agent

Default owner: Codex in the main thread.

Owns:

- project brief normalization
- route graph
- planner-level story plan with duration budgets, content requirements, and asset slots
- story cell budgets: how many narration, dialogue, phone, hint, memory, video, and choice beats each unit should contain
- style and safety rules
- runtime asset contract
- agent handoffs
- final go/no-go between gates

Does not own:

- silent story rewrites after approval
- bulk generation
- final QA approval without Checker input

### 2. Narrative Agent

Owns:

- fuller script expansion
- player comprehension contract
- text/image/video presentation mode decisions
- dialogue, narration, phone messages, memory logs
- transition logic between units

Must output:

- `story_plan.json` matching `schemas/media_story_plan.schema.json`
- `hybrid_script.json`
- narrative QA notes
- list of facts the player must know before each choice

Must use:

- the Planning Agent's unit roles, duration budgets, content round budgets, character appearances, and asset slots

Must ask Planning before:

- adding a new visible character
- adding a new background/location
- adding a new prop that requires art
- adding a new video beat
- changing a choice target or ending

### 3. Character / World Agent

Owns:

- character bible expansion
- visual anchors
- relationship arcs
- speaking style
- location and prop continuity

Must output:

- character design docs
- location/prop sheets when needed
- consistency constraints for art prompts
- reusable character pose / expression requirements for runtime dialogue layers

### 4. UI Art Agent

Owns:

- UI visual directions
- title / dialogue / choice / log / phone overlay concept prompts
- art-direction contact sheets
- UI asset plan
- an art completeness audit against the planner's asset slots and the narrative script

Must not:

- implement runtime CSS directly unless assigned
- generate UI that blocks core video or scene art
- reference existing IP names in prompts

### 5. Video Agent

Owns:

- video-specific prompt expansion
- first-frame-to-video / reference-video task setup
- tail-frame chaining decisions when approved
- video duration, ratio, audio, and watermark settings

Must not:

- add extra video clips beyond the planner's video asset slots
- use story text baked into video frames when the runtime should render it as UI
- change narrative timing without Narrative/Planning approval

### 6. Generation Executive Agent

Owns:

- prompt packs
- API task submission
- local downloads
- sanitized manifests
- generation error reports

Must not:

- redesign narrative structure
- add unreferenced assets
- write API keys or signed URLs into repo files

Must preserve:

- approved character references as exact reference inputs for character pose and scene images
- scene-specific reference hygiene: single-character reference for single-character scenes, multi-character references only for planned group scenes
- separate runtime assets for background, character layer, props, video first frame, and video clip where the plan asks for them

### 7. Runtime Integration Agent

Owns:

- compiling approved script and manifests into game data
- HTML/CSS/JS or Godot runtime package
- save state and route state behavior
- local smoke test

Must not:

- import unapproved assets
- change story beats without Narrative/Planning approval

### 8. Checker Agent

Owns independent review.

Checks:

- story comprehension
- schema validity
- asset-to-runtime mapping
- local file existence
- visual and character consistency
- first-person rules
- UI readability
- no secrets or signed URLs in game-facing files

Must not:

- silently patch production outputs
- approve generated assets only because files exist

## Gate Flow

```text
G0 intake
G1 route graph
G2 story bible + character/world bible
G3 planner story plan with content budgets and asset slots
G4 narrative expansion into hybrid script
G5 art/UI completeness audit + asset plan
G6 prompt packs
G7 video-specific payload review when video slots exist
G8 generation
G9 checker visual/story/runtime QA
G10 runtime integration
G11 final playtest + acceptance
```

## Folder Policy

Reusable tool files:

```text
media_asset_pipeline/
skills/interactive-media-asset-pipeline/
schemas/
templates/
```

Game case files:

```text
games/<project_id>/
video_engine/public/<project_id>/
video_engine/public/assets/<project_id>/
```

Recommended game case layout:

```text
games/<project_id>/
  planning/
    project_brief.json
    story_bible.json
    character_design.json
    story_plan.json
    hybrid_script.json
    asset_plan.json
  outputs/
    prompt_pack/
    provider_payloads/
    manifests/
    qa/
  scripts/
    project-specific adapters only
```

`media_asset_pipeline/examples/` may contain small samples, but production case files should live under `games/<project_id>/`.

## Completion Definition

A case is ready to generate only when:

- first meaningful choice is narratively justified
- every choice has required player understanding
- video is reserved for high-value beats
- every unit has content round budgets and explicit asset slots
- every dialogue-heavy unit declares whether visible characters are scene-baked or separate runtime character layers
- the Narrative Agent has not added unplanned visual requirements
- the Art Agent has checked that every scripted visual requirement maps to an asset slot
- every planned image/video/UI asset maps to a runtime field
- Checker has zero blockers for the current gate
