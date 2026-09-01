# Git Multi-Agent Workflow

This workflow makes concurrent agent work attributable, reviewable, and
recoverable. Git is the evidence boundary; chat transcripts are coordination,
not the system of record.

## Invariants

1. `main` and its primary worktree are owned by the Codex orchestrator for
   planning, review records, and integration.
2. One task maps to one branch, one worktree, one implementer session, and one
   durable handoff. No writable worktree is shared between agents.
3. Every task starts from a recorded immutable base commit. File ownership is
   declared before work starts; overlapping ownership is resolved by the
   orchestrator, never by concurrent edits.
4. Claude implements but cannot commit, merge, rebase, push, or mutate Git
   history. Codex reviews independently and creates local commits only after
   the declared checks pass.
5. Nothing is pushed, published, deployed, or opened as a pull request without
   explicit human approval. Force pushes, destructive resets, and `git clean`
   are prohibited.

## Bootstrap exception

Task 0 began before this repository had a commit. Git cannot create a worktree
from an unborn branch, so Task 0 may be implemented in the initial worktree.
This does not waive review. Codex must inspect all initial files, rerun Task 0's
checks, record the verdict, and then create the first authorised local baseline
commit. This is the sole exception; Task 1 onward follows the isolated flow.

## Task lifecycle

### 1. Specify

Codex creates `.agents/tasks/TASK-NNN.md` containing:

- objective and decision class;
- base commit SHA and dependency task;
- branch `agent/claude/task-NNN-short-name`;
- worktree `.worktrees/task-NNN-short-name`;
- implementer/session identity;
- owned and forbidden paths;
- invariants, acceptance criteria, and exact verification command;
- expected evidence and stop conditions.

The primary worktree must be clean before delegation. Codex checks existing
task ownership to prevent collisions. The orchestrator can create the isolated
tree with `scripts/create_task_worktree.sh TASK-NNN short-name [base-ref]`;
the script refuses unborn repositories, dirty integration trees, existing
branches, and existing worktree paths.

### 2. Isolate and implement

Codex creates the branch and worktree from the pinned base. Claude works only
inside that worktree and one task at a time. It may not pull unrelated changes
into its branch or modify orchestration policy. Generated dependencies,
solver distributions, secrets, caches, and result artefacts stay ignored.

Claude records a JSON handoff under `.agents/handoffs/` using `TEMPLATE.json`.
The handoff includes actual changed files, commands and exit results, evidence
paths and digests, assumptions, limitations, unresolved risks, and final state.

### 3. Review independently

Codex verifies the base SHA and diffs the complete candidate, including
untracked files. It checks scope, architecture, privacy, supply-chain changes,
scientific claims, secrets, and generated-file leakage. Canonical checks run in
a fresh process outside the implementer's writable context; milestone physics
also reproduces the declared reference case.

The verdict is appended to `.agents/review-log.md` as `PASS`, `PASS WITH
CONDITIONS`, or `FAIL`. A failure returns a bounded repair request in the same
task worktree. Acceptance criteria are not weakened to obtain a pass.

### 4. Integrate

After a passing verdict, Codex creates a small logical local commit and
integrates it into `main` without rewriting shared history. Recommended
trailers are:

```text
Task: TASK-NNN
Agent-Implementer: Claude
Agent-Reviewer: Codex
```

Do not use `Co-authored-by` to imply that an agent is a human author. The task
brief, handoff, review record, tests, and acquisition manifests are committed
with the code they explain.

### 5. Retain and clean up

After integration, Codex confirms that the handoff/evidence is durable and the
branch is contained in `main`. Worktree removal and branch deletion are
separate, explicit cleanup actions; neither is performed by an implementer.
Run `git worktree prune` only after inspecting `git worktree list` and only to
remove already-stale administrative records.

## Concurrency and recovery

The current limit is one active implementation worktree plus one independent
review context. Increase it only after ownership checks are automated. If work
is interrupted, preserve the worktree and handoff, record the last known base
and verification state, and resume the same task rather than copying partial
files between trees. If the base moves, Codex decides whether to integrate the
candidate first or create a new task; Claude does not self-rebase.

## Commit quality

Commits are scoped to one task and contain no secrets, local runtimes, caches,
large solver outputs, or unrelated formatting. Tests and documentation change
with behaviour. A passing test is evidence only for its declared scope; it is
not an engineering approval or a solver-validation claim.
