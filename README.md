# RP_AVG_game — Generate a playable branching AVG from a single story seed

English | [简体中文](README.zh-CN.md)

> Feed in a story seed, get back a web-based AVG (visual novel) with branches, stats and multiple endings.

This project splits interactive-fiction production into a "screenplay-style" multi-agent pipeline. A **Director** plans the full Story Graph first; **Writers** write each node's prose in parallel with only local context; an **Auditor** runs rule-based checks on structure and coherence. The result is compiled into a single-file HTML game, or packaged for a generic runtime player. No model is called at play time — the output is a static web page that works offline and can be deployed anywhere.

```
Seed ─► Director ─► story_graph.json ─► Writers (parallel) ─► narratives.json
                                                                  │
     single-file HTML / runtime game package ◄─ build_game ◄─ Auditor ─► audit_report.json
                                 ▲
             asset_generator (backgrounds / character sprites / video / audio)
```

## Quick start

All you need is Python 3.10+. No dependencies to install and no API key required.

```bash
git clone https://github.com/shanshan1017/rp-avg-game && cd rp-avg-game
python3 -m http.server 8000
```

| Demo | URL | Notes |
|---|---|---|
| Victorian locked-room mystery | http://localhost:8000/demos/game_victorian_mystery_001.html | Single-file HTML: backgrounds + character sprites + branches |
| Sakura parallel worlds | http://localhost:8000/demos/game_sakura_parallel_003.html | Single-file HTML |
| Zhu Xian: Seven Peaks Tournament | `bash avg_game_toolkit_v1/start_zhuxian_preview.sh` → http://127.0.0.1:8062/runtime/ | Toolkit runtime: 41 nodes, 24 choices, 5 endings, with video and audio |
| Story tree visualization | http://localhost:8000/outputs/story_tree_viz.html | Branch structure of the three sample seeds |

The demo stories themselves are written in Chinese.

## Core mechanics

- **Story Graph** (`pipeline/story_graph_schema.py`) defines 6 node types: `narrative`, `choice`, `branch_point`, `merge_point`, `dead_end`, `ending`. There are three kinds of branches:
  - `pearl_string`: options lead to different passages that then rejoin the main line
  - `strong`: options lead to different routes
  - `value_based`: the route is decided by accumulated stats
- **State system**: a primary stat, multi-dimensional stats, flags and variables together drive choice gating (`all / any / not / >= …`), ending resolution and "consequence echoes".
- **Auditor** (`pipeline/auditor.py`) checks graph integrity, item tracking, character presence, naming consistency, dead-end causality and timeline, plus structural quality: pseudo-choices, funnel convergence, unused stat systems and endings without conditions.
- **Runtime** (`avg_game_toolkit_v1/runtime_container/fixed_avg_runtime/`) is a re-skinnable generic web player. It reads `runtime_game_package.json` and uses localStorage for save slots and ending collection.

## Generate your own game

```bash
# Offline mode: validates the whole pipeline with built-in samples, no API needed
python3 pipeline/pipeline.py --mode offline --output-dir /tmp/offline
python3 avg_engine/build_game.py --story-graph /tmp/offline/story_graph.json \
    --narratives /tmp/offline/narratives.json --output /tmp/offline/game.html

# LLM mode: bring your own OpenAI-compatible endpoint
cp .env.example .env   # fill in your own keys; .env is git-ignored
pip install -r requirements.txt
python3 pipeline/pipeline.py --mode llm --seed-file data/seed_001.jsonl --output-dir outputs/my_story
```

For image, video and audio generation and the toolkit's multi-agent workflow, see **[MANUAL.md](MANUAL.md)** and [`avg_game_toolkit_v1/README.md`](avg_game_toolkit_v1/README.md).

## Repository layout

| Path | Contents |
|---|---|
| `pipeline/` | Director / Writers / Auditor and the Story Graph schema |
| `avg_engine/` | Compiler: story graph + narratives → single-file HTML (`build_game.py`, `asset_generator.py`, `templates/`) |
| `avg_game_toolkit_v1/` | Three-layer game production toolkit: `tool_core/` (multi-agent generation) → `runtime_container/` (generic runtime) → `playable_games/` (packaged games) |
| `demos/` | Playable demos and their local assets |
| `outputs/seed00{1,2,3}/` | Sample outputs: story graph, prose, world bible, audit report, visualizations |
| `data/` | Story seeds (`gen_seeds.py` generated 100 seeds across genres) |
| `qa/` | QA tests that run offline |
| `docs/` | System design and QA plan |

## Development and conventions

```bash
pip install -r requirements-dev.txt && pre-commit install
ruff check . && python3 qa/test_pipeline.py
```

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for directory conventions, naming, secret handling, asset size limits and commit rules. Every PR runs lint, the offline pipeline, QA, runtime package validation and a gitleaks secret scan in CI.

## Notes

- The repository contains no secrets; all external services are configured through environment variables (see `.env.example`). Values such as `<PROJECT_ROOT>` and `api.example.com` in the docs are placeholders.
- The Zhu Xian demo is a non-commercial fan work based on the original novel's setting; all rights to the original work belong to its author.
