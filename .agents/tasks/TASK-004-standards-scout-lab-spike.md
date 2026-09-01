# TASK-004 — Standards Scout Lab spike custody

- Decision class: C — new capability, live-local-model integration pattern,
  and citation-provenance boundary; explicitly outside the currently authorised
  Phase A.5 scope and ahead of Phase C
- Class C authority: human authorisation given in chat on 2026-09-01
  ("I authorize step 3 from your 'what's next' answer") and recorded in
  `ROADMAP.md`
- Dependency: none; this independent Lab scope neither depends on nor blocks
  Phase A.5, A5.2, or Phase B
- Base commit: `9bb83c4c2ca3c123138ef1a727d3b843a8470abb`
- Branch: `agent/claude/task-004-standards-scout-lab-spike`
- Worktree: `.worktrees/task-004-standards-scout-lab-spike`
- Implementer/session: Claude / `noam-claude-task-004`
- Orchestrator/reviewer: Codex
- Owned paths:
  - `tools/standards_scout/**`
  - `tests/standards_scout/**`
  - `.agents/handoffs/TASK-004-standards-scout-lab-spike.json`
- Forbidden paths: everything else, explicitly including `src/noam/**`,
  `studies/**`, `domains/**`, `knowledge/**`, `registry/**`, `adapters/**`,
  `experiments/**`, `archive/**`, `security/**`, `tests/noam_core/**`,
  `.claude/**`, `.gitignore`, `pyproject.toml`, `scripts/**`, `.agents/tasks/**`,
  `.agents/review-log.md`, and all top-level governance documents

## Objective

Bring the already-built, twice-reviewed Standards Scout offline skeleton under
proper single-branch/single-worktree custody, so every further change happens
in isolation rather than on `main`. Repair any finding from the fresh review.
Do not run against real Airport documents or a live model: engineer-supplied
restricted data and an unsandboxed host are outside this task.

## Invariants and stop conditions

- Introduce no engineering conclusion, compliance decision, or Noam
  registry/A5.1 integration.
- Add no network access, package installation, live model call, or restricted
  data inside the worktree.
- Keep Scout out of `scripts/verify.sh`; its verification remains a focused
  Lab suite.
- If repair requires a forbidden path, stop and escalate to Codex rather than
  expanding scope.

## Acceptance criteria

1. From a fresh checkout of the task worktree, the following passes in full
   (72 tests at task creation):

   ```text
   python -m unittest discover -s tests/standards_scout -p "test_*.py" -t .
   ```

2. Every finding from review round 3 ships with a focused regression test.
3. No file outside the owned paths is modified by the implementer.
4. The offline-only, privacy, provenance, and human-authority limitations remain
   explicit; passing tests do not constitute an engineering or compliance
   conclusion.

## Required evidence

- `.agents/handoffs/TASK-004-standards-scout-lab-spike.json`, conforming to
  `.agents/handoffs/TEMPLATE.json`, with changed files, exact unittest command
  and output, assumptions, limitations, and unresolved risks.
- Diff and changed-file list against the pinned base, demonstrating that only
  owned paths changed.
- Confirmation that no restricted content was read, generated, or referenced.
- Confirmation that no network, package installation, or live model call was
  attempted.

