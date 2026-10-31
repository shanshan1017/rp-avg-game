#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8062}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME_DIR="$ROOT/playable_games/zhuxian_qimai_huiwu_v1"

if [[ ! -f "$GAME_DIR/runtime/runtime_game_package.json" ]]; then
  echo "Missing runtime package: $GAME_DIR/runtime/runtime_game_package.json" >&2
  exit 1
fi

echo "Serving zhuxian_qimai_huiwu_v1 from:"
echo "  $GAME_DIR"
echo
echo "Open:"
echo "  http://127.0.0.1:$PORT/runtime/"
echo
python -m http.server "$PORT" --bind 127.0.0.1 --directory "$GAME_DIR"
