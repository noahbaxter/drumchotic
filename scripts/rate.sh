#!/bin/bash
# Rate charts and write a report to data/ratings/ (plain text, previews in Discord).
#   scripts/rate.sh ~/path/to/charts/folder
#   scripts/rate.sh --help                      every option
set -euo pipefail

# folder and --out paths are relative to where this was run from
export RATE_CWD="$PWD"
cd "$(dirname "$0")/.."
exec .venv/bin/python -m drumchotic.rate "$@"
