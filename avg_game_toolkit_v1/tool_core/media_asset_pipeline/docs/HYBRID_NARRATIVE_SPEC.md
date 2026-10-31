# Hybrid Narrative Spec

This pipeline no longer assumes every story node must be a video. The default production model is:

```text
text + image for exposition, relationship context, inner thought, phone messages, logs
video for emotionally important beats, reveals, reversals, and endings
choice UI only after the player has enough context to choose
```

## Why

Pure video is expensive and easy to under-explain. If a 10 second clip must communicate identity, location, relationship history, stakes, and a branch decision at once, players often understand the mood but not the story.

The script therefore needs a **player comprehension contract** before asset generation:

- Who am I?
- Where am I?
- Who is on screen?
- What is my relationship with them?
- What changed in this unit?
- Why am I choosing now?
- What does each choice mean emotionally or mechanically?

## Presentation Modes

### `text_image`

Use for:

- opening context
- relationship setup
- phone/message/log UI
- route recap
- quiet emotional beats
- low-cost transitions

Required assets:

- one story still or background
- optional character portrait
- text layers

### `video`

Use for:

- character entrance
- emotional turn
- magic or action reveal
- moment that benefits from movement, voice, music, or timing
- ending payoff

Required assets:

- approved first frame
- video clip
- optional tail frame

### `text_image_choice`

Use when the player should choose after reading context rather than after a full clip.

Required checks:

- `choice_rationale` is explicit
- `required_understanding_before_choice` is satisfied by previous or current text layers

### `video_choice`

Use only when the video itself clearly sets up the decision.

Required checks:

- the video does not rely on unreadable text embedded in the image
- if the choice depends on messages or hidden context, that context also appears in the frontend text layer

## Planning Unit vs Script Unit

V2 separates two layers:

### Planner Story Plan

Schema: `schemas/media_story_plan.schema.json`

The Planning Agent writes this first. It controls:

- unit role and route position
- duration budget
- what the player must learn
- how many narration/dialogue/message rounds the writer should produce
- which characters may appear
- which UI surfaces are needed
- exact asset slots required by runtime
- which agent owns each slot
- checker acceptance criteria

The planner does **not** write every final line of dialogue.

### Hybrid Script

Schema: `schemas/media_hybrid_script.schema.json`

The Narrative Agent expands the story plan into playable content:

- concrete narration rounds
- dialogue rounds
- phone messages
- right-top hints
- choice copy
- timing and ordering inside the unit

The hybrid script must satisfy the story plan. If it introduces a character, prop, background, UI surface, or video not listed in the plan's asset slots, it must ask Planning for a plan update.

## Story Unit Contract

Every story unit must define:

- `player_context`: what the player already knows before this unit starts
- `new_information`: facts this unit adds
- `visual_evidence`: what image/video must show
- `text_evidence`: what frontend text must state
- `required_understanding_before_choice`: facts required before any choice appears
- `transition_from_previous`: why this unit follows the last one
- `media_assets`: exact asset ids used in runtime

For production, every unit should also have a planner-level asset slot list:

- background or still slot
- optional character pose / portrait slots
- optional prop reference slots
- optional phone or system overlay slots
- optional video first frame and video clip slots
- optional UI overlay slots

If a unit has choices, it also needs:

- `choice_rationale`
- choice labels that describe intent, not vague actions
- target unit ids that are reachable

## Cost Policy

Recommended 1-2 minute interactive video structure:

- 35-50% `text_image`
- 35-45% `video`
- 10-20% `choice` or `ending` overlays

For short demos, start with 3-5 videos and use images/text for the rest. Generate more video only after narrative QA approves that the player understands the route.

## Unit Composition Pattern

A rich `text_image` or `text_image_choice` unit may contain:

- background image
- optional character layer
- 2-5 narration rounds
- 0-4 dialogue rounds
- 0-3 phone/message rounds
- right-top hint or countdown
- optional memory/log unlock
- optional choice overlay

The story plan controls the min/target/max number of rounds. The Narrative Agent writes the actual text.

Example:

```text
Unit: prologue corridor
Background: after-school corridor with charm and clock tower
Narration: 3 rounds
Phone messages: 0
Dialogue: 0
Right-top hint: fireworks countdown
Choice: none
Assets: corridor background, charm prop, countdown UI treatment
```

This is different from a pure outline. It is a production request that tells writers and artists what must exist.

## Story Cell Execution Contract

V3 treats each story unit as a **story cell**, not a single caption attached to an image. The Planning Agent defines the cell budget and asset contract; the Narrative Agent writes the concrete sequence.

A production story cell can include:

- `set_background`: one approved background or still
- `show_character`: optional portrait / bust / expression layer
- `narration`: protagonist inner thought or third-person system prose
- `dialogue`: named speaker line
- `phone_message`: runtime-rendered message UI
- `right_top_hint`: compact status, countdown, clue, or bond hint
- `memory_log`: optional evidence/profile unlock
- `play_video`: only for approved key video slots
- `choice`: final step after comprehension requirements are satisfied

The Narrative Agent should output both flat `text_layers` for readability and ordered `sequence_steps` for runtime compilation. The runtime should never be forced to infer ordering from a paragraph.

## Character Layer Policy

For reusable visual novel style scenes, character presence should usually be split into:

- background/still art for place and props
- reusable character pose or expression assets for dialogue
- runtime text for names, choices, hints, and story facts

If a generated still already contains a character, the plan must say whether that character is scene-baked or whether a separate runtime layer is still required. For recurring dialogue, prefer separate character pose assets so expression and placement can change without regenerating the whole background.

Art and Checker agents must verify:

- each visible speaking character has either a scene-baked still reference or a `character_pose` slot
- the prompt uses the approved character reference, not a cast lineup, unless the scene intentionally contains the whole cast
- multi-character stills are marked high risk
- protagonist body, hands, reflections, and face remain hidden for first-person games unless the plan explicitly permits otherwise

## QA Rules

Checker must block generation if:

- the first choice appears before identity, location, and relationship context are clear
- a choice depends on information only implied by a model-generated image
- a video prompt includes message/text content that the frontend does not also render
- a scene uses more characters than the script unit allows
- an asset exists but no runtime field displays or plays it
- the Narrative Agent adds a visible character, prop, or UI surface not present in the planner asset slots
- the Art Agent cannot map every required visual element in the script to an asset slot

## Runtime Implications

The game runtime should support:

- still scene display
- dialogue/narration box
- phone/message overlay
- character profile popover or memory log
- video scene playback
- choice layer
- route state updates

Runtime data should consume `media_hybrid_script.schema.json` or a compiled equivalent, not only a flat video-node table.
