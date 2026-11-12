#!/bin/bash
# Refresh feature caches if anything they depend on changed, then fit once,
# print the report and render the plots.
#   scripts/run.sh                  everything
#   scripts/run.sh tiers hardest    only those plots
set -euo pipefail

cd "$(dirname "$0")/.."
PY=.venv/bin/python

for set in charts:features dmt:features_dmt anchors:features_anchors; do
    if [[ -d "data/${set%%:*}" ]]; then
        $PY -m drumchotic.build_features "data/${set%%:*}" "data/cache/${set##*:}.json"
    fi
done

$PY -m drumchotic "$@"
