#!/bin/bash
# Build the explorer page (filterable plots and table of every chart) and open it.
set -euo pipefail

cd "$(dirname "$0")/.."
out=$(.venv/bin/python -m web.build_explorer)
echo "$out"
open "$out"
