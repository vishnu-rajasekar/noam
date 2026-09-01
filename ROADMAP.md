# Noam Roadmap

## Delivery principle

Noam grows from real engineering studies, not speculative platform
architecture. The active study is
**S001 · Maxwell · Airport Unitised Curtain Wall Structural Design**
(`studies/S001_airport_cw/`); every near-term phase exists to make that study
— and the next one — more traceable, reusable, and defensible.

This replaces the earlier Task 0–5 roadmap (`docs/archive/TASKS.md`), which
assumed a Joule/EnergyPlus-only first vertical slice and directly contradicted
`docs/lab/PROJECT_LAYER.md`'s Maxwell+Joule first slice. That contradiction is
why the old roadmap is archived rather than amended: see
`docs/archive/README.md`.

Cobra remains a separate research project, not a dependency of any phase
below. It may integrate later only by conforming to Noam's stable contracts.

## Phase A — Study kernel and registry (this restructuring)

Structured local study memory and provenance, with no network dependency:

- `src/noam/models/` — Study, Requirement, ModelHypothesis, Capability,
  Experiment, Result, Insight, Precedent, Evidence, RuleCard(metadata-only).
- `src/noam/registry/` — YAML/Markdown authoring store (authoritative) plus a
  local SQLite index (disposable, rebuildable — a documented, offline-first
  substitute for the DuckDB index originally suggested; see the migration
  report for why).
- `src/noam/cli/` — `noam study|requirement|hypothesis|experiment|insight|
  capability|registry|search` commands.
- `studies/S001_airport_cw/` seeded and ready for engineer input.

Exit condition: `noam study show S001` and `noam registry validate` run
against real, tested code with zero network calls, and the traceability
contract `registry validate` enforces actually matches what's claimed —
filename/id consistency, duplicate-id detection, and every cross-reference
(`Study`↔child records, `Experiment`→`ModelHypothesis` including its
*approval* state, `Experiment`/`Result`→`Capability`) checked, not just
declared. Closed 2026-09-02 (Phase A closure task).

## Phase A.5 — Recorded-fixture local proposal intake

Approved as a Class C sequencing change inserted before Phase B (human
decision, 2026-09-02): before any live model is wired to Noam, prove the
request/response/provenance contract a future local model integration must
satisfy, entirely offline, against recorded fixtures.

**A5.1 — Recorded-Fixture Local Proposal Intake** (scope fixed by the
authorising task; do not broaden without a new human decision):

- runtime request/response/provenance contracts for a "proposal" produced
  from source material;
- a deterministic recorded-fixture backend — no live Ollama or any other
  live model;
- a tiny synthetic or clearly redistributable fixture corpus, each fixture
  carrying source, licence, and SHA-256 metadata;
- a structured proposal package: `sourced_facts`, `inferred_facts`,
  `missing_information`, `proposed_study_fields`, `proposed_requirements`,
  `proposed_model_hypothesis`;
- every claim linked to a source, carrying a confidence value, and fixed at
  `status=proposed` — model output never approves an engineering record;
- byte-stable recorded output, and structured unresolved states (not
  invented defaults) for missing or incompatible inputs;
- network-denial, prompt-injection-content, privacy, and
  authority-boundary tests;
- no raw prompt or corpus content in logs.

Explicitly out of scope for A5.1: live Ollama/any live model, downloads or
installations, embeddings/vector search, licensed standards, confidential
or S001 content, `RuleCard` promotion, Rhino/Grasshopper, solvers,
engineering conclusions, autonomous approval, and any change to an
established engineering schema (`src/noam/models/`) unless independent
review identifies a concrete compatibility defect requiring a new human
approval.

No A5.2 or later sub-task is defined or authorised yet.

## Phase B — S001 Maxwell vertical slice

Use the Airport CW study to establish the first real Maxwell capabilities:

- a reviewed `ModelHypothesis` for at least mullion sizing (isolated-member
  idealisation) and one global-frame question;
- a preliminary member-analysis adapter contract against the existing
  **FrameSizer** tool (adapter boundary only — FrameSizer itself is not
  reimplemented, see `adapters/README.md`);
- a global frame analysis adapter contract (Karamba/RFEM candidates);
- a model-comparison record between isolated-member and global-frame results
  for the same question, so the escalation trigger between them is evidenced
  rather than assumed;
- a validation workflow that keeps analysis and design-check evidence
  separate (`ARCHITECTURE.md` § analysis vs. design checks).

Exit condition: S001 has at least one `Experiment` with a recorded `Result`,
a human-reviewed `ModelHypothesis`, and a decision that traces back through
both.

## Phase C — Knowledge/standards vertical slice

Private, local standards and project-document retrieval for S001:
`knowledge/restricted/` document intake → clause/section extraction →
`RuleCard` proposals → human review. RuleCards remain metadata-only until a
human promotes one; no clause text is fetched or scraped, and no deterministic
check ever re-reads a standard through an LLM at run time
(`ARCHITECTURE.md`).

## Phase D — Engineering experiment/data layer

Parameter sweeps, datasets, sensitivity, and model-fidelity comparison
(`experiments/` at the repository root, distinct from a single study's
`experiments/` folder) — built once S001 or a following study has enough
repeated experiments to make sweep tooling worth its cost.

## Phase E — ML only when justified

Surrogate modelling and active learning, only once repeated high-fidelity
simulations exist to train and validate against. Noam must remain fully
useful with zero ML; this phase does not gate any earlier one.

## Phase F — Additional domains and studies

Joule thermal/energy work resumes only through the versioned engine-profile
discipline in `docs/lab/JOULE_ENGINE_PROFILES.md` (the archived Task 0 spike
does not count as a running start — see
`archive/experiments/task0_energy/STATUS.md`). Fick (hygrothermal),
panelisation/system-level studies, and further Maxwell/Joule studies follow
the same Study → ModelHypothesis → Experiment → Capability pattern proven in
Phase B, rather than a bespoke architecture per domain.

## Explicit non-goals for the near term

- autonomous compliance or engineering approval;
- a generic "utilisation" API that hides the governing design standard;
- semantic/vector search (structured search first — see Phase A);
- reimplementing FrameSizer, Karamba, RFEM, or RSECTION instead of adapting
  to them;
- multi-agent runtime infrastructure beyond the existing
  Codex-orchestrator/Claude-implementer worktree workflow;
- a local/private LLM for standards retrieval (contracted for in
  `ARCHITECTURE.md`, not built until Phase C needs it).
