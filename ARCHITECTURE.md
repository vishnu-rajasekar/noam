# Noam Architecture

## Responsibility model

```text
Human engineer:          accountable engineering judgement and approval
Noam:                     orchestration, explanation, study coordination,
                          precedent retrieval — no numerical authority
Physical environments:   deterministic engineering calculations/simulations
                          (Maxwell, Joule, ...)
Knowledge service:        standards, guidance, products, precedents,
                          derived engineering rules (RuleCards)
Project/study service:    requirements, assumptions, risks, decisions,
                          evidence, study state
Rhino / Grasshopper:      primary geometry authoring and engineering
                          visualisation environment
```

Noam has no independent numerical authority anywhere in this system: a
`Result` is only ever produced by a deterministic tool or solver, never
inferred by a chat model.

## The study hierarchy

```text
Noam
 └─ Domain / Environment                (Maxwell, Joule, ...)
     └─ Study                           one bounded engineering problem
         ├─ Requirement                 what must be satisfied, and why
         ├─ Rule                        (future) executable form of a
         │                              standard clause — see RuleCard below
         ├─ ModelHypothesis             the idealisation chosen to answer
         │                              one analysis question
         ├─ Capability                  reusable deterministic functionality,
         │                              promoted out of a study when validated
         ├─ Experiment ─── Result       a bounded run of a Capability against
         │                              a ModelHypothesis, and what it produced
         ├─ Insight                     a finding derived from evidence
         ├─ Precedent                   reusable modelling strategy backed by
         │                              one or more studies
         └─ Evidence                    engineering/professional record tying
                                         the above to a decision
```

This hierarchy is implemented today as Pydantic models under
`src/noam/models/`, persisted as YAML/Markdown authoring files under
`studies/` and `domains/`, and indexed (not owned) by a local SQLite index
under `registry/`. **Authoring files are authoritative; the index is a
disposable, rebuildable query layer** — never hand-edit the index, and never
treat it as the source of truth if it and the files disagree.

## The governing workflow

```text
Real project problem
       ↓
Study (engineering question, decision required, project stage)
       ↓
Requirement(s)
       ↓
ModelHypothesis — the lowest-fidelity model that can answer THIS decision
       ↓
Experiment / analysis, using a Capability
       ↓
Result, then validation
       ↓
Engineering decision (human)
       ↓
Reusable Capability / Insight / Precedent → future studies
```

**Governing rule:** use the lowest-fidelity model capable of answering the
current engineering decision reliably. A Stage 2 study generally wants fast,
transparent, option-oriented models; later stages may require specific
products, detailed connections, local FEM, fabrication/tolerance data, or
test/certification evidence. Fidelity is a property of the `ModelHypothesis`,
chosen per decision, not a global setting.

### Five things that must never collapse into one "validation" flag

1. **Software correctness** — does the code do what it claims to do?
2. **Numerical/physics correctness** — does the solver converge, balance, and
   agree with a benchmark?
3. **Modelling-hypothesis correctness** — is the chosen idealisation adequate
   for *this* question (see `ModelHypothesis.fidelity`,
   `included_behaviour`/`excluded_behaviour`, `escalation_conditions`)?
4. **Code/standard applicability** — is the right design code, edition, and
   clause being applied, to the right jurisdiction and material?
5. **Engineering judgement** — the human's accountable decision, which may
   reasonably override any of the above with recorded reasoning.

A `Result` records (1) and (2). A `ModelHypothesis`'s `validation_required`
and `approval_status` record (3). A future `RuleCard` records (4), kept
strictly separate from analysis so that a solver can be numerically correct
while pointed at the wrong material standard. (5) is always a human
`Evidence`/decision record, never a system output.

## Analysis vs. design checks — a hard architectural boundary

```text
Analysis                          Design checks
────────                          ─────────────
geometry                          material standard (code + edition)
supports / releases               strength criteria
loads                             stability criteria
section stiffness                 serviceability criteria
member forces, reactions          project-specific limits
deformation
```

These are separate `Capability` families with separate provenance. **There is
no generic "utilisation" API that hides which code produced a check.** Every
future design-check `Result` retains: governing standard/rule, assumptions,
version, source, and validation state — because a solver can compute member
forces correctly while a wrapped design check silently applies the wrong
material code. Keeping them apart is what makes that failure mode visible
instead of invisible.

## Domains / environments

- **Maxwell** — structural and mechanical engineering. Contains the separate
  experimental laboratory **Cobra** (geometry/panelisation/planarisation
  research); Cobra is not a dependency of any current Maxwell study.
