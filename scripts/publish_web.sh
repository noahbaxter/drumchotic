#!/bin/bash
# Build the explorer page and publish it to GitHub Pages (gh-pages branch, one commit, replaced each time).
set -euo pipefail

cd "$(dirname "$0")/.."
.venv/bin/python -m web.build >/dev/null
pages=.worktrees/gh-pages
if [ ! -d "$pages" ]; then
  if git ls-remote --exit-code --heads origin gh-pages >/dev/null; then
    git fetch -q origin gh-pages:gh-pages
    git worktree add -q "$pages" gh-pages
  else
    git worktree add -q --orphan -b gh-pages "$pages"
  fi
fi
cp data/web/index.html "$pages/index.html"
touch "$pages/.nojekyll"
cd "$pages"
git add index.html .nojekyll
if git rev-parse -q --verify HEAD >/dev/null; then
  git commit -q --amend -m "explorer page"
else
  git commit -q -m "explorer page"
fi
git push -q --force origin gh-pages
echo "https://noahbaxter.dev/drumchotic/"
