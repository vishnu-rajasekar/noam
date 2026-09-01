# Noam — Facade Copilot Domain Foundation

## Purpose

Noam is intended to connect architectural intent to an engineered,
compliant, buildable, costed, and explainable facade proposition. It should
support learning and decision-making without replacing accountable professional
judgement.

The foundational responsibility split is:

```text
Rhino/Grasshopper: geometry and visual experimentation
Engineering services: calculations and simulations
Knowledge service: standards, guidance and precedents
Project service: requirements, risks, decisions and programme
Noam: orchestration, explanation and teaching
Human engineer: accountable judgement and approval
```

This document defines the target domain architecture; it does not assume an
existing geometry or analysis pipeline and does not claim that the wider
services are implemented. Noam owns the shared facade representation. Maxwell
and Joule will contribute domain-specific models and evidence without
redefining the shared objects.

## Governing questions

The copilot should help a project team answer a coupled set of questions:

1. Can it look like this?
2. Will it stand?
3. Will it provide comfort and environmental protection?
4. Will it comply here?
5. Can it be manufactured, transported, installed, maintained, and replaced
   here?
6. How much will it cost, how long will it take, and how certain are those
   answers?

These must not become isolated pass/fail checks. A change in geometry can alter
panel spans, joint lengths, structural loads, thermal bridges, solar response,
tolerances, fabrication, installation, programme, carbon, and cost. The system
therefore needs an explicit dependency graph between intent, physical objects,
requirements, analyses, evidence, risks, and decisions.

## Project and BEM first

Facade intelligence begins with a project rather than an isolated surface. The
engineer first establishes project identity, location, building use, levels,
orientation, climate reference, targets, units, coordinate frame, and model
provenance. A parametric massing or supplied Rhino volume is then converted into
a reviewable, solver-neutral Building Energy Model containing levels, thermal
zones, envelope faces, and adjacency.

Facade typologies are assigned to regions of that BEM. Only then does the
engineer provide bay geometry directly or select a BEM envelope region from
which Noam generates candidate bays. See
[PROJECT_LAYER.md](PROJECT_LAYER.md) for the authoritative workflow and data
provenance.

## Open forms of design intent

Intent may arrive at different levels of maturity and in different media:

- text: briefs, performance requirements, specifications, narratives, and
  design questions;
- drawings: DWG/DXF, plans, elevations, sections, details, schedules, and
  annotated PDFs or scans;
- models: massing, surfaces, meshes, NURBS/Breps, BIM/IFC objects, Rhino
  geometry, and Grasshopper definitions;
- project context: location, orientation, climate, building use, primary
  structure, procurement route, budget, programme, and available supply chain.

All inputs should be translated into a common, traceable representation while
retaining the source, version, coordinate system, units, confidence, and any
human interpretation. The original source remains evidence; a generated model
is a derived interpretation and must not silently replace it.

## Classification before calculation

Classification defines the basis of design. It determines which physical
models, codes, failure modes, interfaces, tests, and cost rules are relevant.
The first classification should cover both facade system and complexity.

### Facade-system classification

The system taxonomy should begin with common manufactured systems, including:

- unitised curtain wall;
- stick curtain wall;
- window wall and punched windows;
- rainscreen and drained/back-ventilated cladding;
- precast concrete, stone, brick, terracotta, metal, glass, and composite
  assemblies;
- double-skin, cavity, ventilated, louvred, screened, and shading systems;
- rooflights, canopies, inclined glazing, and facade/roof transitions;
- hybrids and interfaces between systems.

Classification should record the rationale and supporting evidence, not merely
assign a label. Bespoke systems are valid, but should initially be represented
as deviations, compositions, or extensions of known systems. This keeps the
standard case explainable and makes the genuinely novel parts visible.

### Simple and complex design classification

`simple` and `complex` should be derived classifications based on several
independent dimensions:

| Dimension | Typical simple condition | Typical complexity trigger |
|---|---|---|
| Geometry | planar, repetitive bays | curvature, torsion, inclination, irregular tessellation |
| Topology | regular grid and interfaces | branching, discontinuity, transitions, many unique nodes |
| Structure | short clear load paths | long spans, large movements, coupled or indeterminate behaviour |
| Thermal/moisture | continuous layers | penetrations, offsets, material transitions, condensation-sensitive zones |
| System | established typology | hybrid, novel, bespoke, or poorly evidenced assembly |
| Manufacture | standard families | many unique components, specialist forming, tight tolerances |
| Assembly | repeated sequence | difficult access, unusual sequencing, high interface density |
| Compliance | established route | conflicting requirements, unusual use, limited test evidence |
| Project context | ordinary exposure and logistics | extreme climate, exposure, transport, access, or supply constraints |

A facade may be geometrically simple but thermally or logistically complex.
The copilot should retain the dimension scores and reasons instead of reducing
the project to an unexplained single complexity score. Classification should
also be revisable as information develops.

## Functional-unit object model

The primary reasoning object should be a **Facade Functional Unit**: the
smallest repeatable assembly that performs the required facade functions and
can be related to a bay, system, elevation, building, and site.

```text
Project / Site
  Building
    Facade Zone / Orientation / Exposure
      Facade System
        Bay
          Functional Unit
            Components
            Interfaces
            Connections
            Layers and paths
```

### Functional unit

A functional unit should contain or reference:

- geometry, location, orientation, extent, repetition, and tolerances;
- system type and intended functions;
- components, materials, finishes, and replaceable parts;
- interfaces, joints, seals, gaskets, membranes, cavities, fixings, brackets,
  anchors, and fire stops;
