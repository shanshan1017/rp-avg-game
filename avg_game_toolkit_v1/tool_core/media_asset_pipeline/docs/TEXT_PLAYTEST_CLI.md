# Text Playtest CLI

The text playtest is a MUD-like dry run for projects whose images and videos do
not exist yet. It turns a cross-disciplinary plan into a playable text route so
Planner and Checker can test whether the game logic is understandable and
reachable before spending generation budget.

## What It Shows

Each cell can display:

- title, mode, location, and visible characters;
- player context and scene purpose;
- facts the player must understand before choosing;
- visual evidence that art/video must eventually show;
- text evidence and UI surfaces that must exist in runtime;
- approved asset slots;
- enabled and disabled choices with lock hints;
- current state flags.

## What It Does Not Prove

It does not prove final art quality, video continuity, lip sync, UI beauty, or
mobile layout. It proves the content-system loop can run.

## Pack Shape

The game case owns the pack file. The reusable tool owns the runner.

```text
games/<project_id>/<run_id>/playtest/text_playtest_pack.json
tool_versions/cross_disciplinary_coherence_v1/bin/play_text_game.py
```

The pack is intentionally runtime-facing and media-light:

```json
{
  "project_id": "example",
  "title": "Example",
  "entry_cell_id": "cell_00",
  "initial_state": {},
  "cells": [
    {
      "cell_id": "cell_00",
      "title": "Opening",
      "mode": "text_image",
      "next_cell_id": "cell_01",
      "player_must_understand": [],
      "visual_evidence": [],
      "text_evidence": [],
      "ui_surfaces": [],
      "asset_slots": [],
      "choices": []
    }
  ]
}
```

## Run Modes

Interactive:

```bash
python tool_versions/cross_disciplinary_coherence_v1/bin/play_text_game.py \
  games/<project>/<run>/playtest/text_playtest_pack.json
```

Scripted path:

```bash
python tool_versions/cross_disciplinary_coherence_v1/bin/play_text_game.py \
  games/<project>/<run>/playtest/text_playtest_pack.json \
  --path c03_lin,c07_protect_lin,c11_promise,c13_answer_equal
```

Useful commands during interactive play:

- `look`: reprint the current cell.
- `state`: show current state.
- `log`: show visited cells and selected choices.
- `assets`: show asset slots for the current cell.
- `choose <number-or-choice-id>`: select a choice.
- `quit`: stop.

## Gate Use

Planner should run at least:

- one true-route path;
- each heroine ending path;
- each designed failure path;
- one intentionally invalid gated choice, to confirm the CLI exposes a fair
  lock hint.

Checker should not approve generation until the text playtest can traverse all
approved endings/failures or the Planner has explicitly accepted the gap.
