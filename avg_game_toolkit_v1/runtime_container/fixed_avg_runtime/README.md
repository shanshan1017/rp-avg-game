# Fixed AVG Runtime

This runtime loads `runtime_game_package.json` without story-specific code.

Use it for P0/P1 text and prompt QA before paid media generation:

```bash
cp /path/to/runtime_game_package.json ./runtime_game_package.json
python -m http.server 8050
```

Then open the folder in a browser. You can also pass a package URL:

```text
index.html?package=runtime_game_package.json
```

Current scope:

- data-driven nodes, segments, choices, conditions, state changes;
- local asset references for backgrounds, portraits, inline images, video, and audio;
- save/continue through `localStorage`;
- worldline review with click-to-jump for QA.

