# Adapters (contracts only — not implemented)

This directory is where future solver adapters live, once S001 (Phase B,
see `ROADMAP.md`) actually needs one. Nothing here is implemented tonight.

## Why adapters, not reimplementation

Noam's core models (`src/noam/models/`) are not coupled to any particular
solver. `Capability.implementation_reference` points at an adapter; the
`Capability` record itself (inputs, outputs, assumptions, limitations,
valid domain, validation evidence) is what a study actually reasons about.

## Known external assets S001 will eventually need an adapter for

None of these are reimplemented here — they are existing tools the study
will call out to:

- **FrameSizer** — existing preliminary beam/member sizing based on
  conventional formulas. Candidate for the first adapter: isolated-member
  mullion/transom sizing.
- **Grasshopper curtain-wall layout workflow** — existing geometry
  generation, feeds a `ModelHypothesis`'s geometry idealisation.
- **Rhino / Grasshopper** — geometry authoring (see `ARCHITECTURE.md`).
- **Karamba** — scripted global-frame/FEM analysis candidate.
- **RFEM** — structural verification / global FEM candidate.
- **RSECTION** — section-property calculation candidate.

## The shape an adapter contract will take

```text
Rhino/GH geometry
      ↓
    topology
      ↓
  FrameSizer                    (isolated-member preliminary sizing)
      ↓
scripted Karamba / global FEM   (global-frame verification)
      ↓
RSECTION section properties     (where required)
      ↓
RFEM verification               (where justified)
      ↓
results back into Rhino
```

Each arrow above is a bounded, typed contract, not a direct dependency of
`src/noam/models/`. An adapter converts a `ModelHypothesis` plus a
`Capability`'s declared inputs into whatever the external tool needs, and
converts the tool's raw output back into a `Result` — never the reverse (no
tool-specific shape leaks into the shared models).

**Do not build an adapter before a `ModelHypothesis` in S001 actually
requires it.** See `ROADMAP.md` Phase B.
