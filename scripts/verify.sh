#!/usr/bin/env bash
# Canonical verification entry point (IMPLEMENTER_REVIEWER_PROTOCOL.md).
#
# --fast runs the src/noam study/registry core test suite (tests/noam_core).
# This superseded Task 0's EnergyPlus spike as the canonical --fast check
# during the 2026-09-01 study-driven restructuring; see ROADMAP.md and
# archive/experiments/task0_energy/STATUS.md. --archive-task0 reproduces the
# old (rejected, non-blocking) Task 0 check for historical reference only.
# --integration/--release extend as later phases land; an unimplemented mode
# fails loudly rather than silently passing.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="${1:-fast}"
MODE="${MODE#--}"

# Interpreter selection is shared with scripts/noam.sh so both entry points
# behave identically (Phase A closure repair, 2026-09-02). See the library
# header for the exact order: declared .venv-noam, then $NOAM_PYTHON, then a
# fixed list of named interpreters including bare `python`, each accepted
# only after a pydantic/PyYAML import probe.
# shellcheck source=scripts/lib/pick_python.sh
source "$REPO_ROOT/scripts/lib/pick_python.sh"

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

case "$MODE" in
    fast)
        if ! PYTHON="$(noam_require_python "$REPO_ROOT")"; then
            echo "verify.sh: cannot run the --fast suite (see message above)." >&2
            exit 1
        fi
        echo "== src/noam core test suite (using $PYTHON) =="
        if "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
            "$PYTHON" -m pytest tests/noam_core -v
        else
            "$PYTHON" -m unittest discover -s tests/noam_core -p "test_*.py" -v
        fi
        ;;
    archive-task0)
        # Historical only -- see archive/experiments/task0_energy/STATUS.md.
        # This never passed independent review and is not a release gate.
        export HOME="$REPO_ROOT/.ladybug_home"
        mkdir -p "$HOME/ladybug_tools"
        PYTHON="$REPO_ROOT/.venv/bin/python"
        if [[ ! -x "$PYTHON" ]]; then
            echo "verify.sh: expected the isolated Ladybug worker venv at $PYTHON" >&2
            exit 1
        fi
        echo "== archived Task 0 spike test suite (rejected; historical only) =="
        "$PYTHON" -m pytest archive/experiments/task0_energy/tests -v
        ;;
    integration)
        # A5.1 recorded-fixture proposal-intake gate (ROADMAP.md Phase A.5).
        # Same interpreter rule and same pytest/unittest fallback as --fast.
        if ! PYTHON="$(noam_require_python "$REPO_ROOT")"; then
            echo "verify.sh: cannot run the --integration suite (see message above)." >&2
            exit 1
        fi
        echo "== A5.1 recorded-fixture proposal-intake suite (using $PYTHON) =="
        if "$PYTHON" -c "import pytest" >/dev/null 2>&1; then
            "$PYTHON" -m pytest tests/a5_1 -v
        else
            "$PYTHON" -m unittest discover -s tests/a5_1 -p "test_*.py" -v
        fi
        ;;
    release)
        echo "verify.sh: --release is not yet implemented (see ROADMAP.md Phase B" >&2
        echo "onward for what introduces --release scope)." >&2
        exit 2
        ;;
    *)
        echo "verify.sh: unknown mode '--$MODE' (expected --fast, --integration," >&2
        echo "--release, or --archive-task0)" >&2
        exit 2
        ;;
esac
