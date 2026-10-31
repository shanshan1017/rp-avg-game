#!/usr/bin/env python3
"""Parse story_readable.txt into a structured narratives JSON file.

Splits the readable story by node markers like [node_XX] and extracts
the full literary narrative text for each node, stripping choice menus.
"""

import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def parse_readable(text: str) -> dict:
    node_pattern = re.compile(
        r'[\U0001f4d6\U0001f517\U0001f500\U0001f531\U0001f3c1\U0001f480]'
        r'\s*\[(\w+)\]\s*(.+?)\s*\(第(\d+)幕\)',
        re.UNICODE
    )

    chunks = []
    for m in node_pattern.finditer(text):
        chunks.append({
            "node_id": m.group(1),
            "title": m.group(2).strip(),
            "act": int(m.group(3)),
            "start": m.end(),
        })

    result = {}
    for i, chunk in enumerate(chunks):
        end = chunks[i + 1]["start"] if i + 1 < len(chunks) else len(text)
        # walk backwards from end to find the start of the next node header line
        raw = text[chunk["start"]:end]

        # find next emoji-header and trim
        next_header = re.search(
            r'\n\s*[\U0001f4d6\U0001f517\U0001f500\U0001f531\U0001f3c1\U0001f480]',
            raw, re.UNICODE
        )
        if next_header:
            raw = raw[:next_header.start()]

        raw = raw.strip()

        # remove leading separator lines
        raw = re.sub(r'^-{3,}\s*', '', raw)
        # remove "↳ 选择: ..." prefix line
        raw = re.sub(r'^↳\s*选择:.*?\n', '', raw, flags=re.MULTILINE)
        raw = raw.strip()

        # strip trailing choice menu block
        choice_marker = re.search(r'\n\s*【请选择】', raw)
        narrative_text = raw[:choice_marker.start()].strip() if choice_marker else raw.strip()

        # strip trailing [结局类型: ...] and [死因: ...]
        narrative_text = re.sub(r'\s*\[结局类型:\s*\w+\]\s*$', '', narrative_text)
        narrative_text = re.sub(r'\s*\[死因:\s*.+?\]\s*$', '', narrative_text)

        # strip leading horizontal-rule separators
        narrative_text = re.sub(r'^-{3,}\s*\n?', '', narrative_text)
        narrative_text = narrative_text.strip()

        result[chunk["node_id"]] = {
            "node_id": chunk["node_id"],
            "title": chunk["title"],
            "act": chunk["act"],
            "narrative_text": narrative_text,
        }

    return result


def main():
    readable_path = BASE_DIR / "outputs" / "seed001" / "story_readable.txt"
    output_path = BASE_DIR / "outputs" / "seed001" / "narratives_seed001.json"

    print(f"Reading {readable_path}...")
    text = readable_path.read_text(encoding="utf-8")

    print("Parsing nodes...")
    narratives = parse_readable(text)
    print(f"  Found {len(narratives)} nodes")

    for nid, entry in narratives.items():
        tlen = len(entry["narrative_text"])
        print(f"  {nid}: {entry['title']} ({tlen} chars)")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(narratives, f, ensure_ascii=False, indent=2)

    print(f"\nWritten to {output_path}")


if __name__ == "__main__":
    main()
