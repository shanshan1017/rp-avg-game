# 素材请求与本地保存流程

这份文档说明 `心动失控夜` 的图片、首帧、视频是如何发请求、如何下载到本地、如何记录到 manifest，并给出可复跑命令。所有密钥都只通过环境变量传入，不写入文档、脚本输出或前端文件。

## 目录约定

```text
interactive_video_game/
  pipeline/generate_assets.py
  outputs/heart_rush_night_v0/
    character_prompts.json
    video_prompts.json
    character_assets.json
    first_frame_assets.json
    video_task_payloads.json
    video_tasks.json
    video_results.json
    video_manifest.json
  video_engine/public/assets/
    characters/
    posters/
    videos/
```

本地游戏只读取 `video_engine/public/assets/` 下的文件：

- 角色图：`assets/characters/<character_id>.png`
- 节点首帧/封面：`assets/posters/<node_id>.png`
- 视频尾帧：`assets/posters/<node_id>_last_frame.png`
- 视频文件：`assets/videos/<node_id>.mp4`

## 环境变量

从 `.env.example` 复制到本地 shell 或私有 `.env` 后再运行脚本：

```bash
export GPT_IMAGE_API_KEY="replace_me"
export GPT_IMAGE_BASE_URL="https://api.example.com/v1"
export GPT_IMAGE_MODEL="gpt-image-2-c"

export ARK_API_KEY="replace_me"
export ARK_VIDEO_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
export ARK_VIDEO_MODEL="doubao-seedance-2-0-260128"

export DEFAULT_VIDEO_RESOLUTION="720p"
export DEFAULT_VIDEO_RATIO="16:9"
export DEFAULT_GENERATE_AUDIO="true"
export DEFAULT_WATERMARK="false"
```

## 图片请求

图片接口是 OpenAI 兼容格式：

```http
POST {GPT_IMAGE_BASE_URL}/images/generations
Authorization: Bearer {GPT_IMAGE_API_KEY}
Content-Type: application/json
```

请求体：

```json
{
  "model": "gpt-image-2-c",
  "prompt": "角色或首帧 prompt",
  "n": 1,
  "size": "1536x864"
}
```

脚本入口：

```bash
python3 interactive_video_game/pipeline/generate_assets.py characters --workers 4
python3 interactive_video_game/pipeline/generate_assets.py first-frames --workers 4
```

保存逻辑：

1. 如果响应里有 `data[0].b64_json`，脚本直接 base64 解码写入 PNG。
2. 如果响应里有 `data[0].url`，脚本用 `requests.get(url)` 下载图片二进制，再写入 PNG。
3. 角色图写到 `video_engine/public/assets/characters/`。
4. 首帧图写到 `video_engine/public/assets/posters/`。
5. 生成结果分别记录到 `character_assets.json` 和 `first_frame_assets.json`。

注意：`first_frame_assets.json` 会保留图片服务返回的 `source_url`。视频图生视频时，当前脚本会把这个 `source_url` 作为首帧参考传给火山方舟。如果图片接口只返回 base64、没有公网 URL，则需要先把本地首帧上传到可访问地址，或扩展脚本支持视频接口的 base64 图片输入。

## 视频创建任务

视频生成是异步任务。创建任务接口：

```http
POST {ARK_VIDEO_BASE_URL}/contents/generations/tasks
Authorization: Bearer {ARK_API_KEY}
Content-Type: application/json
```

请求体结构：

```json
{
  "model": "doubao-seedance-2-0-260128",
  "content": [
    {
      "type": "text",
      "text": "视频主 prompt"
    },
    {
      "type": "image_url",
      "image_url": {
        "url": "首帧公网 URL"
      },
      "role": "first_frame"
    }
  ],
  "resolution": "720p",
  "ratio": "16:9",
  "duration": 12,
  "generate_audio": true,
  "watermark": false,
  "return_last_frame": true
}
```

脚本入口：

```bash
python3 interactive_video_game/pipeline/generate_assets.py prepare-videos
python3 interactive_video_game/pipeline/generate_assets.py submit-videos --workers 4
```

执行后会生成：

- `video_task_payloads.json`：每个节点的完整请求体。
- `video_tasks.json`：提交结果和 `task_id`。

`prepare-videos` 会读取：

- `outputs/heart_rush_night_v0/video_prompts.json`
- `outputs/heart_rush_night_v0/first_frame_assets.json`

然后把每个节点的 `main_prompt`、首帧 URL、时长、分辨率、比例等合成请求体。

## 视频轮询与下载

查询接口：

```http
GET {ARK_VIDEO_BASE_URL}/contents/generations/tasks/{task_id}
Authorization: Bearer {ARK_API_KEY}
```

