# TASK-000 — Feasibility and deterministic reference case

- Decision class: B
- Dependency: none
- Base commit: unavailable (unborn `main`; documented bootstrap exception)
- Branch: `main` bootstrap only
- Worktree: repository primary worktree
- Implementer/session: Claude / `noam-cai`
- Orchestrator/reviewer: Codex
- Owned paths: `spike/task0_energy/**`, Task 0 tests and fixtures, and the Task 0
  handoff record
- Orchestrator-owned paths: governance documents, acquisition manifests,
  `.claude/settings.json`, `.gitignore`, and Git state
- Forbidden: paid APIs, network access, installers, EnergyPlus 26.1 execution,
  compliance claims, sandbox weakening, Git mutations

## Objective and acceptance

Implement Task 0 exactly as specified in `TASKS.md`, using the accepted
publisher-hash-matched EnergyPlus 25.1 runtime only inside the project sandbox.
Record the engine profile, executable digest, translation path, inputs, units,
raw logs, outputs, diagnostics, and limitations. The invalid native signature
and exploratory-only status must remain visible.

Claude must provide `.agents/handoffs/TASK-000.json` and its actual verification
commands/results. Codex then reviews every initial repository file, reruns the
canonical checks and reference case independently, and records the verdict
before creating the first local baseline commit. Nothing is pushed.
