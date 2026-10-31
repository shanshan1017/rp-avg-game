# Prompting Rules

## Style Lock

Use one style profile per project. A style profile should define:

- Medium and rendering style
- Palette
- Linework
- Lighting
- Camera language
- Detail density
- Forbidden styles

Do not invent a new art style inside individual scene prompts unless the user explicitly changes the project style.

## Character Consistency

Character prompts should produce a clean approved reference first. Use stable anchors:

- Face shape and expression tendency
- Hair color, length, silhouette
- Outfit and accessory anchors
- Color accents
- Body language
- Age as adult and story-safe

Poster and video prompts should cite the approved character reference and repeat the most important anchors in text.

For AVG dialogue sprites, consistency must be enforced structurally, not by prose:

- First generate one approved reference or base cutout per recurring character.
- Expression and pose variants must use reference-image generation/editing with `input_asset_ids`.
- Runtime sprites must be cutout-ready: transparent background when supported, otherwise pure chroma-key green `#00FF00`.
- Variants may change only expression, eye direction, minor hand position, or a small pose adjustment.
- Variants must not change face identity, hairstyle, outfit, body type, camera distance, or core accessories.
- Do not mix scene background with character sprites. Backgrounds and CGs are separate asset types.

## Reference Hygiene

- Pass only the images that should influence the current output.
- Do not pass a multi-character lineup to a single-character poster.
- Do not pass unrelated style references if the model keeps importing their subjects.
- Treat reference images as content, not pure style.
- For a no-character image, use text-only first when possible.

## First-Person Video

When the protagonist is the camera:

- Do not show protagonist face, body, back view, social avatar, reflection, or shadow identity.
- Avoid protagonist hands unless the project explicitly wants hand interactions.
- Describe the camera as the player's eye line.
- Keep dialogue and reactions from visible characters or off-screen audio.

## Scene Prompt Checklist

Each scene prompt should include:

- Node id and narrative purpose
- On-screen characters
- Location
- First-frame composition
- Action beats by time range for video
- Dialogue in quotes when audio generation should speak it
- Camera movement
- Mood and lighting
- Negative constraints

## Negative Constraints

Project defaults:

- No photorealistic live action
- No real human face
- No celebrity or public figure likeness
- No existing anime/game IP
- No visible protagonist when first-person
- No watermark, logo, subtitles, UI buttons, character name labels, calligraphy panels, stamps, seals, or text overlays inside generated scene art

Use safety wording that avoids over-triggering moderation filters while still stating the intended boundary.
