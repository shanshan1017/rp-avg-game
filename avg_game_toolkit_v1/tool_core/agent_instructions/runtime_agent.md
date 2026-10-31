# Runtime Agent Instruction

## Role

You build or update the fixed game runtime and compile approved content into a hot-swappable `runtime_game_package.json`.

## Highest Rule

The runtime should be stable while games are data. A new story should load by swapping the package JSON and local assets, not by rewriting game code. The runtime must preserve segmented reading rhythm, visible choice feedback, and multimodal presentation planned by upstream agents.

## Inputs

- `runtime_game_package.schema.json`
- approved `story_intention_statement` metadata
- approved hybrid script
- asset manifest
- mechanics plan
- UI surface plan
- Planner constraints

## Output

- `runtime_game_package.json`
- runtime integration report
- smoke-test notes
- `agent_report.json`

## Runtime Must Support

- Home/library screen.
- Import/load JSON package.
- Continue, new game, endings, achievements, chapter select, save slots, settings, play stats.
- Text segments with click/keyboard advance.
- Speaker names.
- Background images.
- Character portraits/expressions/layers.
- Phone/message overlays.
- Right-top hints and memory logs.
- Choice overlay.
- Choice callbacks and state echoes.
- Conditional choices and routes.
- Values, flags, variables, achievements.
- Image, video, and audio local assets.
- Ending/failure screens.
- Optional worldline/review mode for production QA.

## Package Assembly Rules

- Store story-specific content in package data, not runtime code.
- Preserve segment order and segment granularity from Narrative.
- Preserve state effects and route conditions from Mechanics.
- Preserve asset ids and required/optional status from Art/UI/Video.
- Include enough metadata for review: project id, version, title, story intention summary, chapters, endings, achievements, asset manifest.
- Required missing assets should fail loudly in QA mode.
- Optional missing assets should degrade gracefully in player mode.

## Must Not

- Do not hardcode story content in runtime.
- Do not add unapproved assets.
- Do not change branch logic while implementing UI.
- Do not collapse segments into walls of text.
- Do not remove choice callbacks or state echoes.
- Do not require signed remote URLs at play time.
- Do not expose developer introduction content in the default player home screen.

## Done Criteria

- A valid package loads without code changes.
- Package unload/load resets story-specific state safely.
- Save/load keys are scoped by game id and package version.
- Segment clicking, portraits, choices, state changes, and endings can be smoke-tested.
- Missing optional assets degrade gracefully.
- Missing required assets are reported clearly.
- Review mode can help inspect worldline, nodes, assets, and state when available.
