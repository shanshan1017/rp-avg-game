# MiniMax Audio Capability Reference

This reference summarizes the configured MiniMax audio provider for standalone runtime audio. Do not store API keys in repo files or game-facing manifests.

## Provider Config

Use environment variables:

```bash
export MINIMAX_API_KEY="..."
export MINIMAX_BASE_URL="https://api.minimaxi.com"
```

Backup base URL:

```text
https://api-bj.minimaxi.com
```

Auth header:

```text
Authorization: Bearer $MINIMAX_API_KEY
Content-Type: application/json
```

## Capability Summary

### `audio.tts`

Endpoint:

```text
POST /v1/t2a_v2
```

Use for:

- character voice lines;
- narrator lines;
- short UI/system voice prompts;
- optional key-scene spoken dialogue outside generated video clips.

Models:

```text
speech-2.8-hd
speech-2.8-turbo
speech-2.6-hd
speech-2.6-turbo
speech-02-hd
speech-02-turbo
speech-01-hd
speech-01-turbo
```

Recommended default:

```text
speech-2.8-hd
```

Core request:

```json
{
  "model": "speech-2.8-hd",
  "text": "今天是不是很开心呀(laughs)，当然了！",
  "stream": false,
  "voice_setting": {
    "voice_id": "male-qn-qingse",
    "speed": 1,
    "vol": 1,
    "pitch": 0,
    "emotion": "happy"
  },
  "audio_setting": {
    "sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 1
  },
  "subtitle_enable": false,
  "output_format": "hex"
}
```

Important parameters:

- `text`: required, under 10000 characters; for text over 3000 characters, prefer streaming.
- `stream`: false by default; streaming returns hex chunks.
- `voice_setting.voice_id`: selected voice.
- `voice_setting.speed`: usually 1.
- `voice_setting.vol`: usually 1.
- `voice_setting.pitch`: usually 0.
- `voice_setting.emotion`: e.g. `happy`; use only when supported by chosen voice/model.
- `audio_setting.sample_rate`: common values include 32000 or 44100.
- `audio_setting.bitrate`: e.g. 128000.
- `audio_setting.format`: `mp3`, `wav`, or `flac` depending endpoint support.
- `audio_setting.channel`: 1 for mono.
- `pronunciation_dict`: use for difficult names, multilingual terms, or fixed readings.
- `language_boost`: optional language/dialect hint, including `auto`.
- `subtitle_enable`: optional subtitle timing service.
- `subtitle_type`: `sentence`, `word`, or `word_streaming`.
- `output_format`: `hex` or `url`; prefer `hex` for local save and durable manifests.
- `aigc_watermark`: false by default.

Text controls:

- Pause marker: `<#x#>` where x is seconds, range `[0.01, 99.99]`.
- Inline pronunciation override: Mandarin pinyin, IPA, or Cantonese Jyutping in parentheses.
- Speech event tags for speech-2.8 models include `(laughs)`, `(chuckle)`, `(coughs)`, `(breath)`, `(sighs)`, `(gasps)`, `(sniffs)`, `(emm)`, etc.

Response:

```json
{
  "data": {
    "audio": "<hex encoded audio>",
    "status": 2
  },
  "extra_info": {
    "audio_length": 9900,
    "audio_sample_rate": 32000,
    "audio_size": 160323,
    "bitrate": 128000,
    "usage_characters": 26,
    "audio_format": "mp3",
    "audio_channel": 1
  },
  "trace_id": "...",
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

Save hex audio locally:

```python
from pathlib import Path

