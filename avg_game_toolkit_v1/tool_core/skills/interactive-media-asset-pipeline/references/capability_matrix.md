# Capability Matrix

This matrix describes model-native capabilities only. Project conveniences such as A/B style tests, contact sheets, linting, and local QA reports are intentionally outside v1.

## Image: GPT Image 2-C

Use the project OpenAI-compatible image configuration through environment variables:

- `GPT_IMAGE_API_KEY`
- `GPT_IMAGE_BASE_URL`
- `GPT_IMAGE_MODEL`, default project value: `gpt-image-2-c`

Never store the key in repo files.

### `image.text_to_image`

Use for new concept art, style exploration, locations, props, and first-pass character designs when no visual reference exists.

Inputs:

- Text prompt
- Size
- Quality
- Output format

Outputs:

- Base64 image data or remote image URL depending provider response
- Optional revised prompt

Best for:

- First character drafts
- Environment concepts
- Abstract UI mood art

Risks:

- Recurring character consistency can drift.
- Fine text rendering and exact layout are unreliable.

### `image.reference_edit`

Use the image edit endpoint with one or more input images. The result may be a modified image or a new image composed from references.

Inputs:

- One or more reference images
- Text prompt
- Size / quality / output format when supported

Best for:

- Character-consistent posters
- Costume variants from an approved character reference
- Scene first frames that must preserve a specific character or object

Rules:

- For scene images, pass only the character references that should appear in that scene.
- Treat every reference image as both style and content. Style references can leak subjects into the output.
- For no-character scenes, prefer text-only or carefully constrained environment/style references.

### `image.mask_edit`

Use an input image plus a same-size alpha mask to edit only part of an image.

Inputs:

- Base image
- Alpha-channel mask
- Text prompt

Best for:

- Fixing hands, props, signage-like artifacts, clothing details, or background problems without rerolling the whole image
- Removing an accidental extra character

Limits:

- Masking is prompt-guided, not pixel-perfect.
- The image and mask must match size and format requirements.

### `image.responses_multiturn`

Use the Responses API image generation tool for iterative creative sessions where the conversation context matters.

Best for:

- Human-in-the-loop art direction
- Iterative edits where previous outputs should remain in context

Batch rule:

- Do not use it as the default batch generator unless the project specifically needs conversational image evolution. Batch jobs should prefer Image API generate/edit because manifests are simpler.

### `image.streaming`

Use streaming partial images only for interactive previews.

Batch rule:

- Disable partial images for production batch runs unless the user explicitly wants preview artifacts. Partial images can add cost and clutter.

## Video: Ark Seedance

Use the project Ark configuration through environment variables:

- `ARK_API_KEY`
- `ARK_VIDEO_BASE_URL`, default project value: `https://ark.cn-beijing.volces.com/api/v3`
- `ARK_VIDEO_MODEL`, current Seedance 2.0 model id used by the project

Endpoint shape:

- Create task: `POST /contents/generations/tasks`
- Query task: task id polling until `queued`, `running`, `succeeded`, `failed`, or `expired`

### `video.text_to_video`

Use text only.

Best for:

- Generic motion drafts
- Non-character establishing shots

Risk:

- Character and style consistency are weaker than image-referenced generation.

### `video.first_frame_to_video`

Use text plus one approved first-frame image.

Best for:

- Most node videos in an interactive video game
- Keeping composition and character design close to the poster

Rules:

- The first frame should already be game-ready.
- Match `ratio` to the first-frame aspect ratio, or use `adaptive`.

### `video.reference_image_to_video`

Use text plus one or more reference images.

Best for:

- Character-consistent movement
- Prop or location continuity

Rules:

- Pass only references that belong in the shot.
- Avoid real human face references unless the provider policy explicitly allows the source.

### `video.reference_video_to_video`

Use text plus a reference video.

Best for:

- Extending a motion style
- Keeping camera language from a previous generated clip

Rules:

- Seedance 2.0 can use trusted generated videos from the same account for face-containing continuity where supported by platform policy.

### `video.reference_audio`

