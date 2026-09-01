# Knowledge Graph Backbone

## Principle

Noam uses one logical knowledge graph as its system of record. It connects what
the facade is, what is required of it, how it was analysed, what was observed,
and why a decision was made.

The implementation is hybrid:

- an operational typed property graph supports rapid application development
  and traversal queries;
- controlled vocabularies, JSON-LD contexts, validation shapes, and RDF
  import/export provide semantic interoperability;
- semantic exports, vector indexes, search indexes, and analytical tables are
  derived projections, not competing sources of truth;
- the storage backend remains replaceable behind stable graph contracts.

This permits modular shipping without giving up provenance, validation, or a
path to organisation-scale deployment.

## Graph modules

### Intent

Briefs, design goals, constraints, optimisation priorities, questions, source
documents, and requested outcomes.

### Product and facade

Project, site, building, building revision, level, space, thermal zone,
envelope face, facade zone, typology, system, bay, functional unit, component,
material, connection, interface, and functional path.

### Geometry

Stable facade identities linked to Rhino object IDs, coordinate frames, units,
geometry revisions, representations, topology, and derived analysis geometry.
The graph stores identity and metadata; large geometry and mesh artefacts remain
in the artefact store.

### Requirements

Jurisdiction, regulation, standard, clause, guidance, project criterion,
applicability, exception, effective date, document edition, and verification
status.

### Experiments

Hypothesis, scenario, analysis model, parameter, boundary condition, solver,
run, transfer, observation, result, convergence, uncertainty, and failure.

### Evidence

Calculation, simulation, test, measurement, precedent, source document,
provenance, confidence, validation, review, and approval.

### Delivery

Quantity, cost, carbon, manufacture, procurement, programme, installation,
maintenance, risk, decision, action, responsibility, and approval.

## Core relations

```text
FacadeZone CONTAINS Bay
BuildingRevision HAS_LEVEL Level
BuildingRevision HAS_ZONE ThermalZone
ThermalZone BOUNDED_BY EnvelopeFace
FacadeTypology ASSIGNED_TO FacadeRegion
FacadeRegion SUBDIVIDED_INTO Bay
Bay INSTANTIATES FunctionalUnit
FunctionalUnit HAS_COMPONENT Bracket
Bracket CONNECTS Mullion TO Slab
Bracket INTERRUPTS InsulationPath
Requirement APPLIES_TO FacadeZone
AnalysisRequest REFERENCES Bracket
SolverRun IMPLEMENTS AnalysisRequest
Result PRODUCED_BY SolverRun
Evidence SUPPORTS Decision
GeometryRevision SUPERSEDES GeometryRevision
Change INVALIDATES AnalysisModel
```

Relations are typed, directed where meaningful, versioned, and attributable to
a source or actor.

## Identity and time

Every shared entity receives a stable identifier independent of any one tool.
Tool-specific IDs—such as a Rhino object GUID or an RFEM member number—are
aliases scoped to a model and revision.

Facts are superseded rather than silently overwritten. Records distinguish:

- when a fact was valid in its source or project;
- when Noam learned or changed it;
- which geometry, document, solver, and environment version produced it;
- which later changes invalidate dependent models, evidence, or decisions.

## Trust and promotion

Graph assertions carry, where applicable:

- source and source location;
- organisation and project scope;
- jurisdiction and applicability;
- confidentiality and permissions;
- author or producing tool;
- confidence and validation status;
- reviewer and approval status;
- units, coordinate frame, and revision.

Language models cannot write authoritative facts directly. Noam produces a
proposed `GraphChangeSet`; deterministic validation, access rules, and human
approval decide whether it becomes trusted project knowledge.

## Artefacts

Large or specialised content remains outside the graph:

- `.3dm`, DWG, IFC, and solver input files;
- meshes and multidimensional result fields;
- images, animations, and viewport captures;
- spreadsheets, PDFs, reports, and certificates.

The graph stores immutable references with content hashes, media type, units,
coordinate frame, ownership, permissions, and creation provenance.

## Environment extensions

Each specialist environment registers a bounded graph extension. Maxwell can
add structural idealisations, load cases, reactions, and deformation evidence;
Joule can add thermal zones, boundaries, heat flows, comfort results, and
thermal-bridge evidence. Neither redefines the shared bracket or bay.

Extensions must declare their entity types, relations, required fields,
validation rules, supported graph-schema version, and migration path.

## Required queries

The graph must support questions such as:

- Which requirements apply to the facade bay selected in Rhino?
- Which models and decisions depend on this bracket or material?
- What becomes invalid if its geometry changes?
- Which structural and thermal evidence supports the current option?
- Which assumptions remain unverified?
- Which alternatives satisfy a requirement within stated uncertainty?
- Which result was produced from this geometry, solver, and boundary-condition
  revision?

Vector retrieval may discover relevant text, but graph relationships and cited
sources establish applicability and evidential lineage.

## Initial storage strategy

The first implementation may use an embedded local property graph for rapid
delivery. Persistence is accessed through a graph repository contract rather
than vendor-specific queries in domain code. A later organisation-hosted graph
must accept the same stable identities, schemas, change sets, and query
contracts without redefining the domain.
