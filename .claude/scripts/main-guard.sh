#!/usr/bin/env bash
# Main branch edit guard.
# Invoked as a PreToolUse hook on Edit and Write tools.
# Blocks file edits when the current branch is 'master'.
set -euo pipefail

branch=$(git branch --show-current 2>/dev/null || echo "")

if [ "$branch" != "master" ]; then
  exit 0
fi

echo "=== MASTER BRANCH EDIT GUARD ==="
echo ""
echo "You are on the 'master' branch."
echo "Direct file edits on 'master' are not permitted - see RELEASING.md."
echo ""
echo "Switch to an appropriate branch before editing:"
echo "  feature branch:  git checkout -b DEV/<your_name>/<description>"
echo "  bug fix branch:  git checkout -b BUG/<your_name>/<description>"
echo "  release branch:  git checkout REL/vX.X.X"
echo ""
echo "BLOCKED - switch branches before editing."
exit 1
