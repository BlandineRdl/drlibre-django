#!/usr/bin/env bash
# Deterministic quality gates: fast for agent loops, full mirrors pre-commit and the suite.
set -euo pipefail
case "${1:-fast}" in
  fast) uv run ruff check . && uv run ruff format --check . && uv run lint-imports ;;
  full) uv run pre-commit run --all-files && uv run pytest ;;
  *) echo "usage: $0 fast|full" >&2; exit 2 ;;
esac
