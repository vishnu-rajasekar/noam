# TASK-001 — Phase A closure (study kernel and registry)

- Decision class: B (repairs a Class B deliverable; no schema-breaking
  change was required — Experiment/Result already carried the fields this
  task's checks needed, per the prior Codex verdict C repair)
- Dependency: none (Phase A itself)
- Base commit: unavailable (unborn `main`; same bootstrap exception as
  TASK-000 — this repository has no baseline commit yet)
- Branch: `main` bootstrap only
- Worktree: repository primary worktree
- Implementer/session: Claude
- Orchestrator/reviewer: Codex (via the `codex-review.sh` Stop-hook — see
  "Coordination" below; this task was authorised directly by the human,
  not specified by Codex first, because no baseline commit exists yet for
  Codex to have specified it against)
- Owned paths: `src/noam/**`, `tests/noam_core/**`, `scripts/verify.sh`,
  `ARCHITECTURE.md`, `ROADMAP.md`, `AGENTS.md`, `.gitignore`,
  `.agents/tasks/TASK-001-phase-a-closure.md`,
  `.agents/handoffs/TASK-001-phase-a-closure.json`
- Forbidden: paid APIs, network access, installers, live model
  integration, Rhino/Grasshopper, solvers, S001 confidential content,
  Git mutations, committing

## Objective and acceptance

Close the Phase A inspection findings without weakening any test or
inventing project values:

1. `scripts/verify.sh --fast` finds and uses a valid available Python
   environment reliably, and fails clearly (not silently) when required
   dependencies are genuinely unavailable.
2. Registry-validation gaps closed where they belong to the Phase A
   traceability contract: filename/id consistency, duplicate-id detection
   (studies, requirements, hypotheses, experiments, results, insights,
   evidence, capabilities, precedents), `Insight`/`Evidence` cross-checked
   against their study (previously unchecked; `Evidence` was not even
   loaded), and `Result.capability_id` / `Experiment.capability_ids`
   checked against real `Capability` records (previously unchecked).
3. An absent or unapproved reviewed `ModelHypothesis` cannot masquerade as
   a valid, reviewed S001 hypothesis: an `Experiment` referencing a
   non-existent hypothesis id fails validation (already true after the
   prior Codex-verdict-C repair); an `Experiment` referencing a hypothesis
   whose `approval_status` is not `approved` now also fails validation.
4. The commit-safe (`studies/`) vs. prohibited-confidential
   (`knowledge/restricted/`) boundary is documented concretely in
   `ARCHITECTURE.md`.
5. The durable-`.agents/`-vs-`.gitignore` contradiction is resolved:
   `.gitignore` narrowly ignores only the two genuinely ephemeral
   dotfiles the review tooling itself regenerates
   (`.last-review-hash`, `.review-round-count`); `.agents/tasks/`,
   `.agents/handoffs/`, and `.agents/review-log.md` are tracked.
6. `ROADMAP.md` records the approved Phase A.5/A5.1 insertion, scoped
   exactly as authorised, with no broadening.
7. Canonical verification and the full existing test suite pass.

## Invariants and stop conditions

- Do not weaken tests, tolerances, or the verification script to obtain a
  pass.
- Do not invent project/engineering values anywhere (S001's `brief.md` and
  `model-hypothesis.md` remain templates with unknowns left unknown).
- Do not touch `security/acquisitions/`, `.claude/settings.json`, or
  perform any Git mutation.
- Stop and escalate if a finding requires a schema-breaking change beyond
  what is already in scope, or requires confidential/S001-specific values
  that were never supplied.

## Acceptance criteria and verification command

`bash scripts/verify.sh --fast` — must exit 0 with the full
`tests/noam_core` suite passing. `bash scripts/noam.sh registry validate`
against the real `studies/S001_airport_cw` must report no problems.

## Coordination (on-demand review, human decision 2026-09-02)

Claude cannot invoke `codex` directly (verified: not on the sandboxed
Bash tool's PATH, and `~/.local/bin` is outside the sandbox's allowed read
scope per `.claude/settings.json`). The only working review path is the
existing Stop-hook (`~/.claude/scripts/codex-review.sh`), which runs
`codex exec` outside Claude's sandbox once Claude reaches a clean stopping
point with a non-empty diff. This task's completion is therefore submitted
for review by finishing this bounded gate and stopping; the hook's verdict
(if it blocks) arrives as feedback in the next turn and is treated as an
authoritative, unmodifiable finding per `IMPLEMENTER_REVIEWER_PROTOCOL.md`.
The hook enforces its own two-round repair cap
(`MAX_ROUNDS=2` in that script) rather than the three specified in the
human's instruction for this session; that discrepancy is a property of
shared harness infrastructure outside this repository and is reported
here rather than silently overridden.

## Required evidence

See `.agents/handoffs/TASK-001-phase-a-closure.json` for changed files,
verification command and result, assumptions, limitations, and unresolved
risks.
