# Rhino and Solver Integrations

## Rhino-first product rule

Analysis related to design geometry should be authored, launched, inspected,
and compared from Rhino whenever practical. “Inside Rhino” means a coherent
Rhino-centred workspace, not necessarily loading every numerical library into
Rhino's process.

Users should be able to:

- select or create geometry and classify facade objects;
- assign systems, materials, loads, supports, boundaries, and scenarios;
- generate and inspect analysis idealisations;
- launch and monitor solver jobs;
- view mapped fields, deformations, diagrams, warnings, and uncertainty;
- edit option and requirements tables;
- open dashboards and reports;
- approve proposed model and graph changes.

The existing [Rhino MCP platform](../mcps/rhino-mcp/README.md) is the starting
point for agent access to Rhino context, RhinoCommon operations, Grasshopper
canvases, viewport images, and an in-Rhino conversation panel. Maxwell and
Joule do not inherit an existing solver adapter; their first adapters are built
against Noam's contracts for the shipping vertical slice.

## Adapter architecture

```text
Rhino facade objects
        ↓
analysis request linked to graph identities
        ↓
environment model builder and validator
        ↓
solver-specific adapter
        ↓
isolated local process / container / approved external tool
        ↓
result validation and immutable artefacts
        ↓
graph evidence + Rhino result mapping
```

An adapter owns translation, invocation, result extraction, and diagnostics. It
does not decide whether a result is acceptable for the project.

## Selection policy

Prefer open-source tools when they are robust for the intended question and can
be validated, automated, reproduced, and legally deployed. Evaluate candidates
against:

- supported physics and element/model types;
- verification and validation evidence;
- convergence and diagnostic quality;
- API, CLI, and headless operation;
- meshing and result extraction;
- unit and coordinate handling;
- operating-system and container support;
- licence, modification, and redistribution terms;
- performance and organisational acceptance.

Use four integration tiers:

1. robust open-source solver with a stable programmatic interface;
2. open-source solver wrapped by a managed worker and conversion pipeline;
3. free or separately licensed tool after automation and redistribution review;
4. commercial tool such as RFEM or ANSYS when it offers required capability,
   validation, compatibility, or an established organisational workflow.

Open-source preference never lowers the engineering validation bar.

## Candidate tools

| Domain | Initial candidates | Status in Noam |
|---|---|---|
| FEM | CalculiX, Code_Aster, Elmer, FEniCS; RFEM fallback | Benchmark and select per analysis class |
| Thermal bridge | Purpose-built open solver to be selected; THERM candidate | Licence and automation verification required |
| Building energy | [EnergyPlus](https://energyplus.net/)/OpenStudio | Open-source candidate |
| CFD | [OpenFOAM](https://openfoam.org/licence/) | Open-source candidate |
| Commercial multiphysics | RFEM, ANSYS, others | Adapter only when justified |

The list is a candidate registry, not a claim that an adapter exists or that a
tool is validated for every facade question.

Separately developed research tools, including Cobra, remain outside Noam until
they deliberately implement the same adapter, graph, result, provenance, and
validation contracts. Their internal data structures do not shape Noam's
backbone.

## Capability manifest

Every adapter publishes:

```yaml
tool: example_solver
version: 1.0
environment: Maxwell
capabilities:
  - create_analysis_model
  - run_static_analysis
  - extract_displacement_field
execution: isolated_local_worker
permissions:
  read_project: true
  modify_rhino: approval_required
  network: denied
validation_status: experimental
```

The real manifest also declares units, coordinate conventions, supported schema
versions, licences, timeouts, resource limits, and failure states.

## State and results

Grasshopper wires and Rhino objects carry lightweight `ResultHandle` values,
not multi-gigabyte field databases. The handle references:

- graph run and source-object identities;
- geometry and mesh revisions;
- units and coordinate frame;
- solver, adapter, and environment versions;
- status, convergence, and diagnostics;
- summary values and immutable artefacts;
- visualisation mappings and provenance.

## Field transfer and coupling

Cross-solver exchange uses an explicit `TransferSpec` containing source and
target regions, physical quantity, units, mapping method, coordinate transform,
conservation requirement, relaxation, coupling direction, and convergence
criteria.

Raw Grasshopper feedback loops are not used for multiphysics iteration. A
coupling controller validates participants, creates checkpoints, runs eligible
jobs, transfers fields, measures residuals, applies relaxation, and stops on
convergence or a declared limit.

## Fallback discipline

Prefer structured APIs, command-line interfaces, and documented file formats.
Screen reading and UI automation are last-resort integrations. If a fallback
cannot reliably confirm inputs, solver status, results, and provenance, it is
not suitable for authoritative engineering evidence.
