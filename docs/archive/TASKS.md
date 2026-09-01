# Noam Implementation Tasks

Tasks are sequential checkpoints. Do not start a later task until Codex records
the prior task's review verdict. See `IMPLEMENTER_REVIEWER_PROTOCOL.md`.

## Task 0 — Feasibility and deterministic reference case (Class B)

Establish the supported Joule baseline in `JOULE_ENGINE_PROFILES.md`, then prove
the local path from a minimal neutral building model through the declared
Honeybee/OpenStudio translation path to EnergyPlus 25.1 on the target Rhino 8
Mac. The case is a rectangular office building with one zone per floor and one
parameterised façade orientation.

Constraints: isolate the Ladybug worker from the Python 3.12 application core;
use the published LBT 1.10 / Python 3.10.10 / OpenStudio 3.10 / EnergyPlus 25.1
compatibility chain; no remote simulation service; no paid AI API; pin and
record exact versions; follow the external-resource acquisition protocol; do
not make compliance claims. The direct EnergyPlus 26.1 profile remains blocked
and cannot satisfy this task.

Exit: the exploratory-profile acquisition and compatibility evidence records
the bounded human risk acceptance; a
script produces a valid analysis input, records whether direct IDF or OpenStudio
translation was used, runs EnergyPlus 25.1, parses declared annual and peak
heating/cooling outputs, preserves raw logs, and passes deterministic schema,
units, provenance, and failure tests. If the accepted hash-bound runtime cannot
execute within the declared sandbox, or the real APIs differ materially, stop
and report. Promotion to a supported or compliance-capable profile is outside
this task.

## Task 1 — Headless project and study kernel (Class B)

Implement the frontend-independent Python application core and graph-compatible
JSON sidecar. It creates a project, location/site metadata, rectangular massing,
levels, one zone per floor, envelope faces, façade typology assignments, and a
study revision without importing Rhino, FastAPI, or MCP packages into domain
code.

Exit: `scripts/verify.sh --fast` passes unit, schema, identity, provenance, and
round-trip persistence tests.

## Task 2 — Joule energy comparison slice (Class B)

Implement three editable options on one selected orientation. Variables are
WWR, glazing U-value, SHGC, visible transmittance, and overhang depth. Run both
conditioned Ideal Loads and an explicitly labelled unconditioned overheating
proxy. Return annual and peak heating/cooling plus person-hour overheating
proxy metrics, with per-metric ranking and Pareto membership. Never create a
hidden aggregate score.

Exit: `scripts/verify.sh --integration` reproduces the reference case, detects
stale inputs, records failures, and emits evidence-complete result artefacts.

## Task 3 — Stable interfaces (Class B)

Expose the same application use cases through CLI, local FastAPI/OpenAPI 3.1,
SSE progress events, and bounded MCP tools/resources. Use CloudEvents-shaped
event envelopes and an OpenTelemetry adapter with content capture disabled.

Exit: contract tests prove interface parity and `scripts/verify.sh --integration`
passes without any external model API.

## Task 4 — Rhino 8 Noam panel (Class B)

Implement the C# Eto dockable panel using MVVM. The view model calls the local
application API and contains no simulation business logic. Support project
initiation, massing parameters or selected Rhino volume, façade orientation,
three editable options, run progress, result table, Pareto visibility, and
graph-linked Rhino overlays.

Exit: build succeeds for the installed Rhino 8 target; view-model tests run
headlessly; a manual smoke checklist records project creation, study execution,
result display, save/reopen, and stale-geometry handling.

## Task 5 — Release evidence and private-alpha handoff (Class B)

Package scripted prerequisites, example project, fixtures, operator guide,
limitations, privacy/learning controls, and troubleshooting. No installer may
silently enable outbound inference or metered API use.

Exit: `scripts/verify.sh --release` passes from a clean process and the release
manifest identifies every dependency, artefact hash, test result, known limit,
and manual approval still required.
