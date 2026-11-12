#!/bin/bash
# Run a heavy step on bazzite, where the chart copies and spare CPU live, and pull back its results.
# Sends the code as it is right now, uncommitted edits and new files included, without touching git.
#   scripts/remote.sh features         re-measure charts (fast unless sticking or parsing changed)
#   scripts/remote.sh report           scorecards and outliers
#   scripts/remote.sh audit            per-axis scorecard
#   scripts/remote.sh web              rebuild the explorer data, pulled to data/web/
#   scripts/remote.sh rate ARGS...     scripts/rate.sh there; the report is pulled to data/ratings/
#   scripts/remote.sh test             the unit tests
#   scripts/remote.sh dmt              send data/dmt (tournament charts) over after adding some
#   DRUMCHOTIC_HOST=other scripts/remote.sh ...   another machine set up the same way
set -euo pipefail

HOST=${DRUMCHOTIC_HOST:-bazzite}
DIR=drumchotic
cd "$(dirname "$0")/.."
step=${1:?usage: scripts/remote.sh features|report|audit|web|rate|test|dmt [args]}
shift

# snapshot the working tree into a throwaway commit through a temporary index, so the real index,
# stash and branches stay as they are; .gitignore keeps data and venvs out
index=$(mktemp)
trap 'rm -f "$index"' EXIT
cp "$(git rev-parse --git-path index)" "$index"
GIT_INDEX_FILE=$index git add -A
# never ship data or a venv, even as links (worktrees link them): checking those out would replace the
# remote's real data folder
GIT_INDEX_FILE=$index git rm -r -q --cached --ignore-unmatch data .venv .worktrees
snapshot=$(git commit-tree "$(GIT_INDEX_FILE=$index git write-tree)" -p HEAD -m "remote run")
if git ls-tree -r --name-only "$snapshot" | grep -qE '^(data|\.venv)(/|$)'; then
  echo "refusing to send data or .venv to $HOST" >&2; exit 1
fi
git push -q -f "$HOST" "$snapshot:refs/heads/remote-run"
ssh "$HOST" "cd $DIR && git checkout -q -f --detach remote-run"

remote() { ssh "$HOST" "cd $DIR && $*"; }
pull() { ssh "$HOST" "cd $DIR && tar -cf - $1" | tar -xf - ; }

case $step in
  features)
    remote 'for set in charts:features dmt:features_dmt anchors:features_anchors; do
              .venv/bin/python -m drumchotic.build_features "data/${set%%:*}" "data/cache/${set##*:}.json"; done
            .venv/bin/python -m drumchotic.build_familiarity' ;;
  report) remote ".venv/bin/python -m drumchotic.report $(printf '%q ' "$@")" ;;
  audit) remote ".venv/bin/python -m drumchotic.audit $(printf '%q ' "$@")" ;;
  web) remote ".venv/bin/python -m web.build" && pull "data/web/data.json data/web/index.html" && echo "-> data/web/" ;;
  rate)
    remote "scripts/rate.sh $(printf '%q ' "$@")"
    mkdir -p data/ratings && pull data/ratings ;;
  test) remote ".venv/bin/python -m unittest discover -s tests -q" ;;
  dmt) tar -cf - data/dmt | ssh "$HOST" "cd $DIR && tar -xf - 2>/dev/null"; echo "data/dmt sent" ;;
  *) echo "unknown step: $step" >&2; exit 2 ;;
esac
