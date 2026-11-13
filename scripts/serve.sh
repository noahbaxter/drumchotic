#!/bin/bash
# Serve the explorer page locally and open it. The page reloads itself when web/explorer.html
# changes, and rebuilds its data first when web/build_explorer.py, the drumchotic code or features change.
#   scripts/serve.sh            port 8781
#   scripts/serve.sh 9000       another port
set -euo pipefail

cd "$(dirname "$0")/.."
port=${1:-8781}
(sleep 2 && open "http://localhost:$port/") &
exec .venv/bin/python -m web.serve "$port"
