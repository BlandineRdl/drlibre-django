#!/usr/bin/env bash
# Score the files the commit holds (the git index), never untracked folders such as nested worktrees.
set -euo pipefail
tree="$(mktemp -d)"
trap 'rm -rf "$tree"' EXIT
git checkout-index --all --prefix="$tree/"
uv run python-doctor "$tree" "$@"
