# shellcheck shell=bash
# Shared, deterministic interpreter selection for the repository's shell
# entry points (scripts/verify.sh and scripts/noam.sh). Source this file and
# call `noam_pick_python "$REPO_ROOT"`.
#
# Phase A closure repair (2026-09-02): verify.sh and noam.sh previously used
# two different ad-hoc rules -- verify.sh scanned only `python3`/`python3.12`/
# `python3.11`, and noam.sh hard-coded `python3`. On a machine where `python3`
# resolves to an interpreter without pydantic/PyYAML but `python` resolves to
# one that has them, verify.sh failed and noam.sh crashed. Both now use the
# single rule below.
#
# Selection order (first match wins):
#   1. the declared project environment, $REPO_ROOT/.venv-noam/bin/python,
#      if it exists, is executable, *and* can import the runtime
#      dependencies;
#   2. an explicit override in $NOAM_PYTHON, if it can import the runtime
#      dependencies;
#   3. the first of a fixed, ordered list of named interpreters -- including
#      bare `python` -- that resolves on PATH *and* can import the runtime
#      dependencies (pydantic and yaml).
#
# Every candidate, including the declared environment, is accepted only after
# its `import pydantic, yaml` probe succeeds (Phase A closure repair round 3,
# 2026-09-02: round 2 accepted `.venv-noam/bin/python` unconditionally, so a
# half-built declared environment was selected even when a usable PATH
# interpreter existed). A broken declared environment is now skipped
# deterministically in favour of the override and PATH candidates rather than
# selected; when nothing qualifies the function prints nothing and returns 1,
# and callers must fail loudly rather than continue.

# Ordered candidate list for step 3. `python3` is tried before the
# version-pinned names, and bare `python` last, so the result is
# deterministic when more than one usable interpreter is installed.
NOAM_PYTHON_CANDIDATES=(python3 python3.13 python3.12 python3.11 python3.10 python)

# Probe: can "$1" import the runtime dependencies?
_noam_python_has_deps() {
    "$1" -c 'import pydantic, yaml' >/dev/null 2>&1
}

# Print the selected interpreter path on stdout; return 1 if none qualifies.
noam_pick_python() {
    local repo_root="${1:?noam_pick_python: repo root argument required}"
    local declared="$repo_root/.venv-noam/bin/python"
    local candidate resolved

    if [[ -x "$declared" ]] && _noam_python_has_deps "$declared"; then
        printf '%s\n' "$declared"
        return 0
    fi

    if [[ -n "${NOAM_PYTHON:-}" ]]; then
        resolved="$(command -v "$NOAM_PYTHON" 2>/dev/null)" || resolved=""
        if [[ -n "$resolved" ]] && _noam_python_has_deps "$resolved"; then
            printf '%s\n' "$resolved"
            return 0
        fi
    fi

    for candidate in "${NOAM_PYTHON_CANDIDATES[@]}"; do
        resolved="$(command -v "$candidate" 2>/dev/null)" || continue
        if _noam_python_has_deps "$resolved"; then
            printf '%s\n' "$resolved"
            return 0
        fi
    done

    return 1
}

# Convenience wrapper: print the interpreter or a shared, actionable error
# (and return 1) when none qualifies.
noam_require_python() {
    local repo_root="${1:?noam_require_python: repo root argument required}"
    local python
    if python="$(noam_pick_python "$repo_root")"; then
        printf '%s\n' "$python"
        return 0
    fi
    {
        echo "no Python interpreter with pydantic + PyYAML is available."
        echo "Checked, in order: \$REPO_ROOT/.venv-noam/bin/python, \$NOAM_PYTHON,"
        echo "then: ${NOAM_PYTHON_CANDIDATES[*]}."
        echo "Run 'uv sync' once uv / network access are available, set NOAM_PYTHON"
        echo "to a prepared interpreter, or point .venv-noam at one (see README.md)."
    } >&2
    return 1
}
