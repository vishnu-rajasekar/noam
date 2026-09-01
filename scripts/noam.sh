#!/usr/bin/env bash
# Fallback CLI launcher for use before `uv`/`uv sync` are available (see
# README.md and the migration report). Once `uv sync` has run, prefer
# `uv run noam ...`, which uses the project's declared entry point instead.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Same interpreter-selection rule as scripts/verify.sh (Phase A closure
# repair, 2026-09-02): both entry points must agree on which interpreter is
# usable, and both must fail loudly -- never fall through to a `python3` that
# lacks pydantic/PyYAML.
# shellcheck source=scripts/lib/pick_python.sh
source "$REPO_ROOT/scripts/lib/pick_python.sh"

if ! PYTHON="$(noam_require_python "$REPO_ROOT")"; then
    echo "noam.sh: cannot launch the CLI (see message above)." >&2
    exit 1
fi

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m noam.cli.main "$@"
