#!/bin/bash
# Pull chart files (notes.mid/.chart + song.ini, no audio) for the DMT tournament setlists from the NAS.
# Files come from the NAS's plocate index (rebuilt nightly), so anything added today shows up tomorrow.
# Only adds: tournaments extracted by hand into data/dmt (Drummer's Monthly 1 to 3, Icebreaker 2022) stay.
set -euo pipefail

REMOTE_HOST=nasmox
REMOTE_DIR="/terramox/Games/Standalone/Rhythm/Clone Hero/Charts/Sync Charts/Drummer's Monthly Drive/Tournaments"
DEST="$(cd "$(dirname "$0")/.." && pwd)/data/dmt"

FILES="^$REMOTE_DIR/.*/\(notes\.mid\|notes\.chart\|song\.ini\)$"
mkdir -p "$DEST"
ssh "$REMOTE_HOST" "cd $(printf '%q' "$REMOTE_DIR") && plocate -0 -r $(printf '%q' "$FILES") \
    | sed -z $(printf '%q' "s|^$REMOTE_DIR/|./|") | tar --null -T - -cf -" \
    | tar -xf - -C "$DEST"
echo "$(find "$DEST" -name song.ini | wc -l | tr -d ' ') songs in $DEST"