audio_hex = result["data"]["audio"]
Path("voice_line.mp3").write_bytes(bytes.fromhex(audio_hex))
```

### `audio.voice_design`

Endpoint:

```text
POST /v1/voice_design
```

Use for:

- designing original synthetic character voices from text descriptions;
- creating a reusable `voice_id` for TTS;
- previewing a proposed character voice.

Request:

```json
{
  "prompt": "讲述悬疑故事的播音员，声音低沉富有磁性，语速时快时慢，营造紧张神秘的氛围。",
  "preview_text": "夜深了，古屋里只有他一人。窗外传来若有若无的脚步声。",
  "aigc_watermark": false
}
```

Optional:

- `voice_id`: provide one to control the custom id; omit to auto-generate.

Response:

```json
{
  "voice_id": "generated_voice_id",
  "trial_audio": "<hex encoded preview audio>",
  "base_resp": {
    "status_code": 0,
    "status_msg": "success"
  }
}
```

Rules:

- `preview_text` maximum length is 500 characters.
- Preview synthesis is billed.
- Treat designed voices as original synthetic voices unless the provider/API explicitly supports consented voice cloning.
- Store `voice_id` in authoring manifests and runtime package only if it is needed for reproducibility; do not store private source samples.

### `audio.music_generation`

Endpoint:

```text
POST /v1/music_generation
```

Use for:

- standalone BGM loops;
- ending music;
- menu music;
- route theme sketches;
- instrumental ambience-like music.

Models:

```text
music-2.6
music-cover
music-2.6-free
music-cover-free
```

Recommended:

- `music-2.6` for paid production if available.
- `music-2.6-free` only for drafts or low-RPM testing.
- Prefer `is_instrumental: true` for game BGM unless lyrics are explicitly required.

Instrumental request:

```json
{
  "model": "music-2.6",
  "prompt": "日系校园恋爱AVG，黄昏，温柔但带一点遗憾，钢琴和轻弦乐，适合对话场景循环",
  "stream": false,
  "output_format": "hex",
  "is_instrumental": true,
  "audio_setting": {
    "sample_rate": 44100,
    "bitrate": 256000,
    "format": "mp3"
  },
  "aigc_watermark": false
}
```

Song request:

```json
{
  "model": "music-2.6",
  "prompt": "独立民谣，忧郁，内省，渴望，咖啡馆",
  "lyrics": "[Verse]\\n街灯微亮晚风轻抚\\n影子拉长独自漫步\\n[Chorus]\\n推开木门香气弥漫",
  "audio_setting": {
    "sample_rate": 44100,
    "bitrate": 256000,
    "format": "mp3"
  }
}
```

Cover models:

- `music-cover`
- `music-cover-free`

Reference inputs:

- `audio_url`, or
- `audio_base64`, or
- `cover_feature_id`

Rules:

- Only use reference audio that the project has rights to use.
- Do not use copyrighted songs or vocals as cover references unless explicitly licensed.
- `cover_feature_id` is valid for 24 hours.
- If output returns `url`, download it immediately and store a local file; do not place expiring URLs in runtime manifests.

## Runtime Policy

Standalone audio belongs in `runtime_game_package.assets` as local assets:

```json
{
  "asset_id": "bgm_evening_promise",
  "type": "audio",
  "path": "audio/bgm_evening_promise.mp3",
  "usage": ["audio_bgm"],
  "required": false,
  "duration_sec": 72.4
}
```

Game-facing packages must contain local paths, not API responses, API keys, signed URLs, or provider trace data.

## Video Audio Boundary

Seedance videos can generate embedded audio when `generate_audio=true`. For those scenes:

- write ambience/BGM/dialogue/SFX intent into the video prompt;
- do not create separate runtime audio unless the game needs a transition, loop, replay control, or non-video continuation;
- keep text/UI fallback for any information conveyed by sound.

## Voice And Voice Cloning Boundary

The documented MiniMax APIs here support TTS and text-described voice design. They do not, by themselves, establish legal permission for cloning a real person.

Voice cloning or reference-voice workflows require:

- explicit consent from the voice owner;
- legally obtained source samples;
- no celebrity/public-figure/known performer likeness without approval;
- clear usage scope;
- output review;
- no private source samples in runtime packages.

If those conditions are not met, use:

- no voice;
- a preset voice id;
- `audio.voice_design` for an original synthetic character voice;
- recorded/licensed actor voice.

## Capability Decision Table

| Need | Preferred capability |
| --- | --- |
| Character spoken line outside video | `audio.tts` |
| Narrator line | `audio.tts` |
| Original character voice concept | `audio.voice_design` then `audio.tts` |
| Menu or route BGM | `audio.music_generation` with `is_instrumental: true` |
| Ending song with lyrics | `audio.music_generation` with lyrics |
| Draft BGM under lower quota | `music-2.6-free` |
| Reference-based cover | `music-cover` only with licensed reference audio |
| Video scene dialogue / ambience | Put audio intent in video prompt; use video `generate_audio=true` |
| UI click / small SFX | Manual import or future short-SFX provider unless MiniMax music/TTS is intentionally suitable |

