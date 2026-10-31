# Checker Handoff: campus_triangle_v1

You are the Checker Agent. Read only. Do not modify files, generate assets, submit jobs, or patch schemas.

## Scope

Review the Planning output for:

- A 1-2 minute first-person interactive video game.
- University campus love triangle / light fantasy.
- Three adult female leads:
  - Lin Cheng, childhood friend.
  - Tang Lingyin, tsundere from the next class.
  - Xing Mi, otherworldly servant.
- Male protagonist is first-person camera and must not appear.
- No image or video generation in this trial.

## Files To Review

- `interactive_video_game/media_asset_pipeline/examples/campus_triangle_v1/project_brief.json`
- `interactive_video_game/media_asset_pipeline/examples/campus_triangle_v1/story_bible.json`
- `interactive_video_game/media_asset_pipeline/examples/campus_triangle_v1/character_design.md`
- `interactive_video_game/media_asset_pipeline/examples/campus_triangle_v1/character_design.json`
- `interactive_video_game/media_asset_pipeline/examples/campus_triangle_v1/script_table.json`
- `interactive_video_game/media_asset_pipeline/examples/campus_triangle_v1/asset_plan.json`
- `interactive_video_game/media_asset_pipeline/examples/campus_triangle_v1/PLANNING_REPORT.md`
- `interactive_video_game/schemas/media_project_brief.schema.json`
- `interactive_video_game/schemas/media_story_bible.schema.json`
- `interactive_video_game/schemas/media_character_design.schema.json`
- `interactive_video_game/schemas/media_script.schema.json`
- `interactive_video_game/schemas/media_asset_plan.schema.json`

## Required Checks

1. JSON syntax and schema shape.
2. Storyline reachability: entry, all choice targets, failure, endings.
3. Typical route duration should be 60-120 seconds.
4. Characters should be adult and visually distinct.
5. Every visible recurring character has detailed narrative, relationship, visual, voice, and generation rules.
6. First-person male protagonist must remain invisible.
7. Script `required_assets` must map to asset plan entries.
8. Asset plan should only include assets referenced by runtime or approved production references.
9. Multi-character nodes must be marked high risk and must not use cast lineup references.
10. No API keys, signed URLs, or paid generation instructions.

## Output

Return:

- PASS / PASS_WITH_NOTES / FAIL
- Blocking issues
- Non-blocking notes
- Concrete recommended revisions
