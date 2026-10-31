#!/usr/bin/env python3
"""Build a playable AVG game HTML from story_graph + narratives + assets.

Reads story_graph.json, narratives JSON, and asset manifest,
merges them into the game template to produce a single playable HTML.
"""

import argparse
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = ENGINE_DIR / "templates" / "game_template.html"

BG_NODE_MAP = None


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def merge_narratives(graph: dict, narratives: dict) -> dict:
    nodes = graph.get("nodes", {})
    if isinstance(nodes, list):
        nodes = {n["node_id"]: n for n in nodes}

    merged = {}
    for nid, node in nodes.items():
        narr_entry = narratives.get(nid, {})
        text = narr_entry.get("narrative_text", "")
        if not text or len(text) < 50:
            text = node.get("scene_description", node.get("title", f"[{nid}]"))
            if node.get("death_cause"):
                text += f"\n\n{node['death_cause']}"
            if node.get("death_description_hint"):
                text += f"\n\n{node['death_description_hint']}"

        merged[nid] = {
            "text": text,
            "title": narr_entry.get("title", node.get("title", "")),
            "act": narr_entry.get("act", node.get("act", 1)),
        }
    return merged


def normalize_nodes(graph: dict) -> dict:
    nodes = graph.get("nodes", {})
    if isinstance(nodes, list):
        graph["nodes"] = {n["node_id"]: n for n in nodes}
    return graph


def resolve_backgrounds(manifest: dict) -> dict:
    raw_bgs = manifest.get("backgrounds", {})
    if BG_NODE_MAP is None:
        return dict(raw_bgs)
    resolved = {}
    for node_id, manifest_key in BG_NODE_MAP.items():
        if manifest_key in raw_bgs:
            resolved[node_id] = raw_bgs[manifest_key]
    return resolved


def build_game_data(graph: dict, narratives_merged: dict, manifest: dict) -> dict:
    return {
        "story": graph,
        "narratives": narratives_merged,
        "assets": {
            "backgrounds": resolve_backgrounds(manifest),
            "characters": manifest.get("characters", {}),
            "videos": manifest.get("videos", {}),
        },
    }


def inject_into_template(template_html: str, game_data: dict) -> str:
    game_data_js = json.dumps(game_data, ensure_ascii=False, indent=None)
    script_tag = f"<script>\nconst GAME_DATA = {game_data_js};\n</script>"
    story = game_data.get("story", {})
    title = story.get("title", "AVG Game")
    subtitle = story.get("subtitle", story.get("time_period", ""))
    result = template_html.replace("<!-- GAME_DATA_PLACEHOLDER -->", script_tag)
    result = result.replace("<!-- TITLE_PLACEHOLDER -->", title)
    result = result.replace("<!-- MAIN_TITLE_PLACEHOLDER -->", title)
    result = result.replace("<!-- SUBTITLE_PLACEHOLDER -->", subtitle)
    return result


def main():
    parser = argparse.ArgumentParser(description="Build AVG game HTML")
    parser.add_argument("--story-graph", type=str,
                        default=str(BASE_DIR / "outputs" / "seed003" / "story_graph.json"))
    parser.add_argument("--narratives", type=str,
                        default=str(BASE_DIR / "outputs" / "seed003" / "narratives.json"))
    parser.add_argument("--manifest", type=str,
                        default=str(ENGINE_DIR / "assets" / "manifest.json"))
    parser.add_argument("--template", type=str, default=str(TEMPLATE_PATH))
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    print("Loading story graph...")
    graph = load_json(args.story_graph)
    graph = normalize_nodes(graph)
    story_id = graph.get("story_id", "unknown")
    print(f"  Story: {graph.get('title', '?')} ({len(graph.get('nodes', {}))} nodes)")

    print("Loading narratives...")
    narr_raw = {}
    if os.path.exists(args.narratives):
        narr_raw = load_json(args.narratives)
        print(f"  Loaded {len(narr_raw)} narrative entries")
    else:
        print(f"  No narratives file at {args.narratives}, using scene_description fallback")

    print("Merging narratives...")
    narratives_merged = merge_narratives(graph, narr_raw)
    coverage = sum(1 for n in narratives_merged.values() if len(n.get("text", "")) > 50)
    print(f"  Coverage: {coverage}/{len(narratives_merged)} nodes have text > 50 chars")

    print("Loading asset manifest...")
    manifest = {}
    if os.path.exists(args.manifest):
        manifest = load_json(args.manifest)
        bg_count = len(manifest.get("backgrounds", {}))
        char_count = len(manifest.get("characters", {}))
        print(f"  Assets: {bg_count} backgrounds, {char_count} characters")
    else:
        print(f"  No manifest found, building without assets")

    print("Resolving background mapping...")
    resolved_bgs = resolve_backgrounds(manifest)
    print(f"  Mapped {len(resolved_bgs)} backgrounds to story nodes")

    print("Building game data...")
    game_data = build_game_data(graph, narratives_merged, manifest)

    print("Loading template...")
    with open(args.template, encoding="utf-8") as f:
        template_html = f.read()

    print("Injecting data into template...")
    final_html = inject_into_template(template_html, game_data)

    output_path = args.output
    if not output_path:
        out_dir = ENGINE_DIR / "output"
        os.makedirs(out_dir, exist_ok=True)
        output_path = str(out_dir / f"game_{story_id}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nGame built successfully!")
    print(f"  Output: {output_path}")
    print(f"  Size: {size_mb:.2f} MB")
    print(f"  Nodes: {len(graph.get('nodes', {}))}")
    print(f"  Narrative coverage: {coverage}/{len(narratives_merged)}")


if __name__ == "__main__":
    main()
