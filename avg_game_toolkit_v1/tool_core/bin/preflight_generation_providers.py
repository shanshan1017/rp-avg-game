#!/usr/bin/env python3
"""Preflight provider connectivity before paid media generation."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_env_file(path: Path | None) -> list[str]:
    if not path or not path.exists():
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
        try:
            parts = shlex.split(raw_value, comments=False, posix=True)
            value = parts[0] if parts else ""
        except ValueError:
            value = raw_value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
        loaded.append(key)
    return loaded


def normalize_gpt_image_base_url(base_url: str) -> str:
    base = (base_url or "https://api.example.com/v1").rstrip("/")
    for suffix in ("/images/generations", "/images/edits"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def provider_endpoint(provider: str, entries: list[dict[str, Any]]) -> str:
    if provider == "gpt_image":
        base = os.environ.get("GPT_IMAGE_BASE_URL", "")
        if not base:
            for entry in entries:
                if entry.get("provider") == provider:
                    base = ((entry.get("request") or {}).get("url") or "")
                    break
        return urljoin(normalize_gpt_image_base_url(base).rstrip("/") + "/", "images/generations")
    if provider == "volcengine_video":
        url = os.environ.get("ARK_VIDEO_TASK_URL", "")
        if url:
            return url
        base = os.environ.get("ARK_VIDEO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        return base.rstrip("/") + "/contents/generations/tasks"
    return ""


def check_tcp(url: str, timeout: float) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    result: dict[str, Any] = {
        "url": url,
        "host": host,
        "port": port,
        "addresses": [],
        "reachable": False,
        "error": "",
    }
    if not host:
        result["error"] = "missing_host"
        return result
    try:
        result["addresses"] = sorted({item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    except OSError as exc:
        result["error"] = f"dns_error: {exc}"
        return result
    try:
        with socket.create_connection((host, port), timeout=timeout):
            result["reachable"] = True
    except OSError as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def required_providers(manifest: dict[str, Any]) -> list[str]:
    providers = sorted({
        entry.get("provider")
        for entry in manifest.get("entries", [])
        if entry.get("provider") in {"gpt_image", "volcengine_video"}
    })
    return [provider for provider in providers if provider]


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight image/video provider connectivity without printing secrets")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--connect-timeout", type=float, default=5.0)
    args = parser.parse_args()

    loaded_keys = load_env_file(args.env_file)
    manifest = load_json(args.manifest)
    entries = manifest.get("entries") or []
    checks = []
    for provider in required_providers(manifest):
        endpoint = provider_endpoint(provider, entries)
        item = check_tcp(endpoint, args.connect_timeout)
        item["provider"] = provider
        checks.append(item)
    missing_env = []
    if any(item["provider"] == "gpt_image" for item in checks) and not os.environ.get("GPT_IMAGE_API_KEY"):
        missing_env.append("GPT_IMAGE_API_KEY")
    if any(item["provider"] == "volcengine_video" for item in checks) and not os.environ.get("ARK_API_KEY"):
        missing_env.append("ARK_API_KEY")
    failed = [item for item in checks if not item["reachable"]]
    report = {
        "status": "failed" if failed or missing_env else "passed",
        "manifest": str(args.manifest),
        "env_file_loaded": bool(args.env_file and args.env_file.exists()),
        "env_keys_loaded": sorted(key for key in loaded_keys if key in {"GPT_IMAGE_API_KEY", "GPT_IMAGE_BASE_URL", "ARK_API_KEY", "ARK_VIDEO_BASE_URL", "ARK_VIDEO_TASK_URL"}),
        "missing_environment": missing_env,
        "checks": checks,
    }
    if args.report:
        write_json(args.report, report)
    print(json.dumps({"status": report["status"], "checks": len(checks), "failed": len(failed), "missing_environment": missing_env}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
