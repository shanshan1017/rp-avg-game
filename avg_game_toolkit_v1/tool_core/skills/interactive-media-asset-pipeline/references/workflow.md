# Workflow

## Multi-Agent Baseline

Use at least three roles:

- Planning Agent: Codex in the current thread, owns the story plan, schemas, asset plan, and user approval.
- Executive Agent: Claude Code worker, executes only approved prompt/generation/manifest work.
- Checker Agent: Claude Code worker, independently reviews outputs and writes a QA/rerun report.

See `multi_agent_workflow.md` for detailed role boundaries.

Use `../../agent_instructions/` when launching isolated workers. These role files are the canonical prompts for Planner, Story Graph Director, Scene Dramaturgy, Narrative, Character/World, Mechanics, Art/Video/UI, Audio, Runtime, and Checker agents.

## Gate 0: Intake

Normalize every new user request into `project_intake.json` first, then derive a production project brief:

- Input types: text premise, full script, images, videos, audio references, style notes, runtime target
- Runtime target: HTML first unless the user chooses Godot
- Session length, node length, number of endings, number of choice points
- Protagonist visibility rule
- Safety boundaries and reference ownership
- Runtime asset contract

Required permission fields:

- May Planner make assumptions?
- May Planner start planning?
- May agents execute?
- Is paid image/video/audio generation allowed now?

If the user has not answered a field that changes story structure, runtime, safety, cost, or execution permission, ask before continuing.

Do not start art generation until the runtime asset contract says where each asset will appear.

## Gate 1: Storyline

Plan the complete route graph first as `story_graph_plan.json`, not as a loose prose outline.

Required checks:

- Entry node exists.
- Every choice target exists.
- Every ending and failure node is reachable.
- Typical playthrough length matches the target.
- Branches are meaningful, not only cosmetic.
- State variables are named before detail writing.
- Branch type, value effects, route matrix, ending conditions, witnesses, and expected later echoes are explicit.

Run:

```bash
python bin/check_story_graph_plan.py /absolute/path/to/story_graph_plan.json --fail-on-error
```

## Gate 2: Story Bible

Define:

- World premise
- Tone
- Visual style profile
- Main cast
- Character visual anchors
- Locations
- Recurring props
- Music/audio direction
- Protagonist visibility rule

Recurring characters need approved references before posters and videos.

## Gate 3: Planner Media Story Plan

Planning Agent writes `media_story_plan.schema.json` from the approved story graph before the Narrative Agent writes final dialogue.

Each unit plan needs:

- unit role
- presentation target
- duration budget
- planner intent
- player context at start
- must-deliver information
- background requirements
- character appearances
- narration/dialogue/message round budgets
- right-top hints or other UI surfaces
- choice requirements
- asset slots with owners
- agent briefs
- acceptance criteria

This gate answers: "What must the writer write and what must the artist generate?"

Blocking issue: a unit cannot ask the Narrative Agent to write a visual prop, visible character, background, or video unless it has a corresponding asset slot.

## Gate 4: Hybrid Script

Before writing the hybrid script, create `scene_dramaturgy_plan.json`. This is the missing bridge between graph and prose.

Each planned scene needs:

- player context;
- current pressure;
- active characters and what each wants now;
- conflict or obstacle;
- scene turn;
- first appearance requirements;
- visible evidence;
- text evidence;
- runtime surfaces;
- segment/dialogue budget;
- choice callback requirements;
- branch information boundary;
- asset/video hooks.

Blocking issue: a story unit cannot move to final writing if it only summarizes facts and does not define a playable scene turn.

Default to `media_hybrid_script.schema.json` for interactive video projects. Use the older flat script table only for simple all-video prototypes.

Each story unit needs:

- `unit_id`
- `presentation_mode`: `text_image`, `video`, `text_image_choice`, `video_choice`, `ending`, `failure`
- target duration
- player context before the unit
- new information delivered by the unit
- visual evidence: what image/video communicates
- text evidence: what narration/dialogue/phone UI/log must say
- transition from previous unit
- required understanding before choice
- media asset ids
- choices and target unit ids when present

This is the main handoff surface for prompt generation and runtime integration.

Blocking issue: the first meaningful choice cannot appear until the player knows who they are, where they are, who the visible characters are, what the relationship stakes are, and why the choice matters.

## Gate 5: Asset Plan

For every story plan asset slot and hybrid script unit, decide which assets exist and why:

- Character reference images
- Location reference images
- Story stills for text-image units
- Node poster / first frame for video units
- Node video for key beats only
- Tail frame
- UI concept / UI production assets
- Optional audio reference
- Standalone BGM / ambience / SFX / voice-line slots when runtime needs audio outside generated videos

Every asset must include:

- Runtime usage
- Generation capability
- Input references
- Local output path
- QA requirements

Before prompt pack, the Art/UI Agent must check:

- every background requirement maps to a story still or reusable background
- every visible character maps to an approved character reference or pose slot
- every prop mentioned in the script maps to an asset slot
- every UI surface required by the script maps to a UI plan or runtime-native component
- every video unit has a first frame and video clip slot
- every video unit has embedded audio intent when `generate_audio=true`
- every non-video audio cue maps to a runtime scene, UI event, route echo, or ending/failure state

## Gate 6: Prompt Pack

Prompt pack order:

1. Style profile prompt
2. Character prompts
3. Location prompts when needed
4. UI concept prompts when the runtime needs a new interface direction
5. Story still prompts
6. Poster / first-frame prompts
7. Video prompts
8. Standalone TTS/music prompts for approved non-video runtime audio slots
9. Negative constraints

Prompts must preserve approved style and character anchors. Scene prompts must not introduce characters that are not in the script table.

## Gate 7: Generation

Owner: Executive Agent.

Recommended order:

1. Generate or approve character references.
2. Generate required environment or prop references.
3. Generate UI concepts when assigned and route them to human selection before CSS implementation.
4. Generate required story stills.
5. Generate node posters / first frames for key video units.
6. Generate videos from approved posters and exact references.
7. Generate standalone audio only for approved non-video runtime slots.
8. Save tail frames only when the video API returns them.
9. Write generation manifests.

## Gate 8: QA

Owner: Checker Agent.

Check:

- All local paths exist.
- No game-facing manifest contains API keys or signed platform URLs.
- Each runtime asset is referenced by the game config.
- No unreferenced generated asset entered the production manifest.
- Character identity and outfit remain consistent.
- First-person protagonist rule is respected.
- Scene poster and video contain only intended characters.
- Video duration and ratio match runtime needs.
- Video prompts include embedded audio intent when video audio is enabled.
- Standalone audio assets are not duplicated from video-internal sound.
- Voice-design/TTS/music outputs are stored locally and use licensed/original voices only.
- The player comprehension contract is satisfied before each choice.
- Text/image units are not missing required text evidence.
- Video units are reserved for meaningful beats, not every minor transition by default.

## Gate 9: Runtime Package

Owner: Planning Agent after reading the Checker report, or a separate implementation worker after explicit approval.

Only after assets are approved:

- Build `runtime_game_package.json` from the script table, mechanics plan, character/world bible, and generation manifest.
- Preserve presentation modes in runtime data.
- Support still image + text units, video units, choice overlays, memory/log overlays, and endings.
- Keep assets under the runtime public directory or Godot import directory.
- Preserve source manifests and prompt packs in `outputs/<game_id>/`.
- Keep rerolls in attempt-specific folders.

The fixed runtime should support Story-to-game-like home functions except developer introduction content:

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

Blocking issue: game-specific story, branch, or asset logic hardcoded into runtime code instead of `runtime_game_package.json`.