Use text plus image/video reference and audio reference.

Best for:

- Music-driven sequences
- Reusing a background music or rhythm reference

Rules:

- Audio cannot stand alone; include at least one image or video reference.
- Generated audio is mono when enabled.

### `video.last_frame_chain`

Set `return_last_frame=true` to obtain a PNG tail frame and use it as the next clip's first-frame reference.

Best for:

- Continuous routes
- Match cuts
- Multi-clip scenes that need visual continuity

Rules:

- Tail frames are production references unless the runtime explicitly displays them.

### Core Parameters

- `resolution`: `480p`, `720p`, `1080p` where supported
- `ratio`: `16:9`, `4:3`, `1:1`, `3:4`, `9:16`, `21:9`, `adaptive`
- `duration`: Seedance 2.0 supports integer seconds in the documented range, usually `4-15`, or `-1` for model-selected duration
- `generate_audio`: true or false
- `watermark`: false for production unless the user requests otherwise
- `seed`: integer or `-1`
- `execution_expires_after`: task timeout in seconds
- `callback_url`: optional status callback
- `safety_identifier`: stable non-private end-user identifier

## Audio: MiniMax

Use the project MiniMax audio configuration through environment variables:

- `MINIMAX_API_KEY`
- `MINIMAX_BASE_URL`, default project value: `https://api.minimaxi.com`

Backup base URL:

- `https://api-bj.minimaxi.com`

Never store the key in repo files or game-facing manifests.

Read `minimax_audio_capability.md` before building request payloads or audio manifests.

### `audio.tts`

Endpoint:

- `POST /v1/t2a_v2`

Use for:

- character voice lines outside generated videos
- narrator lines
- optional key-scene spoken dialogue

Default model:

- `speech-2.8-hd`

Rules:

- Prefer `output_format: "hex"` and save bytes locally.
- Use pronunciation dictionaries for names and special terms.
- Use speech event tags such as `(laughs)` or `(sighs)` only with supported models.
- Do not require voice for essential comprehension without text/UI fallback.

### `audio.voice_design`

Endpoint:

- `POST /v1/voice_design`

Use for:

- original synthetic character voice design
- reusable `voice_id` creation
- previewing voice direction

Rules:

- `preview_text` maximum length is 500 characters.
- Preview is billed.
- This is not automatic permission to clone real people.
- Keep private consent/source records out of runtime packages.

### `audio.music_generation`

Endpoint:

- `POST /v1/music_generation`

Use for:

- BGM
- menu music
- route themes
- ending songs

Models:

- `music-2.6`
- `music-cover`
- `music-2.6-free`
- `music-cover-free`

Rules:

- Prefer instrumental BGM with `is_instrumental: true`.
- Only use cover/reference audio when the project has rights.
- If response returns a temporary URL, download immediately and store a local asset.

### Video Audio Boundary

For Seedance video clips with `generate_audio=true`, audio is embedded in the generated video. Do not create separate runtime audio for sounds that only belong inside the clip. Instead, write the audio intent into the video prompt: ambience, BGM mood, dialogue/voice, SFX, silence timing, and emotional tone.

## Capability Decision Table

| Need | Preferred capability |
| --- | --- |
| Brand-new character concept | `image.text_to_image` |
| Same character in a new scene | `image.reference_edit` |
| Poster with one approved character | `image.reference_edit` with that character only |
| Poster with no character | `image.text_to_image` |
| Fix part of an approved poster | `image.mask_edit` |
| Node video from poster | `video.first_frame_to_video` |
| Node video needing character/prop refs | `video.reference_image_to_video` |
| Continuous next clip | `video.last_frame_chain` |
| Music or voice-like timing | `video.reference_audio` |
| Pure motion test | `video.text_to_video` |
| Character spoken line outside video | `audio.tts` |
| Original synthetic character voice | `audio.voice_design` then `audio.tts` |
| Runtime BGM / menu music / ending music | `audio.music_generation` |
| Licensed reference-based cover | `music-cover` |
| Video scene with dialogue or ambience | video prompt audio intent + `generate_audio=true` |
