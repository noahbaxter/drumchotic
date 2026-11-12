#!/bin/bash
# Score our local chart copies with fretwork (cloned at ../fretwork) for comparison.
# Only ever points at drumchotic/data copies, never the NAS or original chart folders,
# and never lets fretwork write difficulties into song.ini.
set -euo pipefail

cd "$(dirname "$0")/.."
DATA="$PWD/data"
FW="$(cd ../fretwork && pwd)"
OUT="$DATA/references/fretwork_local"

marker=$(mktemp)
for set in charts dmt anchors; do
    [[ -d "$DATA/$set" ]] || continue
    (cd "$FW" && .venv/bin/python build.py --search-path "$DATA/$set" --header "drumchotic_$set" \
        && .venv/bin/python analyze.py --header "drumchotic_$set" --diff-mode None --xlsx-levels X) 2>&1 \
        | tr '\r' '\n' | grep -E "Spreadsheet written|Errors +[1-9]|Traceback" || true
done

changed=$(find "$DATA/charts" "$DATA/dmt" "$DATA/anchors" -newer "$marker" -type f 2>/dev/null | wc -l | tr -d ' ')
rm -f "$marker"
if [[ "$changed" != 0 ]]; then
    echo "fretwork modified $changed files in our chart data, stopping" >&2
    exit 1
fi

mkdir -p "$OUT"
rm -f "$OUT"/drumchotic_*_metrics.xlsx
for set in charts dmt anchors; do
    latest=$(ls -t "$FW/metrics/drumchotic_${set}_metrics_"*.xlsx 2>/dev/null | head -1)
    [[ -n "$latest" ]] && cp "$latest" "$OUT/drumchotic_${set}_metrics.xlsx"
done
echo "fretwork scores -> $OUT"
