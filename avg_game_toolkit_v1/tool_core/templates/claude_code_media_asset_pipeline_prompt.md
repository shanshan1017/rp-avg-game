# Claude Code Media Asset Pipeline Prompt

You are helping the Planning Agent prepare an Executive and Checker handoff in a multi-agent interactive media asset pipeline.

The Planning Agent is Codex in the main thread. Executive and Checker agents must be separate Claude Code sessions.

## Inputs

- Project brief: `<path to project_brief.json>`
- Optional style profile: `<path to style profile>`
- Optional user references: `<paths to image/video/audio references>`
- Project-local skill: `interactive_video_game/skills/interactive-media-asset-pipeline/SKILL.md`

## Task

Do not submit paid generation jobs in this pass.

Produce:

1. `story_bible.json` matching `interactive_video_game/schemas/media_story_bible.schema.json`
2. `character_design.json` matching `interactive_video_game/schemas/media_character_design.schema.json`
3. `character_design.md` as the human-readable character design doc
4. `script_table.json` matching `interactive_video_game/schemas/media_script.schema.json`
5. `asset_plan.json` matching `interactive_video_game/schemas/media_asset_plan.schema.json`
6. `handoff/EXECUTIVE_HANDOFF.md`
7. `handoff/CHECKER_HANDOFF.md`
8. A short human-readable review note listing assumptions, risks, and approval questions

## Rules

- Plan the full storyline and branching graph before expanding node details.
- Write character design before script table and asset plan.
- Every generated asset must be referenced by the runtime asset contract.
- Generate or approve character references before posters and videos.
- Scene posters may only use references for characters that actually appear in that node.
- Do not use a cast lineup as a scene reference unless the scene contains the entire cast.
- Do not use real people, celebrities, public figures, or existing IP as visual references.
- Do not write API keys or signed platform URLs into any output.
- For first-person projects, the protagonist is the camera unless the brief says otherwise.
- Write uncertainties as questions or assumptions, not hidden changes.
- Include current gate id, allowed write scope, forbidden changes, and acceptance criteria separately for Executive and Checker.

## Capability Names

Use only these capability names in `asset_plan.json`:

- `image.text_to_image`
- `image.reference_edit`
- `image.mask_edit`
- `image.responses_multiturn`
- `image.streaming`
- `video.text_to_video`
- `video.first_frame_to_video`
- `video.reference_image_to_video`
- `video.reference_video_to_video`
- `video.reference_audio`
- `video.last_frame_chain`
- `manual.import`
- `skip`

## Output Style

Be concrete. Prefer explicit ids, local output paths, and exact runtime fields over prose.
