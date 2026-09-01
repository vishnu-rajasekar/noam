# Noam

> An engineering orchestrator and engineering-memory system.

Noam coordinates engineering evidence. It is not an autonomous engineer, and
it holds no independent numerical authority — deterministic tools calculate,
the human engineer decides, and Noam's job is to make that work progressively
more reusable, traceable, and easier to validate over time.

## What Noam is for

Every study should leave Noam a little smarter for the next one:

- **more reusable** — a validated `ModelHypothesis` or `Capability` from one
  study is discoverable and reusable in the next, instead of being
  reinvented;
- **more traceable** — every requirement, assumption, experiment, and
  decision is recorded against the study that produced it;
- **better informed** — precedent and prior evidence are queryable before an
  engineer starts modelling from scratch;
- **easier to validate** — software correctness, numerical correctness,
  modelling-hypothesis correctness, code/standard applicability, and
  engineering judgement are tracked as distinct things, never collapsed into
  one pass/fail "validation" flag;
- **easier to record as professional evidence** — the same study record that
  supports an engineering decision doubles as chartership/CPD evidence.

Noam grows from real engineering studies, not from speculative platform
architecture built ahead of need.

## The hierarchy

```text
Noam
 └─ Domain / Environment      (Maxwell, Joule, ...)
     └─ Study                 (one bounded engineering problem)
         ├─ Requirement
         ├─ ModelHypothesis
         ├─ Experiment ──── Result
         ├─ Capability       (reusable, promoted out of a study)
         ├─ Insight
         ├─ Precedent
         └─ Evidence
```

The repository — structured study folders plus a local index — is the source
of truth. Chat systems (Claude, Codex, a future local/private LLM) are
reasoning interfaces over that record, never the record itself.

## Current first study

**S001 · Maxwell · Airport Unitised Curtain Wall Structural Design** — see
[`studies/S001_airport_cw/`](studies/S001_airport_cw/). This is the study the
rest of the foundation exists to support; read `ARCHITECTURE.md` and
`ROADMAP.md` before extending it.

## Documentation map

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — current canonical architecture:
  responsibility model, domains, the study hierarchy, the
  analysis/design-check boundary, and where the code lives.
- [`ROADMAP.md`](ROADMAP.md) — the study-driven near-term plan (Phase A–F).
- [`AGENTS.md`](AGENTS.md) — binding operating rules for humans and agents.
- [`ENVIRONMENTS.md`](ENVIRONMENTS.md) — Maxwell/Joule/Cobra and provisional
  domain naming and contracts.
- [`PROTOCOLS.md`](PROTOCOLS.md) — evidence, privacy, trust levels, and
  failure behaviour, unchanged in spirit and now applied to the study model.
- [`GIT_MULTI_AGENT_WORKFLOW.md`](GIT_MULTI_AGENT_WORKFLOW.md) and
  [`IMPLEMENTER_REVIEWER_PROTOCOL.md`](IMPLEMENTER_REVIEWER_PROTOCOL.md) —
  how Codex and Claude divide task specification, implementation, and
  independent review.
- [`docs/lab/`](docs/lab/) — earlier BEM/facade-first design thinking, still
  useful background, not the current implementation target.
- [`docs/archive/`](docs/archive/) — superseded, contradicted material kept
  for provenance only.

## Quickstart

```bash
uv sync                    # once uv/network access are available
uv run noam --help
uv run noam study show S001
uv run noam registry validate
uv run noam registry index

# Fallback, before `uv sync` has run (needs pydantic + PyYAML importable by
# whatever `python3` resolves to -- see the migration report):
scripts/noam.sh --help
scripts/verify.sh --fast
```

## Status

This directory now contains a minimal, executable local foundation
(`src/noam/`): structured Study/Requirement/ModelHypothesis/Capability/
Experiment/Result/Insight/Precedent/Evidence models, a filesystem-backed
study registry, a local (non-networked) index, and a small CLI. It does not
yet contain any deterministic Maxwell solver adapter, any Rhino integration,
or any standards/RAG pipeline — see `ROADMAP.md` for what's deferred and why.