- **Joule** — thermal, energy, climate, and comfort. Currently dormant: its
  only existing artefact is the archived, rejected feasibility spike at
  `archive/experiments/task0_energy/` (see that directory's `STATUS.md`).
- Provisional names (Fick, Prandtl, Huygens, Sabine, Wöhler, Pourbaix,
  Vapnik, Gittins, Wald) remain documented in `ENVIRONMENTS.md` but must not
  become implemented packages before a real study needs them.

## Where the code lives

```text
src/noam/
├── models/          Pydantic models: Study, Requirement, ModelHypothesis,
│                     Capability, Experiment, Result, Insight, Precedent,
│                     Evidence, RuleCard (metadata only, no execution)
├── registry/         paths, YAML/Markdown store (authoritative), SQLite
│                     index (disposable), validation
├── studies/          study-folder scaffolding
├── cli/               argparse-based `noam` command
└── utils/             ids, YAML/JSON IO helpers

studies/<ID>_<slug>/           one folder per study (see below)
domains/<domain>/capabilities/  promoted, reusable Capability records
domains/<domain>/precedents/    promoted Precedent records
knowledge/public/               non-confidential reference material
knowledge/restricted/           gitignored; project-confidential material,
                                 mounted locally, never committed
adapters/                       contracts only, for future FrameSizer /
                                 Karamba / RFEM / RSECTION integration
experiments/                    future cross-study datasets/sweeps (Phase D)
archive/                        superseded code, kept for provenance
```

A study folder (see `studies/S001_airport_cw/` for the current instance):

```text
studies/<ID>_<slug>/
├── study.yaml              Study record (authoritative)
├── brief.md                 engineer-authored project brief
├── requirements/             Requirement records
├── model/
│   └── model-hypothesis.md   ModelHypothesis record(s)
├── calculations/             working calculations
├── experiments/               Experiment records
├── datasets/                   experiment inputs/outputs
├── validation/                 validation records
├── results/                     Result records
├── decisions/                   human decision records
└── evidence/                     Evidence records
```

## Deployment and privacy

- The registry/core requires **no network access at runtime**. Indexing and
  search are local, structured (no embeddings/vector search yet).
- `knowledge/restricted/` is gitignored; confidential project material is
  mounted there locally and never committed, never uploaded, never sent to a
  hosted model.
- No API keys, metered inference, or cloud infrastructure are required for
  study registration, requirement/hypothesis/experiment recording, or local
  search. See `AGENTS.md` for the binding development-cost boundary.
- Raw project content is never automatic training data; only validated,
  minimised derived evidence is eligible for organisation-wide learning, and
  only with opt-outs honoured (`PROTOCOLS.md`).

### The commit-safe / confidential boundary (Phase A closure, 2026-09-02)

Two directories can both hold content about the same study, and they are
not interchangeable:

```text
studies/<ID>_<slug>/            committed, EXPLICITLY COMMIT-APPROVED METADATA
knowledge/restricted/           gitignored, CONFIDENTIAL/LICENSED CONTENT
```

**Confidentiality follows the information, not the file format or how it
was entered.** A client identifier, a building dimension, a commercially
sensitive decision, a licensed standard's clause wording, or an engineer's
paraphrase of any of these can carry a confidentiality or licence
obligation regardless of whether it arrived as a PDF, was typed from
memory, or was derived by a calculation. "Could someone type it without
the source document" is *not* the test and must not be used as one.

**`studies/<ID>_<slug>/` holds only content a human has explicitly approved
for commit**, minimised and redacted to what the traceability graph
actually needs: structured metadata (ids, dates, statuses, units,
acceptance criteria, model-fidelity choices, approval states) and *opaque
references* to anything confidential (a filename, a citation, a document id
under `knowledge/restricted/`). `study.yaml`, the `Requirement`/
`ModelHypothesis`/`Experiment`/`Result`/`Insight`/`Evidence` YAML, and the
`brief.md`/`model-hypothesis.md` templates live here, but committing them
still requires that each field has been reviewed and cleared — a
`Study.confidentiality` of `restricted` flags that this review must be
strict, it does not by itself authorise inlining sensitive values. When in
doubt a value stays out of `studies/` and is referenced instead.

**`knowledge/restricted/` holds every confidential or licensed item and
every confidential *derived* detail**: client drawings, specifications,
correspondence, licensed standards text, datasets, and also notes,
paraphrases, extracted dimensions, or intermediate results that would
disclose any of the above. It is gitignored (see `.gitignore`) and is
never read by anything that could re-emit its content into a committed
file — the future Phase C standards/RAG pipeline reads from here and writes
only structured, human-reviewed `RuleCard` proposals back into the
committed registry, never source text or confidential derived detail
(`ARCHITECTURE.md`'s Phase C description above).

**Rule of thumb:** put a value in `studies/` only when a human has
explicitly cleared it for commit *and* it is either non-confidential
metadata or an opaque reference. If disclosing it would breach a
confidentiality or licence obligation — whatever its format or origin — it
belongs in `knowledge/restricted/`, cited from `studies/` by reference
only, never inlined. S001's `brief.md` and `model-hypothesis.md` currently
hold only blank templates and explicit unknowns; that is the intended
starting state, not a gap to be filled with sensitive detail.

## Future architecture (contracted for, not built tonight)

- **Standards/knowledge pipeline:** `licensed/project documents → local
  document intake → clause/section extraction → structured retrieval →
  RuleCards → human review → approved rule pack → deterministic engineering
  checks`. The standards-retrieval system and the deterministic
  rule/check registry are architecturally distinct — a calculation never
  re-reads a standard through an LLM at run time.
- **Solver adapters:** `Rhino/GH geometry → topology → FrameSizer →
  scripted Karamba/global FEM → RSECTION section properties → RFEM
  verification → results back into Rhino`, each behind an explicit adapter
  boundary. Noam's core models are not coupled to any particular solver.
  See `adapters/README.md`.
- **Experiment/ML layer:** `deterministic model → parameterised experiment →
  dataset → sensitivity/statistics → model-fidelity comparison → ML only
  where repeated high-fidelity simulation makes a surrogate worth its added
  uncertainty`. Noam must remain fully useful with zero ML.

See `docs/lab/` for the earlier project/BEM/knowledge-graph architecture that
this document supersedes as the *current* target, but which remains valid
background for later phases.
