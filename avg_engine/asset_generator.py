#!/usr/bin/env python3
"""Asset generation pipeline for AVG visual novel.

Generates background images and character sprites using gpt-image-2 API,
then saves an asset manifest.
"""

import argparse
import json
import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

API_URL = os.environ.get("IMAGE_API_URL", "https://api.example.com/v1/images/generations")
API_KEY = os.environ["IMAGE_API_KEY"]
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

STYLE_COMMON = (
    "galgame CG, visual novel illustration, "
    "Key/KyoAni anime art style, soft cel-shading, "
    "clean linework, warm pastel color palette, "
    "2D anime, high-quality bishoujo game artwork"
)

STYLE_BG = (
    f"{STYLE_COMMON}, anime scenic background, "
    "visual novel background CG, hand-painted feel, "
    "wide establishing shot, golden hour lighting, "
    "no people, no characters, empty scene, "
    "dreamy atmospheric perspective, soft bokeh"
)

STYLE_CHAR = (
    f"{STYLE_COMMON}, galgame tachie character portrait, "
    "upper body close-up, facing slightly left, "
    "large expressive anime eyes, detailed hair, "
    "soft gradient background, gentle rim lighting, "
    "bishoujo game character art, emotionally expressive"
)

STYLE_NEGATIVE = (
    "No text, no watermark, no UI, no letters, no words, no subtitle, "
    "no photorealism, no 3D render, no realistic lighting, "
    "no western comic style, no chibi, no deformed"
)


def load_story_graph(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def call_image_api(prompt: str, size: str = "3:2", retries: int = 2) -> str | None:
    payload = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "url",
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                urls = [item["url"] for item in data.get("data", [])]
                if urls:
                    return urls[0]
            print(f"  API error (status {resp.status_code}): {resp.text[:200]}")
        except requests.exceptions.Timeout:
            print(f"  Attempt {attempt+1} timed out")
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
        if attempt < retries:
            time.sleep(3)
    return None


def build_bg_prompt(node: dict, graph: dict) -> str:
    scene = node.get("scene_description", node.get("title", ""))
    tone = node.get("emotional_tone", "")
    location = graph.get("location", "")
    period = graph.get("time_period", "")
    summary = scene[:350] if len(scene) > 350 else scene

    parts = [STYLE_BG]
    if period and location:
        parts.append(f"{period}, {location}")
    parts.append(f"Scene: {summary}")
    if tone:
        parts.append(f"Atmosphere: {tone}")
    parts.append(STYLE_NEGATIVE)
    return ". ".join(parts)


def build_char_prompt(char: dict, graph: dict) -> str:
    desc = char.get("description", "")
    period = graph.get("time_period", "")
    location = graph.get("location", "")
    return (
        f"{STYLE_CHAR}. "
        f"{period}, {location}. "
        f"{desc}. "
        f"{STYLE_NEGATIVE}"
    )


def generate_backgrounds(graph: dict, out_dir: Path, max_workers: int = 3) -> dict:
    nodes = graph.get("nodes", {})
    if isinstance(nodes, list):
        nodes = {n["node_id"]: n for n in nodes}

    results = {}
    tasks = []
    for nid, node in nodes.items():
        prompt = build_bg_prompt(node, graph)
        tasks.append((nid, prompt))

    print(f"Generating {len(tasks)} background images (workers={max_workers})...")

    def _gen(item):
        nid, prompt = item
        print(f"  [gen] {nid}...")
        url = call_image_api(prompt, size="3:2")
        if url:
            results[nid] = url
            print(f"  [ok]  {nid} -> {url}")
        else:
            print(f"  [FAIL] {nid}")
        return nid, url

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_gen, t) for t in tasks]
        for f in as_completed(futures):
            f.result()

    return results


def generate_characters(graph: dict, out_dir: Path) -> dict:
    characters = graph.get("characters", [])
    results = {}
    for char in characters:
        cid = char.get("char_id", "")
        if not cid:
            continue
        print(f"  [gen] character {cid} ({char.get('name','')})...")
        prompt = build_char_prompt(char, graph)
        url = call_image_api(prompt, size="2:3")
        if url:
            results[cid] = {"name": char.get("name", ""), "url": url}
            print(f"  [ok]  {cid} -> {url}")
        else:
            print(f"  [FAIL] {cid}")
        time.sleep(1)
    return results


def save_manifest(bg_urls: dict, char_urls: dict, video_urls: dict, out_dir: Path):
    manifest = {
        "backgrounds": bg_urls,
        "characters": char_urls,
        "videos": video_urls,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    path = out_dir / "manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Manifest saved to {path}")
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate assets for AVG game")
    parser.add_argument("--story-graph", type=str,
                        default=str(BASE_DIR / "outputs" / "seed003" / "story_graph.json"))
    parser.add_argument("--output-dir", type=str, default=str(ASSETS_DIR))
    parser.add_argument("--stage", type=str, default="all",
                        choices=["all", "images", "characters"],
                        help="Which stage to run")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    os.makedirs(out_dir / "backgrounds", exist_ok=True)
    os.makedirs(out_dir / "characters", exist_ok=True)

    graph = load_story_graph(args.story_graph)
    print(f"Loaded story: {graph.get('title', 'unknown')} ({len(graph.get('nodes', {}))} nodes)")

    bg_urls = {}
    char_urls = {}
    video_urls = {}

    existing_manifest = out_dir / "manifest.json"
    if existing_manifest.exists():
        with open(existing_manifest, encoding="utf-8") as f:
            existing = json.load(f)
        bg_urls = existing.get("backgrounds", {})
        char_urls = existing.get("characters", {})
        video_urls = existing.get("videos", {})

    if args.stage in ("all", "images"):
        print("\n=== Stage: Background Images ===")
        bg_urls.update(generate_backgrounds(graph, out_dir, max_workers=args.workers))

    if args.stage in ("all", "characters"):
        print("\n=== Stage: Character Sprites ===")
        char_urls.update(generate_characters(graph, out_dir))

    save_manifest(bg_urls, char_urls, video_urls, out_dir)

    total = len(bg_urls) + len(char_urls) + len(video_urls)
    print(f"\nDone. Total assets: {total} (bg={len(bg_urls)}, char={len(char_urls)}, video={len(video_urls)})")


if __name__ == "__main__":
    main()
