# TASK-005 — Interpreter-selection path portability

- Decision class: A — mechanical cross-platform test correction
- Dependency: reviewed Phase A baseline; blocks TASK-003 conditional integration
- Base commit: `bb351131ce1d38a87bd867384bcaf55ca84b1877`
- Branch: `agent/claude/task-005-interpreter-path-portability`
- Worktree: `.worktrees/task-005-interpreter-path-portability`
- Implementer/session: Claude / `noam-claude-task-005`
- Orchestrator/reviewer: Codex
- Owned paths:
  - `tests/noam_core/test_interpreter_selection.py`
  - `.agents/handoffs/TASK-005-interpreter-path-portability.json`
- Forbidden paths:
  - `scripts/lib/pick_python.sh`, `scripts/verify.sh`, and all production code
  - all Maxwell, Standards Scout, A5.1, study, registry, knowledge, adapter,
    architecture, roadmap, policy, dependency, lock and sandbox files
  - external repositories, network/package acquisition, Git remotes/history,
    deployment, and metered APIs

## Objective

Make the existing interpreter-selection behavioural tests compare paths
portably when Windows Python launches Git Bash, without changing the production
selection order or shell output. Close the four failures where Git Bash's
correct MSYS path (`/tmp/...`) is compared directly with the equivalent
Windows path (`C:/Users/.../Temp/...`).

## Invariants and stop conditions

- Test production behaviour as it exists; do not change
  `scripts/lib/pick_python.sh`, `scripts/verify.sh`, or `scripts/noam.sh`.
- Preserve every existing assertion about candidate order, dependency probes,
  declared environments, `NOAM_PYTHON`, and actionable failure output.
- Normalize only for comparison at the Python-test boundary. On Windows with
  Git Bash, compare the shell-selected path with the expected path expressed
  in Bash/MSYS form (for example via a small test helper using `cygpath -u`).
  On POSIX, retain ordinary POSIX path comparison. Do not hard-code a user's
  temporary directory, drive letter, Git installation path, or `/tmp` mapping.
- Fail explicitly if the Windows path-conversion helper itself fails; do not
  weaken equality to basename, suffix, case-insensitive substring, or mere
  existence.
- Do not skip or xfail Windows. Do not loosen the production contract to make
  the test pass.
- Stop if the failure reproduces outside test path representation, if a
  production change is actually required, or if the canonical failures differ
  from the four recorded path-representation mismatches.

## Acceptance criteria

1. All nine tests in `test_interpreter_selection.py` pass under Windows Python
   launching Git Bash, including the four previously failing selected-path
   assertions.
2. The test continues to compare the full exact selected path to the full
   expected path after platform-appropriate representation conversion.
3. Linux/POSIX behaviour remains supported without requiring `cygpath`.
4. No production file or unrelated test is changed.
5. Ruff reports no finding in the owned Python test.
6. The unchanged canonical command passes from a clean process using the
   prepared review interpreter:

   ```bash
   bash scripts/verify.sh --fast
   ```

   At the current combined test count this is expected to make all core tests
   green, including the 39 TASK-003 Maxwell tests once its reviewed repair is
   present during final integration verification.

## Required evidence

- `.agents/handoffs/TASK-005-interpreter-path-portability.json` conforming to
  `.agents/handoffs/TEMPLATE.json`.
- Exact changed-file list and diff against the pinned base.
- Focused interpreter-selection test command and unedited exit summary.
- Ruff command and exit summary.
- Canonical `bash scripts/verify.sh --fast` command, selected interpreter,
  total pass count, and exit code.
- Confirmation that production scripts, Maxwell, Standards Scout, dependencies,
  network settings and unrelated paths were not modified.
- Concise explanation of Windows/MSYS path equivalence and how the test keeps
  exact-path semantics on both Windows and POSIX.
