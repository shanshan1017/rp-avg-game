#!/usr/bin/env python3
"""Generate image assets and submit video tasks for the interactive video game.

Secrets are read from environment variables only. This script never writes API
keys to output files.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "heart_rush_night_v0"
DEFAULT_PUBLIC = ROOT / "video_engine" / "public" / "assets"
PUBLIC_ROOT = ROOT / "video_engine" / "public"

IMAGE_SIZE_FALLBACKS = {
    "character": ["1024x1536", "1024x1024", "1536x1024", "1792x1024"],
    "first_frame": ["1536x864", "1792x1024", "1536x1024", "1024x576", "1024x1024"],
}

GLOBAL_NEGATIVE = (
    "photorealistic, live action, real human face, celebrity likeness, public figure likeness, "
    "existing anime or game IP, "
    "male protagonist visible, male hands close-up, mirror reflection of protagonist, shadow identity, "
    "watermark, logo, text, UI buttons, subtitles"
)

NEGATIVE_DROP_TERMS = [
    "露骨成人内容",
    "成人露骨",
    "低俗凝视",
    "恐怖血腥",
    "强迫亲密",
    "未成年人",
    "childlike sexualization",
    "explicit adult content",
    "nude",
]


def sanitize_negative(text: str) -> str:
    """Keep renderer constraints while removing terms that can trip prompt filters."""
    cleaned = text or GLOBAL_NEGATIVE
    for term in NEGATIVE_DROP_TERMS:
        cleaned = cleaned.replace(term, "")
    return "，".join(part.strip(" ，,") for part in cleaned.replace(",", "，").split("，") if part.strip(" ，,"))


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def infer_game_id(output_dir: Path) -> str:
    name = output_dir.name
    return name if name else "interactive_video_game"


def public_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PUBLIC_ROOT.resolve()))
    except ValueError:
        return str(path)


def image_endpoint(base_url: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", "images/generations")


def image_payload(model: str, prompt: str, size: str) -> dict:
    return {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
    }


def save_image_response(data: dict, output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    item = (data.get("data") or [{}])[0]
    source_url = item.get("url")
    revised_prompt = item.get("revised_prompt", "")

    if item.get("b64_json"):
        output_path.write_bytes(base64.b64decode(item["b64_json"]))
    elif source_url:
        resp = requests.get(source_url, timeout=120)
        resp.raise_for_status()
        output_path.write_bytes(resp.content)
    else:
        raise RuntimeError(f"Image response did not contain b64_json or url: {data}")

    return {
        "local_path": str(output_path),
        "source_url": source_url or "",
        "revised_prompt": revised_prompt,
    }


def generate_one_image(
    *,
    kind: str,
    asset_id: str,
    prompt: str,
    output_path: Path,
    preferred_size: str,
    api_key: str,
    base_url: str,
    model: str,
) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    sizes = [preferred_size] + [s for s in IMAGE_SIZE_FALLBACKS[kind] if s != preferred_size]
    last_error = ""
    for size in sizes:
        try:
            resp = requests.post(
                image_endpoint(base_url),
                headers=headers,
                json=image_payload(model, prompt, size),
                timeout=600,
            )
            if resp.status_code >= 400:
                last_error = f"{resp.status_code}: {resp.text[:500]}"
                continue
            saved = save_image_response(resp.json(), output_path)
            return {
                "id": asset_id,
                "kind": kind,
                "status": "succeeded",
                "size": size,
                "prompt": prompt,
                **saved,
            }
        except Exception as exc:
            last_error = str(exc)
    return {
        "id": asset_id,
        "kind": kind,
        "status": "failed",
        "prompt": prompt,
        "error": last_error,
    }


def character_jobs(output_dir: Path, public_dir: Path) -> list[dict]:
    prompts = load_json(output_dir / "character_prompts.json")
    negative = prompts.get("negative_prompt") or GLOBAL_NEGATIVE
    jobs = []
    for item in prompts["characters"]:
        prompt = f"{item['prompt']}\n\nNegative prompt: {negative}"
        asset_id = item["character_id"]
        jobs.append({
            "kind": "character",
            "id": asset_id,
            "prompt": prompt,
            "size": item.get("size", "1024x1536"),
            "output_path": public_dir / "characters" / f"{asset_id}.png",
        })
    return jobs


def first_frame_jobs(output_dir: Path, public_dir: Path) -> list[dict]:
    video_prompts_path = output_dir / "video_prompts.json"
    if not video_prompts_path.exists():
        raise FileNotFoundError(f"Missing {video_prompts_path}; run script writing first")
    data = load_json(video_prompts_path)
    jobs = []
    for item in data["video_prompts"]:
        node_id = item["node_id"]
        prompt = "\n".join([
            item.get("style_prompt", ""),
            item.get("first_frame", ""),
            character_anchor_text(item),
            "First-person player POV composition. The male protagonist is not visible.",
            "No UI, no subtitles, no text overlays. Original non-photorealistic anime cinematic illustration.",
            f"Negative prompt: {sanitize_negative(item.get('negative_prompt') or GLOBAL_NEGATIVE)}",
        ])
        jobs.append({
            "kind": "first_frame",
            "id": node_id,
            "prompt": prompt,
            "size": "1536x864",
            "output_path": public_dir / "posters" / f"{node_id}.png",
        })
    return jobs


def character_anchor_text(item: dict[str, Any]) -> str:
    anchors = []
    for character in item.get("character_consistency", []):
        character_id = character.get("character_id", "")
        must_include = "、".join(character.get("must_include", []))
        must_avoid = "、".join(character.get("must_avoid", []))
        if character_id or must_include or must_avoid:
            anchors.append(
                f"Character consistency for {character_id}: must include {must_include}; must avoid {must_avoid}."
            )
    return "\n".join(anchors)


def run_image_batch(kind: str, output_dir: Path, public_dir: Path, workers: int) -> list[dict]:
    api_key = os.environ.get("GPT_IMAGE_API_KEY")
    base_url = os.environ.get("GPT_IMAGE_BASE_URL", "https://api.example.com/v1")
    model = os.environ.get("GPT_IMAGE_MODEL", "gpt-image-2-c")
    if not api_key:
        raise RuntimeError("GPT_IMAGE_API_KEY is required")

    jobs = character_jobs(output_dir, public_dir) if kind == "character" else first_frame_jobs(output_dir, public_dir)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                generate_one_image,
                kind=job["kind"],
                asset_id=job["id"],
                prompt=job["prompt"],
                output_path=job["output_path"],
                preferred_size=job["size"],
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
            for job in jobs
        ]
        for future in as_completed(futures):
            result = future.result()
            print(f"{result['kind']} {result['id']}: {result['status']}")
            results.append(result)

    manifest_path = output_dir / ("character_assets.json" if kind == "character" else "first_frame_assets.json")
    write_json(manifest_path, {
        "generated_at": int(time.time()),
        "kind": kind,
        "results": sorted(results, key=lambda r: r["id"]),
    })
    return results


def ark_video_payload(item: dict, first_frame_asset: dict | None) -> dict:
    model = os.environ.get("ARK_VIDEO_MODEL", "doubao-seedance-2-0-260128")
    content = [{"type": "text", "text": item["main_prompt"]}]
    if first_frame_asset and first_frame_asset.get("source_url"):
        content.append({
            "type": "image_url",
            "image_url": {"url": first_frame_asset["source_url"]},
            "role": "first_frame",
        })
    return {
        "model": model,
        "content": content,
        "resolution": os.environ.get("DEFAULT_VIDEO_RESOLUTION", "720p"),
        "ratio": os.environ.get("DEFAULT_VIDEO_RATIO", "16:9"),
        "duration": int(item.get("duration_sec") or os.environ.get("DEFAULT_VIDEO_DURATION", "12")),
        "generate_audio": os.environ.get("DEFAULT_GENERATE_AUDIO", "true").lower() == "true",
        "watermark": os.environ.get("DEFAULT_WATERMARK", "false").lower() == "true",
        "return_last_frame": True,
    }


def prepare_video_tasks(output_dir: Path) -> dict:
    video_prompts = load_json(output_dir / "video_prompts.json")["video_prompts"]
    first_frames_path = output_dir / "first_frame_assets.json"
    first_frames = {}
    if first_frames_path.exists():
        for item in load_json(first_frames_path).get("results", []):
            first_frames[item["id"]] = item

    tasks = []
    for item in video_prompts:
        node_id = item["node_id"]
        first_frame = first_frames.get(node_id)
        payload = ark_video_payload(item, first_frame)
        tasks.append({
            "node_id": node_id,
            "status": "pending",
            "has_public_first_frame_url": bool(first_frame and first_frame.get("source_url")),
            "payload": payload,
        })
    write_json(output_dir / "video_task_payloads.json", {
        "generated_at": int(time.time()),
        "tasks": tasks,
    })
    return {"tasks": tasks}


def submit_video_tasks(output_dir: Path, workers: int) -> dict:
    api_key = os.environ.get("ARK_API_KEY")
    base_url = os.environ.get("ARK_VIDEO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    if not api_key:
        raise RuntimeError("ARK_API_KEY is required")
    payloads = prepare_video_tasks(output_dir)["tasks"]
    endpoint = urljoin(base_url.rstrip("/") + "/", "contents/generations/tasks")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def submit(task: dict) -> dict:
        resp = requests.post(endpoint, headers=headers, json=task["payload"], timeout=120)
        if resp.status_code >= 400:
            return {**task, "status": "failed_to_submit", "error": resp.text[:1000]}
        body = resp.json()
        return {**task, "status": "submitted", "response": body, "task_id": body.get("id", "")}

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(submit, task) for task in payloads]
        for future in as_completed(futures):
            result = future.result()
            print(f"video {result['node_id']}: {result['status']}")
            results.append(result)

    write_json(output_dir / "video_tasks.json", {
        "submitted_at": int(time.time()),
        "tasks": sorted(results, key=lambda r: r["node_id"]),
    })
    return {"tasks": results}


def download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        with output_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def redact_remote_media_urls(body: dict[str, Any]) -> dict[str, Any]:
    """Keep task metadata while omitting expiring provider download URLs."""
    safe = json.loads(json.dumps(body))
    content = safe.get("content")
    if isinstance(content, dict):
        for key in ("video_url", "last_frame_url", "file_url"):
            if key in content:
                content[key] = ""
    return safe


def poll_video_tasks(output_dir: Path, public_dir: Path, poll_interval: int, max_polls: int) -> dict:
    api_key = os.environ.get("ARK_API_KEY")
    base_url = os.environ.get("ARK_VIDEO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    if not api_key:
        raise RuntimeError("ARK_API_KEY is required")

    video_tasks_path = output_dir / "video_tasks.json"
    data = load_json(video_tasks_path)
    tasks = data.get("tasks", [])
    headers = {"Authorization": f"Bearer {api_key}"}
    videos_dir = public_dir / "videos"
    terminal = {"succeeded", "failed", "expired", "cancelled"}
    task_state = {task["node_id"]: dict(task) for task in tasks}

    for poll_idx in range(1, max_polls + 1):
        active = 0
        print(f"poll {poll_idx}/{max_polls}")
        for node_id, task in sorted(task_state.items()):
            if task.get("status") in terminal and task.get("local_video"):
                continue
            task_id = task.get("task_id")
            if not task_id:
                task["status"] = "missing_task_id"
                continue
            endpoint = urljoin(base_url.rstrip("/") + "/", f"contents/generations/tasks/{task_id}")
            resp = requests.get(endpoint, headers=headers, timeout=120)
            if resp.status_code >= 400:
                task["status"] = "query_failed"
                task["error"] = resp.text[:1000]
                continue
            body = resp.json()
            status = body.get("status", "")
            task["status"] = status
            print(f"  {node_id}: {status}")
            if status == "succeeded":
                content = body.get("content") or {}
                video_url = content.get("video_url") or content.get("file_url")
                if video_url and not task.get("local_video"):
                    local_video = videos_dir / f"{node_id}.mp4"
                    download_file(video_url, local_video)
                    task["local_video"] = str(local_video)
                    task["downloaded_video_at"] = int(time.time())
                last_frame_url = content.get("last_frame_url")
                if last_frame_url and not task.get("local_last_frame"):
                    local_last_frame = public_dir / "posters" / f"{node_id}_last_frame.png"
                    download_file(last_frame_url, local_last_frame)
                    task["local_last_frame"] = str(local_last_frame)
                    task["downloaded_last_frame_at"] = int(time.time())
            elif status not in terminal:
                active += 1
            task["query_response"] = redact_remote_media_urls(body)

        write_json(output_dir / "video_results.json", {
            "updated_at": int(time.time()),
            "tasks": [task_state[k] for k in sorted(task_state)],
        })
        write_video_manifest(output_dir, public_dir, task_state)
        if active == 0:
            break
        time.sleep(poll_interval)

    return {"tasks": list(task_state.values())}


def write_video_manifest(output_dir: Path, public_dir: Path, task_state: dict[str, dict]) -> None:
    videos = {}
    for node_id, task in sorted(task_state.items()):
        local_video = task.get("local_video", "")
        local_poster = public_dir / "posters" / f"{node_id}.png"
        local_last_frame = task.get("local_last_frame", "")
        src = ""
        poster = ""
        last_frame = ""
        if local_video:
            src = public_relative(Path(local_video))
        if local_poster.exists():
            poster = public_relative(local_poster)
        if local_last_frame:
            last_frame = public_relative(Path(local_last_frame))
        videos[node_id] = {
            "src": src,
            "poster": poster,
            "last_frame": last_frame,
            "duration_sec": task.get("payload", {}).get("duration"),
            "task_id": task.get("task_id", ""),
            "status": task.get("status", ""),
            "downloaded_at": task.get("downloaded_video_at", ""),
        }
    write_json(output_dir / "video_manifest.json", {
        "game_id": infer_game_id(output_dir),
        "updated_at": int(time.time()),
        "videos": videos,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate image assets and video tasks")
    parser.add_argument("command", choices=[
        "characters",
        "first-frames",
        "prepare-videos",
        "submit-videos",
        "poll-videos",
    ])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--public-dir", type=Path, default=DEFAULT_PUBLIC)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--poll-interval", type=int, default=30)
    parser.add_argument("--max-polls", type=int, default=120)
    args = parser.parse_args()

    if args.command == "characters":
        run_image_batch("character", args.output_dir, args.public_dir, args.workers)
    elif args.command == "first-frames":
        run_image_batch("first_frame", args.output_dir, args.public_dir, args.workers)
    elif args.command == "prepare-videos":
        prepare_video_tasks(args.output_dir)
    elif args.command == "submit-videos":
        submit_video_tasks(args.output_dir, args.workers)
    elif args.command == "poll-videos":
        poll_video_tasks(args.output_dir, args.public_dir, args.poll_interval, args.max_polls)


if __name__ == "__main__":
    main()
