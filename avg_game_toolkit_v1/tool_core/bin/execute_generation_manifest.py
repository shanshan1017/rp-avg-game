#!/usr/bin/env python3
"""Execute approved media generation manifest entries.

This executor is intentionally narrow:
- it requires an explicit --allow-paid-generation flag;
- it reads secrets only from environment variables;
- it writes generated files only under the selected project root;
- it stores sanitized execution records without API keys or signed URLs.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import shlex
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests


TERMINAL_VIDEO_STATES = {"succeeded", "failed", "expired", "cancelled"}
GENERATION_PHASE_NAMES = {
    10: "character_reference_lock",
    20: "independent_scene_prop_ui_assets",
    30: "character_reference_edits",
    40: "cg_and_video_first_frames",
    50: "video_clips",
    60: "audio_assets",
    90: "other_assets",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_env_file(path: Path, *, override: bool = False) -> list[str]:
    if not path.exists():
        return []
    loaded: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export "):].strip()
        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        if not key or (not override and key in os.environ):
            continue
        try:
            parts = shlex.split(raw_value, comments=False, posix=True)
            value = parts[0] if parts else ""
        except ValueError:
            value = raw_value.strip().strip('"').strip("'")
        os.environ[key] = value
        loaded.append(key)
    return loaded


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def within_project(project_root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(project_root.resolve())
        return True
    except ValueError:
        return False


def output_path(project_root: Path, local_output_path: str) -> Path:
    target = (project_root / local_output_path).resolve()
    if not within_project(project_root, target):
        raise ValueError(f"Refusing to write outside project root: {target}")
    return target


def normalize_gpt_image_base_url(base_url: str) -> str:
    base = (base_url or "https://api.example.com/v1").rstrip("/")
    for suffix in ("/images/generations", "/images/edits"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def provider_key(provider: str) -> str:
    if provider == "gpt_image":
        return "GPT_IMAGE_API_KEY"
    if provider == "volcengine_video":
        return "ARK_API_KEY"
    if provider == "minimax_audio":
        return "MINIMAX_API_KEY"
    return ""


def redact_response(data: Any) -> Any:
    safe = json.loads(json.dumps(data, ensure_ascii=False))
    if isinstance(safe, dict):
        for key in ["url", "video_url", "file_url", "last_frame_url", "source_url", "download_url"]:
            if key in safe:
                safe[key] = "<redacted>"
        for key, value in list(safe.items()):
            safe[key] = redact_response(value)
    elif isinstance(safe, list):
        safe = [redact_response(value) for value in safe]
    return safe


def save_binary_from_url(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=(20, 600)) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def save_image_response(data: dict[str, Any], target: Path) -> dict[str, Any]:
    item = (data.get("data") or [{}])[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    if item.get("b64_json"):
        target.write_bytes(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        save_binary_from_url(item["url"], target)
    else:
        raise RuntimeError("Image response did not contain b64_json or url.")
    saved = {
        "local_path": str(target),
        "bytes": target.stat().st_size,
        "revised_prompt": item.get("revised_prompt", ""),
    }
    if item.get("url"):
        saved["source_url"] = item["url"]
    return saved


def asset_target_from_entry(project_root: Path, entry: dict[str, Any]) -> Path | None:
    local_output_path = entry.get("local_output_path")
    if not local_output_path:
        return None
    return output_path(project_root, local_output_path)


def dependency_path(
    asset_id: str,
    *,
    project_root: Path,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
) -> Path | None:
    result = asset_results.get(asset_id) or {}
    local_path = result.get("local_path")
    if local_path and Path(local_path).exists():
        return Path(local_path)
    entry = entries_by_asset.get(asset_id)
    if entry:
        target = asset_target_from_entry(project_root, entry)
        if target and target.exists() and target.stat().st_size > 100:
            return target
    return None


def dependency_available(
    asset_id: str,
    *,
    project_root: Path,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
    allow_existing_dependencies: bool,
) -> bool:
    result = asset_results.get(asset_id)
    if result:
        return result.get("status") == "succeeded"
    if asset_id in entries_by_asset and not allow_existing_dependencies:
        return False
    return dependency_path(asset_id, project_root=project_root, entries_by_asset=entries_by_asset, asset_results=asset_results) is not None


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def dependency_image_url(
    asset_id: str,
    *,
    project_root: Path,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
) -> str:
    result = asset_results.get(asset_id) or {}
    if result.get("source_url"):
        return result["source_url"]
    path = dependency_path(asset_id, project_root=project_root, entries_by_asset=entries_by_asset, asset_results=asset_results)
    if path:
        return image_data_url(path)
    return ""


def multipart_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def chroma_key_green(path: Path, options: dict[str, Any]) -> dict[str, Any]:
    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        return {"postprocess": "skipped", "reason": f"Pillow unavailable: {exc}"}

    tolerance = int(options.get("tolerance", 72))
    image = Image.open(path).convert("RGBA")
    pixels = image.load()
    removed = 0
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            green_dominance = g - max(r, b)
            if g > 96 and green_dominance > tolerance:
                pixels[x, y] = (r, g, b, 0)
                removed += 1
            elif options.get("spill_desaturate") and g > 90 and green_dominance > max(18, tolerance // 3):
                neutral = int((r + b) / 2)
                pixels[x, y] = (r, min(g, neutral + 18), b, a)
    image.save(path)
    return {
        "postprocess": "chroma_key_green_to_alpha",
        "removed_pixels": removed,
        "mode": "RGBA",
    }


def postprocess_image(entry: dict[str, Any], target: Path) -> dict[str, Any]:
    params = entry.get("model_parameters") or {}
    chroma = params.get("chroma_key") or {}
    if params.get("background_policy") == "chroma_key_green_cutout" or chroma.get("enabled"):
        return chroma_key_green(target, chroma)
    return {}


def execute_image(
    entry: dict[str, Any],
    project_root: Path,
    skip_existing: bool,
    connect_timeout: int,
    read_timeout: int,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    api_key = os.environ.get("GPT_IMAGE_API_KEY", "")
    if not api_key:
        return failed(entry, "missing_environment", "GPT_IMAGE_API_KEY is required.")
    request = entry.get("request") or {}
    payload = dict((request.get("payload") or {}))
    url = request.get("url") or os.environ.get("GPT_IMAGE_BASE_URL", "https://api.example.com/v1/images/generations")
    if os.environ.get("GPT_IMAGE_BASE_URL") and url == request.get("url"):
        action = "edits" if entry.get("capability") in {"image.reference_edit", "image.mask_edit"} else "generations"
        base_url = normalize_gpt_image_base_url(os.environ["GPT_IMAGE_BASE_URL"])
        url = urljoin(base_url.rstrip("/") + "/", f"images/{action}")
    target = output_path(project_root, entry["local_output_path"])
    if skip_existing and target.exists() and target.stat().st_size > 100:
        return succeeded(entry, str(target), {"skipped_existing": True, "bytes": target.stat().st_size})
    headers = {"Authorization": f"Bearer {api_key}"}
    files = []
    handles = []
    try:
        if entry.get("capability") in {"image.reference_edit", "image.mask_edit"}:
            for asset_id in entry.get("input_asset_ids") or []:
                path = dependency_path(asset_id, project_root=project_root, entries_by_asset=entries_by_asset, asset_results=asset_results)
                if not path:
                    return failed(entry, "missing_dependency", f"Missing input image asset: {asset_id}")
                handle = path.open("rb")
                handles.append(handle)
                files.append(("image", (path.name, handle, mimetypes.guess_type(path.name)[0] or "image/png")))
            data = {key: multipart_value(value) for key, value in payload.items() if key not in {"image", "mask"}}
            response = requests.post(url, headers=headers, data=data, files=files, timeout=(connect_timeout, read_timeout))
        else:
            headers["Content-Type"] = "application/json"
            response = requests.post(url, headers=headers, json=payload, timeout=(connect_timeout, read_timeout))
    except requests.RequestException as exc:
        return failed(entry, "request_failed", str(exc))
    finally:
        for handle in handles:
            handle.close()
    if response.status_code >= 400:
        return failed(entry, "provider_error", f"{response.status_code}: {response.text[:1000]}")
    try:
        body = response.json()
        saved = save_image_response(body, target)
        saved.update(postprocess_image(entry, target))
    except Exception as exc:  # noqa: BLE001
        return failed(entry, "save_failed", str(exc))
    return succeeded(entry, str(target), {"response": redact_response(body), **saved})


def prepare_video_payload(
    entry: dict[str, Any],
    *,
    project_root: Path,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    request = entry.get("request") or {}
    payload = dict((request.get("payload") or {}))
    content = list(payload.get("content") or [])
    existing_urls = {
        ((item.get("image_url") or {}).get("url") or "")
        for item in content
        if item.get("type") == "image_url"
    }
    for asset_id in entry.get("input_asset_ids") or []:
        url = dependency_image_url(asset_id, project_root=project_root, entries_by_asset=entries_by_asset, asset_results=asset_results)
        if not url or url in existing_urls:
            continue
        role = "first_frame" if entry.get("capability") == "video.first_frame_to_video" or asset_id.startswith("vff_") else "reference_image"
        content.append({"type": "image_url", "image_url": {"url": url}, "role": role})
        existing_urls.add(url)
    payload["content"] = content
    return payload


def submit_video(entry: dict[str, Any], payload: dict[str, Any], connect_timeout: int, read_timeout: int) -> tuple[dict[str, Any] | None, str]:
    api_key = os.environ.get("ARK_API_KEY", "")
    if not api_key:
        return None, "ARK_API_KEY is required."
    request = entry.get("request") or {}
    url = request.get("url") or os.environ.get("ARK_VIDEO_TASK_URL", "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(connect_timeout, min(read_timeout, 180)))
    except requests.RequestException as exc:
        return None, str(exc)
    if response.status_code >= 400:
        return None, f"{response.status_code}: {response.text[:1000]}"
    return response.json(), ""


def poll_video(task_id: str, poll_interval: int, max_polls: int, connect_timeout: int, read_timeout: int) -> tuple[dict[str, Any] | None, str]:
    api_key = os.environ.get("ARK_API_KEY", "")
    base_url = os.environ.get("ARK_VIDEO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    headers = {"Authorization": f"Bearer {api_key}"}
    url = urljoin(base_url.rstrip("/") + "/", f"contents/generations/tasks/{task_id}")
    last_status = ""
    for _ in range(max_polls):
        try:
            response = requests.get(url, headers=headers, timeout=(connect_timeout, min(read_timeout, 180)))
        except requests.RequestException as exc:
            return None, str(exc)
        if response.status_code >= 400:
            return None, f"{response.status_code}: {response.text[:1000]}"
        body = response.json()
        last_status = str(body.get("status") or "")
        if last_status in TERMINAL_VIDEO_STATES:
            return body, ""
        time.sleep(poll_interval)
    return None, f"video task did not finish after {max_polls} polls; last status={last_status}"


def save_video_response(body: dict[str, Any], target: Path) -> dict[str, Any]:
    content = body.get("content") or {}
    video_url = content.get("video_url") or content.get("file_url")
    if not video_url:
        raise RuntimeError("Video response did not contain a video_url or file_url.")
    save_binary_from_url(video_url, target)
    aux: dict[str, str] = {}
    last_frame = content.get("last_frame_url")
    if last_frame:
        frame_path = target.with_name(target.stem + "_last_frame.png")
        save_binary_from_url(last_frame, frame_path)
        aux["last_frame"] = str(frame_path)
    return {"local_path": str(target), "bytes": target.stat().st_size, "local_aux_paths": aux}


def execute_video(
    entry: dict[str, Any],
    project_root: Path,
    skip_existing: bool,
    poll_interval: int,
    max_polls: int,
    connect_timeout: int,
    read_timeout: int,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    target = output_path(project_root, entry["local_output_path"])
    if skip_existing and target.exists() and target.stat().st_size > 100:
        return succeeded(entry, str(target), {"skipped_existing": True, "bytes": target.stat().st_size})
    payload = prepare_video_payload(entry, project_root=project_root, entries_by_asset=entries_by_asset, asset_results=asset_results)
    submitted, error = submit_video(entry, payload, connect_timeout, read_timeout)
    if error:
        category = "missing_environment" if error == "ARK_API_KEY is required." else "provider_error"
        return failed(entry, category, error)
    assert submitted is not None
    task_id = submitted.get("id") or submitted.get("task_id") or submitted.get("data", {}).get("id")
    if not task_id:
        return failed(entry, "missing_task_id", "Video submit response did not include a task id.", {"submit_response": redact_response(submitted)})
    body, poll_error = poll_video(str(task_id), poll_interval, max_polls, connect_timeout, read_timeout)
    if poll_error:
        return failed(entry, "poll_failed", poll_error, {"task_id": task_id, "submit_response": redact_response(submitted)})
    assert body is not None
    if body.get("status") != "succeeded":
        return failed(entry, "video_failed", f"Video task ended with status={body.get('status')}", {"task_id": task_id, "query_response": redact_response(body)})
    try:
        saved = save_video_response(body, target)
    except Exception as exc:  # noqa: BLE001
        return failed(entry, "save_failed", str(exc), {"task_id": task_id, "query_response": redact_response(body)})
    return succeeded(entry, str(target), {"task_id": task_id, "query_response": redact_response(body), **saved})


def succeeded(entry: dict[str, Any], local_path: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "prompt_id": entry.get("prompt_id"),
        "asset_id": entry.get("asset_id"),
        "capability": entry.get("capability"),
        "provider": entry.get("provider"),
        "status": "succeeded",
        "local_path": local_path,
        "completed_at": now_iso(),
        **(extra or {}),
    }


def failed(entry: dict[str, Any], category: str, message: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "prompt_id": entry.get("prompt_id"),
        "asset_id": entry.get("asset_id"),
        "capability": entry.get("capability"),
        "provider": entry.get("provider"),
        "status": "failed",
        "error_category": category,
        "error": message,
        "completed_at": now_iso(),
        **(extra or {}),
    }


def skip(entry: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "prompt_id": entry.get("prompt_id"),
        "asset_id": entry.get("asset_id"),
        "capability": entry.get("capability"),
        "provider": entry.get("provider"),
        "status": "skipped",
        "reason": reason,
        "completed_at": now_iso(),
    }


def execute_entry(
    entry: dict[str, Any],
    project_root: Path,
    args: argparse.Namespace,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    provider = entry.get("provider")
    capability = entry.get("capability", "")
    if args.only_provider and provider != args.only_provider:
        return skip(entry, f"provider filtered by --only-provider={args.only_provider}")
    if provider == "gpt_image" and capability.startswith("image."):
        return execute_image(entry, project_root, args.skip_existing, args.connect_timeout, args.read_timeout, entries_by_asset, asset_results)
    if provider == "volcengine_video" and capability.startswith("video."):
        return execute_video(entry, project_root, args.skip_existing, args.video_poll_interval, args.video_max_polls, args.connect_timeout, args.read_timeout, entries_by_asset, asset_results)
    return skip(entry, f"unsupported provider/capability: {provider}/{capability}")


def generation_phase_for_entry(entry: dict[str, Any]) -> int:
    try:
        return int(entry.get("generation_phase") or 0)
    except (TypeError, ValueError):
        return 0


def generation_phase_name(entry: dict[str, Any]) -> str:
    phase = generation_phase_for_entry(entry)
    return str(entry.get("generation_phase_name") or GENERATION_PHASE_NAMES.get(phase) or "unclassified")


def execute_dependency_group(
    entries: list[dict[str, Any]],
    project_root: Path,
    args: argparse.Namespace,
    entries_by_asset: dict[str, dict[str, Any]],
    asset_results: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    pending = list(entries)
    allow_existing_dependencies = args.skip_existing or args.allow_existing_dependencies
    while pending:
        ready = [
            entry
            for entry in pending
            if all(
                dependency_available(
                    asset_id,
                    project_root=project_root,
                    entries_by_asset=entries_by_asset,
                    asset_results=asset_results,
                    allow_existing_dependencies=allow_existing_dependencies,
                )
                for asset_id in (entry.get("input_asset_ids") or [])
            )
        ]
        if not ready:
            for entry in pending:
                missing = [
                    asset_id
                    for asset_id in (entry.get("input_asset_ids") or [])
                    if not dependency_available(
                        asset_id,
                        project_root=project_root,
                        entries_by_asset=entries_by_asset,
                        asset_results=asset_results,
                        allow_existing_dependencies=allow_existing_dependencies,
                    )
                ]
                result = failed(entry, "failed_dependency", f"Dependencies unavailable: {', '.join(missing)}")
                results.append(result)
                asset_results[entry.get("asset_id")] = result
                print(f"{result.get('asset_id')}: {result.get('status')} ({result.get('error_category')})", flush=True)
            break
        ready_ids = {id(entry) for entry in ready}
        pending = [entry for entry in pending if id(entry) not in ready_ids]
        print(f"  Starting dependency level: {len(ready)} ready, {len(pending)} pending in this phase", flush=True)
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {}
            for entry in ready:
                print(f"  start {entry.get('asset_id')} [{entry.get('capability')}]", flush=True)
                futures[executor.submit(execute_entry, entry, project_root, args, entries_by_asset, asset_results)] = entry
            for future in as_completed(futures):
                entry = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    result = failed(entry, "executor_exception", str(exc))
                results.append(result)
                asset_results[result.get("asset_id")] = result
                detail = f" ({result.get('error_category')})" if result.get("status") == "failed" else ""
                print(f"{result.get('asset_id')}: {result.get('status')}{detail}", flush=True)
    return results


def execute_entries_with_dependencies(entries: list[dict[str, Any]], project_root: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    entries_by_asset = {entry.get("asset_id"): entry for entry in entries if entry.get("asset_id")}
    asset_results: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    phases: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        phases[generation_phase_for_entry(entry)].append(entry)
    ordered_phases = sorted(phases)
    for index, phase in enumerate(ordered_phases):
        phase_entries = phases[phase]
        phase_name = generation_phase_name(phase_entries[0]) if phase_entries else GENERATION_PHASE_NAMES.get(phase, "")
        print(f"Starting generation phase {phase}: {phase_name} ({len(phase_entries)} assets)", flush=True)
        phase_results = execute_dependency_group(phase_entries, project_root, args, entries_by_asset, asset_results)
        results.extend(phase_results)
        failed_results = [result for result in phase_results if result.get("status") == "failed"]
        if failed_results and args.stop_after_phase_failure:
            remaining_entries = [
                entry
                for later_phase in ordered_phases[index + 1 :]
                for entry in phases[later_phase]
            ]
            for entry in remaining_entries:
                result = failed(
                    entry,
                    "blocked_by_prior_generation_phase",
                    f"Stopped after failures in generation phase {phase}: {phase_name}",
                )
                results.append(result)
                asset_results[entry.get("asset_id")] = result
                print(f"{result.get('asset_id')}: failed (blocked_by_prior_generation_phase)", flush=True)
            break
    return results


def update_runtime_asset_paths(project_root: Path, results: list[dict[str, Any]], runtime_package: Path | None) -> int:
    if not runtime_package or not runtime_package.exists():
        return 0
    package = load_json(runtime_package)
    assets = package.get("assets") or {}
    base = ((package.get("engine_contract") or {}).get("asset_base_path") or "").strip()
    project_assets_root = ((runtime_package.parent / base).resolve() if base else project_root)
    changed = 0
    for item in results:
        if item.get("status") != "succeeded":
            continue
        asset_id = item.get("asset_id")
        local_path = item.get("local_path")
        if asset_id not in assets or not local_path:
            continue
        try:
            relative = str(Path(local_path).resolve().relative_to(project_assets_root))
        except ValueError:
            continue
        if assets[asset_id].get("path") != relative:
            assets[asset_id]["path"] = relative
            assets[asset_id]["source_manifest_id"] = item.get("prompt_id")
            changed += 1
    if changed:
        write_json(runtime_package, package)
        preview_package = project_root / "runtime_preview" / "runtime_game_package.json"
        if preview_package.exists():
            write_json(preview_package, package)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute approved media generation manifest entries")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--allow-paid-generation", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--allow-existing-dependencies", action="store_true", help="Allow dependency assets from existing files even when they were not produced in this run.")
    parser.add_argument("--stop-after-phase-failure", action="store_true", help="Stop later generation phases after any failure in the current phase. Default continues and lets explicit dependencies block only dependent assets.")
    parser.add_argument("--only-provider", default="")
    parser.add_argument("--video-poll-interval", type=int, default=30)
    parser.add_argument("--video-max-polls", type=int, default=120)
    parser.add_argument("--connect-timeout", type=int, default=20)
    parser.add_argument("--read-timeout", type=int, default=900)
    parser.add_argument("--runtime-package", type=Path)
    parser.add_argument("--env-file", type=Path, help="Optional dotenv-style provider key file. Values are not written to reports.")
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    project_root = args.project_root.resolve()
    loaded_env_keys: list[str] = []
    if args.env_file:
        loaded_env_keys = load_env_file(args.env_file)
    policy = manifest.get("execution_policy") or {}
    if not args.allow_paid_generation or not policy.get("paid_generation_allowed"):
        write_json(args.report, {
            "status": "blocked",
            "blocked_reason": "paid generation requires both manifest execution_policy.paid_generation_allowed=true and --allow-paid-generation",
            "checked_at": now_iso(),
        })
        print("Generation blocked: explicit paid generation approval is required.")
        return 2

    entries = list(manifest.get("entries") or [])
    started_at = now_iso()
    results = execute_entries_with_dependencies(entries, project_root, args)

    runtime_updates = update_runtime_asset_paths(project_root, results, args.runtime_package)
    summary = {
        "status": "completed",
        "project_id": manifest.get("project_id"),
        "started_at": started_at,
        "ended_at": now_iso(),
        "entry_count": len(entries),
        "succeeded": sum(1 for r in results if r.get("status") == "succeeded"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "runtime_asset_path_updates": runtime_updates,
        "required_environment": sorted({provider_key(e.get("provider", "")) for e in entries if provider_key(e.get("provider", ""))}),
        "env_file_loaded": bool(args.env_file and args.env_file.exists()),
        "env_file_path": str(args.env_file) if args.env_file else "",
        "env_keys_loaded": sorted(key for key in loaded_env_keys if key in {"GPT_IMAGE_API_KEY", "GPT_IMAGE_BASE_URL", "GPT_IMAGE_MODEL", "ARK_API_KEY", "ARK_VIDEO_BASE_URL", "ARK_VIDEO_TASK_URL", "ARK_VIDEO_MODEL"}),
        "results": sorted((redact_response(result) for result in results), key=lambda r: str(r.get("asset_id") or "")),
    }
    if summary["failed"]:
        summary["status"] = "completed_with_failures"
    write_json(args.report, summary)
    print(json.dumps({k: summary[k] for k in ["status", "entry_count", "succeeded", "failed", "skipped", "runtime_asset_path_updates"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
