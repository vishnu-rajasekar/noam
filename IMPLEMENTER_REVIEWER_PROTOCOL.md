# Claude Implementer / Codex Reviewer Protocol

This protocol operationalises the roles in `AGENTS.md`.

## Task hand-off

Codex writes a bounded task, scoped against the current study
(`ROADMAP.md`, `studies/<ID>_<slug>/`), containing:

- the user-visible outcome and files in scope;
- invariants and forbidden shortcuts;
- concrete acceptance criteria;
- the exact canonical verification command;
- the evidence Claude must return.

Claude may choose implementation details within those constraints. If the real
API, physical model, licence, privacy boundary, or data semantics differ
materially from the task, Claude stops rather than inventing an adapter or
changing the contract.

The durable task brief is stored at `.agents/tasks/TASK-NNN.md` and pins the
base commit, branch, worktree, implementer session, owned paths, forbidden
paths, acceptance command, and required evidence. A task is not ready for
delegation until those fields are complete. See `GIT_MULTI_AGENT_WORKFLOW.md`.

## Implementation return

Claude returns:

- changed files and a concise rationale;
- commands run and unedited pass/fail summaries;
- assumptions, model limitations, and unresolved risks;
- any generated evidence path and its reproducibility metadata.

Claude does not commit. A self-review is useful but is not independent review.
It writes a handoff matching `.agents/handoffs/TEMPLATE.json`; conversational
status alone is not a durable handoff.

## Independent review

Codex inspects the diff and reruns the task's canonical check from a fresh
process. For milestone-facing physics results it also reproduces a declared
reference case or deterministic fixture and checks that the evidence records
versions, inputs, units, diagnostics, and limitations.

A failed review returns a bounded repair request to Claude. Two unsuccessful
repair rounds trigger a human checkpoint; agents do not keep modifying the
acceptance criteria. Review outcomes are appended to `.agents/review-log.md`.

Review occurs outside the implementer's writable worktree. Codex compares the
candidate with its pinned base, checks for ownership collisions and unexpected
generated or secret files, then reruns verification from a clean process. Only
Codex may form the reviewed local commit and integrate it, and only after a
`PASS` or an explicitly bounded `PASS WITH CONDITIONS`.

## Decision classes

- **A — mechanical:** local refactors, fixtures, formatting, and tests with no
  contract or numerical-behaviour change.
- **B — scoped feature:** implementation against an approved contract, followed
  by a Codex checkpoint before the next task.
- **C — architectural or consequential:** changes to shared schemas, physical
  interpretation, privacy/learning policy, trust claims, solver selection,
  public API compatibility, or deployment. Requires explicit human approval.

Subscription authentication and the no-metered-API rule apply to every class.
