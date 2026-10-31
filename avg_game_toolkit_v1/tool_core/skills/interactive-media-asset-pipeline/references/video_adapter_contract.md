# Video Adapter Contract

This is the planned interface for Ark Seedance submit/poll/download support. V1 of the project-local skill documents this contract but does not implement it.

## Environment

Read secrets and provider settings from environment variables:

- `ARK_API_KEY`
- `ARK_VIDEO_BASE_URL`
- `ARK_VIDEO_MODEL`

Never accept API keys in project JSON, prompts, schema examples, or frontend config.

## Adapter Responsibilities

The adapter should:

1. Build a provider request from one `node_video` asset plan item.
2. Submit the video task.
3. Store task id and sanitized request metadata.
4. Poll until terminal status.
5. Download `video_url` to a local `.mp4` when succeeded.
6. Download `last_frame_url` to a local `.png` when returned.
7. Redact remote signed URLs before writing game-facing manifests.
8. Preserve enough debug metadata in `outputs/<project_id>/` to rerun failed tasks.

## Suggested Python Interface

```python
class VideoAdapter:
    def submit(self, job: VideoJob) -> VideoTaskRecord:
        ...

    def poll(self, task_id: str) -> VideoTaskRecord:
        ...

    def wait(self, task_id: str, poll_interval_sec: int = 30) -> VideoTaskRecord:
        ...

    def download(self, task: VideoTaskRecord, output_paths: VideoOutputPaths) -> GeneratedAssetRecord:
        ...
```

## `VideoJob`

Minimum fields:

- `asset_id`
- `node_id`
- `prompt`
- `model`
- `duration`
- `ratio`
- `resolution`
- `generate_audio`
- `return_last_frame`
- `watermark`
- `seed`
- `reference_images`
- `reference_videos`
- `reference_audio`
- `safety_identifier`

## Content Construction

Always include one text item:

```json
{
  "type": "text",
  "text": "<video prompt>"
}
```

Reference images:

```json
{
  "type": "image_url",
  "image_url": {
    "url": "<local uploaded or provider-accessible image url>"
  },
  "role": "reference_image"
}
```

Reference videos:

```json
{
  "type": "video_url",
  "video_url": {
    "url": "<provider-accessible video url>"
  },
  "role": "reference_video"
}
```

Reference audio:

```json
{
  "type": "audio_url",
  "audio_url": {
    "url": "<provider-accessible audio url>"
  },
  "role": "reference_audio"
}
```

## Request Parameters

Recommended defaults for interactive video nodes:

- `ratio`: `16:9` for current HTML game, or `adaptive` when the first frame should control it
- `resolution`: `720p` for iteration, higher only after approval
- `duration`: node script target duration, within provider range
- `generate_audio`: true only when the node prompt includes dialogue or sound intent
- `return_last_frame`: true when continuity matters
- `watermark`: false for production

## Manifest Redaction

Provider task records may temporarily include `video_url`, `last_frame_url`, or `file_url`. These URLs can expire and may include signatures.

Game-facing manifests must store:

- `task_id`
- `status`
- `local_path`
- `local_aux_paths.last_frame` when available
- `prompt`
- `parameters`
- `error` when failed

Game-facing manifests must not store:

- API keys
- Authorization headers
- Signed platform URLs
- Full request headers

## Terminal Status Handling

- `succeeded`: download assets and write local paths.
- `failed`: write provider error, keep sanitized request metadata.
- `expired`: mark as expired and allow rerun.
- `queued` / `running`: do not write as production-ready.

## Retry Rules

Retry only failed or expired jobs. Do not rerun approved videos unless the asset plan explicitly marks them for replacement.
