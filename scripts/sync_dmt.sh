#!/bin/bash
# Pull chart files (notes.mid/.chart + song.ini, no audio) for the DMT tournament setlists from the NAS.
set -euo pipefail

REMOTE_HOST=nasmox
REMOTE_DIR="/terramox/Games/Standalone/Rhythm/Clone Hero/Charts/Sync Charts/Drummer's Monthly Drive/Tournaments"
DEST="$(cd "$(dirname "$0")/.." && pwd)/data/dmt"

mkdir -p "$DEST"
ssh "$REMOTE_HOST" "cd $(printf '%q' "$REMOTE_DIR") && find . \( -name notes.mid -o -name notes.chart -o -name song.ini \) -print0 | tar --null -T - -cf -" \
    | tar -xf - -C "$DEST"
echo "$(find "$DEST" -name song.ini | wc -l | tr -d ' ') songs in $DEST"
