# Project Layer and Building Energy Model

## First principle

The first user action in Noam is to create or open a project. Geometry selection
is meaningful only after it has a project, site, building, revision, units, and
performance context.

```text
Create Project
      ↓
Define site, building, use, levels, and targets
      ↓
Provide or generate building massing
      ↓
Create and review a neutral Building Energy Model
      ↓
Define and assign facade typologies
      ↓
Choose a facade region and create a bay
      ↓
Run a design study and accumulate evidence
```

The project database is not assumed to exist. Noam creates it progressively as
the engineer establishes project facts, confirms derived objects, generates
alternatives, and runs studies.

## Rhino plugin experience

Noam should be a Rhino plugin with a dockable panel organised using MVVM. The
panel is a client of Noam's project and graph services; it does not embed domain
logic in view event handlers.

Suggested navigation:

1. **Projects** — create, open, archive, and inspect project status.
2. **Building** — site, use, levels, massing, zones, and BEM revisions.
3. **Envelope** — faces, facade regions, typologies, bays, and interfaces.
4. **Studies** — variables, scenarios, experiments, results, and comparisons.
5. **Evidence** — requirements, assumptions, sources, decisions, and reports.
6. **Noam** — contextual chat, teaching, warnings, and proposed actions.

The MVVM boundary is:

```text
Dockable views
      ↓ bindings and commands
Project / Building / Envelope / Study view-models
      ↓ application contracts
Project, BEM, graph, Rhino, experiment, and evidence services
      ↓
Knowledge graph + artefact store + specialist environments
```

View-models hold transient interaction state and issue commands. Project facts,
geometry identities, studies, and decisions are persisted through the knowledge
graph services.

## Project initiation

### Required to create a draft project

- project name and internal identifier;
- organisation and project ownership;
- unit system;
- local coordinate origin and north direction;
- location supplied as coordinates or an explicitly unresolved location;
- building-use or occupancy-type hypothesis;
- source of the initial building geometry.

Unknown values are allowed when labelled as unresolved. Noam must not invent
location, use, floor count, weather, or regulatory context.

### Information developed during setup

- address, latitude, longitude, elevation, and time zone;
- jurisdiction and applicable-code hypotheses;
- building typology and intended uses;
- number of floors, level elevations, and floor-to-floor heights;
- operating schedules and internal-condition assumptions;
- climate or weather dataset and its source;
- orientation and surrounding-context assumptions;
- performance targets for energy, comfort, structure, carbon, cost, and other
  project concerns;
- model source, revision, author, units, and coordinate frame.

The project can be saved in a draft state before this information is complete.
Each downstream service declares which fields it requires.

## Building geometry inputs

The initial building can be created through either route:

### Parametric massing

The engineer supplies dimensions, floor count or levels, orientation, and a
simple massing rule. Noam creates Rhino geometry and records it as generated
from those parameters.

### Supplied massing or volume

The engineer selects one or more suitable Rhino Breps, extrusions, or closed
meshes. Noam validates closure, units, orientation, and basic topology before
accepting them as a candidate building volume.

More detailed IFC, CAD, or BIM ingestion is a later additive route. It must map
to the same project and BEM objects rather than creating a separate data model.

## Neutral Building Energy Model

Noam's `BuildingEnergyModel` is a solver-neutral project representation. It is
not initially an EnergyPlus file and must not inherit the schema or assumptions
of one simulation tool.

The initial BEM contains:

```text
Project
  Site
  Building
    BuildingRevision
      Levels
      Spaces / ThermalZones
      EnvelopeFaces
      Adjacencies
      Openings where known
      Internal-condition assumptions
      Weather reference
```

For the first slice, a selected closed volume is intersected by confirmed level
planes. Each floor may begin as one thermal zone. Perimeter/core zoning,
multi-space floors, shading context, detailed openings, and HVAC systems are
later refinements rather than prerequisites for establishing the project layer.

Every derived BEM object links to its source geometry and derivation rule. The
engineer reviews the levels, zones, envelope orientation, adjacency, and areas
before promoting a BEM revision for use by studies.

## Facade typologies

A `FacadeTypology` is a project-level hypothesis or confirmed system family
assigned to one or more envelope regions. It provides consistent intent and
early performance assumptions without pretending that detailed components have
already been designed.

An initial typology may contain:

- name and system family;
- opaque, glazed, or mixed composition;
- conceptual build-up or component roles where known;
- thermal, optical, air/water, structural, fire, acoustic, durability, cost,
  and carbon targets or assumptions;
- orientation, height, inclination, exposure, or use constraints;
- source, confidence, author, and review state.

A BEM can use several facade typologies. Assignment may be manual, generated by
rules, or proposed by Noam, but inferred assignments remain reviewable.

## From BEM or Rhino geometry to a facade bay

Noam supports two first-class routes.

### Route A — Engineer-provided bay geometry

1. The engineer selects a Rhino surface, Brep face, bounded sub-surface, or
   object collection.
2. Noam records the geometry and source revision.
3. The engineer identifies the parent building, envelope region, and typology,
   or asks Noam to propose them.
4. Noam derives dimensions, orientation, topology, and adjacency.
5. The engineer confirms the resulting `FacadeBay` and, when appropriate, its
   `FunctionalUnit` interpretation.

### Route B — Bay generated from the BEM

1. The engineer selects an `EnvelopeFace` or `FacadeRegion` in Rhino or the
   Building/Envelope panel.
2. The engineer provides a grid, module, floor relationship, boundary curves,
   or subdivision rule.
3. Noam generates candidate bay boundaries and Rhino representations.
4. The engineer reviews, edits, and confirms the bays.
5. Confirmed bays inherit their parent region, typology, orientation, exposure,
   and BEM relationships.

An envelope surface is therefore not automatically a bay. It becomes source
geometry for a facade region or bay through an explicit, recorded operation.

## Data provenance

| Information | Primary source | Initial status |
|---|---|---|
| Project identity and ownership | Engineer/organisation | Declared |
| Location, use, levels, targets | Engineer or project brief | Declared |
| Climate and geographic data | Approved open dataset | Sourced |
| Building massing | Rhino selection or Noam generator | Observed or generated |
| Areas, orientation, adjacency | Geometry/BEM service | Derived |
| Thermal zones and envelope faces | BEM generation rule | Generated and reviewable |
| Facade typology | Engineer or classification service | Declared or inferred |
| Bay boundary | Selected geometry or subdivision rule | Observed or generated |
| Components and interfaces | Engineer, template, or study generator | Declared or generated |
| Analysis model | Maxwell, Joule, or another environment | Generated |
| Numerical result | Deterministic calculation or solver | Computed observation |
| Recommendation | Noam | Inference |
| Project decision | Accountable engineer | Approved decision |

Each persisted assertion carries source, method, revision, units, actor,
confidence, and review state as applicable.

## Project states

```text
Draft
  → Geometry supplied
  → BEM generated
  → BEM reviewed
  → Envelope typologies assigned
  → Study-ready
  → Studies active
  → Decision recorded
```

The state describes readiness, not design completeness. A new building or
geometry revision can invalidate later states while preserving history.

## First shipping slice

The initial vertical slice is:

> Create a project, generate a reviewable BEM from a simple Rhino volume and
> level data, assign multiple facade typologies, choose one facade region,
> create or select one bay, run one bounded Maxwell and one bounded Joule
> study, and produce a graph-backed comparison and evidence report.

This proves the project layer, BEM, facade semantics, graph backbone, Rhino
interaction, domain-service contracts, revision behaviour, and reporting in one
coherent workflow.