- structural load paths, supports, restraints, releases, and movement joints;
- thermal layers, insulation continuity, thermal bridges, surface boundaries,
  air paths, vapour paths, drainage paths, and ventilation paths;
- optical and environmental properties;
- manufacturing, transport, access, installation, maintenance, and replacement
  constraints;
- applicable requirements, calculations, simulations, tests, precedents, and
  evidence;
- assumptions, uncertainties, risks, decisions, owners, and status;
- quantities, cost, carbon, lead time, and confidence ranges.

### Relations to the whole

The object model must preserve relationships rather than treating panels as
isolated objects. A unit belongs to a bay; a bay belongs to a system and facade
zone; systems meet at interfaces; facade zones respond to the building and
site. Loads, heat, air, water, vapour, fire, movement, tolerances, work
sequences, cost, and responsibility all cross these boundaries.

The same component may participate in several functional paths. For example, a
bracket transfers load, penetrates insulation, affects fire stopping, imposes
installation tolerances, and contributes cost and embodied carbon.

## From massing or drawing to facade bay

The first automation target is a standard-system pipeline that converts design
evidence into reviewable facade objects:

```text
text / massing / DWG / model
              ↓
source normalisation and provenance
              ↓
faces, zones, grids, levels, openings, edges, and interfaces
              ↓
candidate facade typologies with classification rationale
              ↓
facade bays and repeatable functional units
              ↓
components, layers, joints, supports, and performance paths
              ↓
analysis-ready structural, thermal, environmental, quantity, and cost models
              ↓
requirements, evidence gaps, options, risks, and decisions
```

### Massing-first workflow

From a massing model, the system can identify candidate envelope faces and
classify them by orientation, inclination, height, exposure, adjacency, and use.
It can then establish preliminary performance requirements before a facade
system is selected. Vertical and inclined faces must remain distinct because
load, drainage, water penetration, safety, access, and regulatory assumptions
can change with inclination.

### Drawing-first workflow

From drawings, the system should detect levels, grids, elevations, sections,
openings, panel and joint patterns, dimensions, annotations, legends, detail
references, and system boundaries. It should propose facade typologies and bay
boundaries together with the evidence and confidence behind each proposal.

Native DWG/DXF should primarily use vector entities, blocks, layers, dimensions,
and text. Computer vision is a fallback and complementary method for raster
drawings, scans, rendered sheets, and ambiguous graphical regions. Rule-based
model generation should produce candidate objects, but uncertain classifications
must be reviewable and correctable by a human.

### Model-first workflow

From Rhino, BIM, or other 3D models, the system should preserve object identity
where available and infer missing semantics from topology, geometry, metadata,
and repetition. It should avoid treating every surface patch as a manufactured
panel before a system and bay logic has been established.

## Analysis-ready model generation

A single source model should generate several purpose-specific models rather
than one overloaded digital twin:

- geometric and visual model;
- facade-system and component model;
- structural idealisation with loads, supports, joints, and combinations;
- thermal and moisture model with materials, boundaries, and interfaces;
- environmental model for solar, daylight, comfort, and exposure;
- manufacturing and assembly model;
- quantity, carbon, cost, and programme model;
- compliance, risk, assumption, and decision records.

Every derived model should point back to its source facade objects and record
its abstraction rules. This permits an engineer to understand what was omitted,
merged, idealised, or assumed.

## Interface and thermal-bridge reasoning

Interfaces should be first-class objects. For a proposed interface, the copilot
can query a controlled library of plausible system combinations, generate
candidate layer and connection arrangements, and screen them for:

- insulation and air-barrier continuity;
- linear and point thermal bridges;
- internal surface-temperature and condensation risk;
- drainage, ventilation, and water-shedding continuity;
- structural load transfer and differential movement;
- fire and acoustic continuity;
- tolerances, access, sequence, inspection, maintenance, and replacement.

Generated combinations are hypotheses, not details approved for construction.
They require applicable calculations, evidence, testing, and accountable review.

## Knowledge and decision behaviour

The copilot should distinguish:

- mandatory requirements from recommendations;
- measured or supplied facts from derived data;
- model assumptions from simulation results;
- established systems from precedents and novel proposals;
- verified conclusions from unresolved questions;
- project optimisation priorities from universal claims.

Compliance answers should cite the jurisdiction, document, edition, date, and
clause and should expose ambiguity or missing applicability information.
Geometry and analytics should lead to decision records containing alternatives,
trade-offs, evidence, assumptions, risks, required actions, ownership, and
approval status.

The objective is not a supposedly bias-free answer. It is bias-visible,
evidence-grounded assistance in which priorities, weights, assumptions,
uncertainty, and responsibility are explicit.

## Recommended development boundary

Start with standard, repeated facade systems and make the following reliable:

1. ingest a native drawing or model;
2. identify facade zones and propose bay boundaries;
3. classify the system and complexity dimensions with rationale;
4. instantiate functional units, components, interfaces, and relations;
5. generate traceable analysis-ready models;
6. compare options across geometry, structure, thermal/moisture behaviour,
   compliance, manufacture, assembly, cost, carbon, and programme;
7. return uncertainties and questions for human resolution;
8. store corrections and decisions as project evidence.

Only after this standard path is trustworthy should the same object model and
evidence process be extended to bespoke systems. Generative exploration then
operates inside explicit constraints and produces alternatives for a stated
reason, rather than unconstrained geometric novelty.