脚本入口：

```bash
python3 interactive_video_game/pipeline/generate_assets.py poll-videos \
  --poll-interval 30 \
  --max-polls 120
```

轮询逻辑：

1. 读取 `video_tasks.json` 里的 `task_id`。
2. 每隔 `poll_interval` 秒查询一次任务状态。
3. 状态为 `queued` 或 `running` 时继续等待。
4. 状态为 `succeeded` 时，从响应 `content.video_url` 或 `content.file_url` 下载视频。
5. 如果响应有 `content.last_frame_url`，同时下载尾帧。
6. 状态为 `failed`、`expired`、`cancelled` 时停止该任务并记录错误。

本地保存：

```text
video_engine/public/assets/videos/<node_id>.mp4
video_engine/public/assets/posters/<node_id>_last_frame.png
```

下载函数使用流式写入，避免一次性把大视频读进内存：

```python
with requests.get(url, stream=True, timeout=600) as resp:
    resp.raise_for_status()
    with output_path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
```

## Manifest 写入

轮询过程中会持续写两个文件：

- `video_results.json`：任务状态、查询响应、本地下载路径。
- `video_manifest.json`：前端运行需要的本地资源索引。

`video_manifest.json` 形状：

```json
{
  "game_id": "heart_rush_night_v0",
  "updated_at": 1770000000,
  "videos": {
    "node_01_office_exit": {
      "src": "assets/videos/node_01_office_exit.mp4",
      "poster": "assets/posters/node_01_office_exit.png",
      "last_frame": "assets/posters/node_01_office_exit_last_frame.png",
      "duration_sec": 12,
      "task_id": "cgt-...",
      "status": "succeeded",
      "downloaded_at": 1770000000
    }
  }
}
```

前端不读取远端临时 URL，只读取 `src`、`poster`、`last_frame` 这些本地相对路径。这样火山方舟返回的签名 URL 过期后，游戏仍然可以运行。

## 生成前端数据

素材下载完成后，运行：

```bash
python3 interactive_video_game/video_engine/build_game_data.py
```

它会合并：

- `data/seeds/heart_rush_story_graph_v0.json`
- `outputs/heart_rush_night_v0/scripts.json`
- `outputs/heart_rush_night_v0/video_manifest.json`

输出：

```text
video_engine/public/game_data.js
```

HTML runtime 通过 `game_data.js` 找到每个节点的视频和封面。

## 一次完整复跑

```bash
# 1. 生成角色图
python3 interactive_video_game/pipeline/generate_assets.py characters --workers 4

# 2. 生成每个视频节点的首帧图
python3 interactive_video_game/pipeline/generate_assets.py first-frames --workers 4

# 3. 准备视频任务请求体
python3 interactive_video_game/pipeline/generate_assets.py prepare-videos

# 4. 提交视频任务
python3 interactive_video_game/pipeline/generate_assets.py submit-videos --workers 4

# 5. 轮询并下载视频与尾帧
python3 interactive_video_game/pipeline/generate_assets.py poll-videos --poll-interval 30 --max-polls 120

# 6. 生成前端数据
python3 interactive_video_game/video_engine/build_game_data.py
```

## 检查命令

检查本地视频和封面是否齐全：

```bash
python3 - <<'PY'
import json, re
from pathlib import Path

root = Path("interactive_video_game/video_engine/public")
text = (root / "game_data.js").read_text(encoding="utf-8")
data = json.loads(re.match(r"window\\.HEART_RUSH_GAME = (.*);\\n?$", text, re.S).group(1))

missing = []
for node in data["nodes"].values():
    for key in ("src", "poster"):
        path = root / node["video"][key]
        if not path.exists():
            missing.append((node["id"], key, str(path)))
print("missing:", missing)
PY
```

检查视频时长：

```bash
find interactive_video_game/video_engine/public/assets/videos -name "*.mp4" -print0 \
  | xargs -0 -I{} sh -c 'printf "%s " "{}"; ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 "{}"'
```

## 常见问题

- 不要把真实 API key 写进 JSON、README、前端或提交记录。
- 火山返回的 `video_url` / `last_frame_url` 是临时签名 URL，只用于立即下载，不作为游戏运行资源。
- 如果部分视频失败，先保留成功节点，再只重提失败节点，避免重复花费。
- 如果首帧图没有公网 URL，图生视频不会带首帧参考，需要先上传本地图或扩展视频请求格式。
- 如果要继续做连续镜头，可以把上一段下载好的 `_last_frame.png` 作为下一段首帧参考重新提交视频任务。
