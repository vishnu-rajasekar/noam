# STATUS — archived, not accepted infrastructure

- **Status:** rejected / unaccepted (superseded direction)
- **Decision class at the time:** B (TASK-000)
- **Moved here:** 2026-09-01, as part of the study-driven restructuring
  (see `docs/archive/TASKS.md` and the top-level `ROADMAP.md`)

## What this is

An early feasibility spike for a Joule/EnergyPlus-only first vertical slice,
implemented before the product direction moved to a study-driven engineering
orchestrator (`Noam → Domain → Study → ... → Evidence`). It simulates a
rectangular office building through Honeybee's direct-IDF path.

## Why it is archived rather than treated as accepted infrastructure

Codex's independent review (`.agents/review-log.md`, 2026-08-09 entries)
recorded two `FAIL` verdicts against the original `TASK-000` acceptance
criteria:

1. The implementation hard-coded and executed **EnergyPlus 26.1**, an
   experimental profile that `TASKS.md` (now `docs/archive/TASKS.md`) and
   `security/acquisitions/energyplus-26.1.0.json` explicitly blocked. Only
   the exploratory `lbt-1.10-os-3.10-eplus-25.1` baseline was accepted, and
   even that baseline never reached "supported" status.
2. The 26.1 run also produced physically implausible results (sizing
   temperatures up to 407.31 °C, a negative sentinel maximum airflow), so a
   clean process exit would not have established credible results even if
   the version had been correct.
3. A separate finding: the claimed `HOME` isolation
   (`os.environ.setdefault("HOME", ...)`) is a no-op whenever `HOME` is
   already set, so the documented sandbox boundary did not actually hold.

A repair was requested but no passing re-review verdict was ever recorded
before the product direction changed. **Do not treat any file under this
directory as validated, reusable, or a dependency of `S001` or any other
current study.** The rejected raw run is preserved unmodified at
`_evidence/run_20260809T135930Z/` (see `REJECTED.md` inside it) purely as an
audit record — do not relabel it or use it as a reference case.

## Why it is kept rather than deleted

`AGENTS.md` requires preserving rejected audit artefacts. The spike also
remains useful background if/when Joule/EnergyPlus work resumes (see
`docs/lab/JOULE_ENGINE_PROFILES.md` for the versioned engine-profile policy
that would govern that future work).

## Running its tests (optional, historical only)

The isolated Ladybug/Honeybee virtualenv this spike depends on is at
`.venv/` (Python 3.12, per `AGENTS.md`'s worker-isolation rule — it is not
the interpreter used by the current `src/noam` core). To reproduce the
historical (failing-acceptance) test run only:

```bash
HOME="$PWD/.ladybug_home" .venv/bin/python -m pytest archive/experiments/task0_energy/tests -v
```

This is not part of `scripts/verify.sh --fast` any more. See
`scripts/verify.sh` for the current canonical check, which now covers the
`src/noam` study/registry core instead.
