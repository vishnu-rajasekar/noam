# Physical and Reasoning Environments

Naming and contract reference for `Domain` (see `ARCHITECTURE.md`'s
`src/noam/models/common.py::Domain` enum, which only implements the
confirmed environments below). The `EnvironmentManifest`/`classify`/
`prepare_model` contract described here is a future target, not yet
implemented — S001's actual current scope is tracked in
`studies/S001_airport_cw/`.

## Environment rule

An environment exists to answer a bounded class of questions using explicit
models, assumptions, validation, and evidence. Names are product identities;
the contracts and scientific boundaries matter more than any particular solver.

## Confirmed environments

### Noam

Main facade copilot and orchestrator. Noam maintains the shared project context,
queries the knowledge graph, selects relevant environments, proposes and
coordinates experiments, explains trade-offs, and teaches. It does not replace
solver output or accountable engineering approval.

### Maxwell

Structural and mechanical experimentation: load paths, stresses, stiffness,
deflection, stability, reactions, connections, movement, tolerances, fatigue
inputs, and structural feasibility. Maxwell starts as a blank-slate parent
environment, not a repackaging of an existing solver or research project. Its
first bounded capability will be created specifically for Noam's shipping
vertical slice and must conform to the shared graph and evidence contracts.

### Joule

Thermal and energy experimentation: heat transfer, thermal bridges, surface
temperatures, condensation inputs, solar gains, energy demand, climate response,
and occupant comfort. Joule also starts as a blank slate; its first bounded
capability is selected and implemented only for the shipping vertical slice.

## External projects

Cobra is an independent panelisation/planarisation research project and is not
an active Noam environment or Maxwell implementation. Noam does not plan,
validate, or depend on Cobra while it is being developed separately. A mature
Cobra may later become an external environment or adapter only after it conforms
to Noam's facade identities, graph extensions, analysis requests, immutable
results, provenance, and evidence protocols.

## Provisional environments

These names and boundaries are candidates, not committed products:

| Name | Candidate responsibility |
|---|---|
| Fick | Moisture and mass transport |
| Prandtl | Wind, airflow, pressure, and fluid behaviour |
| Huygens | Light, solar, and optical behaviour |
| Sabine | Acoustics and vibration |
| Wöhler | Fatigue, cycling, and durability |
| Pourbaix | Corrosion and material compatibility |
| Vapnik | Statistical learning and surrogate models |
| Gittins | Exploration/exploitation experiment selection |
| Wald | Sequential evidence and stopping decisions |

All provisional names require package, repository, domain, and trademark checks
before public use. `Hamilton` is not preferred for the ML environment because
it already identifies an established Python dataflow and ML framework.

## Common environment contract

Every environment must be able to:

```text
classify(question, context)
prepare_model(graph_entities, assumptions)
validate_inputs(model)
run(experiment_specification)
evaluate(results, criteria)
explain(results)
record_observation(provenance)
```

It also publishes an `EnvironmentManifest` describing:

- domain and supported questions;
- graph-schema extensions;
- supported object and analysis types;
- solver adapters and versions;
- permissions and external-data behaviour;
- validation evidence and trust level;
- required inputs, outputs, units, and known limitations.

## Cross-domain coupling

Environments exchange typed physical fields, never informal agent conclusions.
For example, a facade bracket can participate simultaneously in:

- Maxwell load transfer and deformation;
- Joule conductive heat flow and surface-temperature assessment;
- a future Fick condensation or moisture analysis;
- a future Pourbaix material-compatibility assessment;
- project cost, installation, and replacement planning.

The shared graph owns the bracket identity. Each environment owns only its
analysis representation and evidence.
