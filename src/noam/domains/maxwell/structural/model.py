"""Solver-neutral structural model -- Maxwell's own vocabulary, not FrameSizer's.

Scope is deliberately narrow: this is the smallest shape that can represent
two benchmarks -- a simply-supported single-span member under one central
point load, and the same member under one full-span uniformly distributed
load (see ``knowledge/restricted/framesizer_audit/`` for the audit that
motivated this boundary, and ROADMAP.md Phase B). It is not a general FEM
data model -- do not add ``Release``, multi-span topology, partial-span
loads, or design-check fields here just because a real solver would
eventually need them. Add them only when a new benchmark requires them.

Every entity that analysis code reads (model, member, load case, node,
support) carries an explicit ``id`` string. Nothing here is looked up by
list position, object identity, or by matching a computed value back
against a result -- see the FrameSizer audit's "fragile provenance" finding
for why that matters.

Units are not carried as a type; they are fixed by convention and named
explicitly in every field: length in millimetres, force in newtons, elastic
modulus in N/mm^2, second moment of area in mm^4. Do not pass values in any
other unit into these fields.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StructuralModelBase(BaseModel):
    """Local strict base for structural-analysis entities.

    Deliberately not ``noam.models.common.NoamBaseModel``: that base is
    documented as being for Study-hierarchy authoring records (YAML files
    under ``studies/``, reviewed and provenance-tracked as engineering
    evidence). These are plain analysis-input/-output objects with a
    different lifecycle. ``extra="forbid"`` is kept for the same reason it
    is used there -- an unrecognised field is far more likely to be a typo
    than an intentional extension.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SupportKind(str, Enum):
    """The only two support kinds this spike understands.

    Both restrain transverse translation and leave rotation free -- neither
    formula this package implements (point-load or UDL midspan moment/
    deflection) depends on which one sits at which end. The distinction
    that matters is axial: a PIN restrains axial (along-member) translation
    as well as transverse; a ROLLER restrains transverse translation only
    and leaves the member free to translate axially. The classical "simply
    supported beam" is PIN at one end, ROLLER at the other -- not PIN at
    both -- because two PINs over-restrain the member axially. This
    package does not model axial force/deformation at all (out of scope
    for these two benchmarks), so the distinction here is representational
    correctness, not a numerical input: ``ClosedFormFormulaAnalysisAdapter``
    requires exactly one of each. Fixed/spring supports are not
    represented; add them only when a benchmark needs them, per the task
    boundary (no ``Release``/``Connection`` concepts yet).
    """

    PIN = "pin"
    ROLLER = "roller"


class Node(StructuralModelBase):
    """A point along a member's axis, identified and positioned explicitly.

    ``position_mm`` is a single coordinate along the member's local axis
    (there is currently only ever one straight member, so a full 2D/3D
    coordinate system is not justified yet).
    """

    id: str = Field(min_length=1)
    position_mm: float


class Support(StructuralModelBase):
    """A support condition applied at one node.

    No default ``kind`` -- callers must state PIN or ROLLER explicitly
    rather than silently getting one by omission (see the module note on
    why the two are not interchangeable for a "simply supported" beam).
    """

    id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)
    kind: SupportKind


class Material(StructuralModelBase):
    """Analysis-only material data.

    Deliberately holds nothing but the elastic modulus this benchmark
    needs. No yield strength, design strength, partial factors, or
    code-derived reduction factors (Kh, Kdef, ...) -- those are
    design-check concerns and belong nowhere near this analysis layer (see
    ARCHITECTURE.md's analysis/design-check boundary, and the FrameSizer
    audit finding that FrameSizer's ``Element`` mutates exactly this kind of
    value as a side effect of construction, which this model must not do).
    """

    id: str = Field(min_length=1)
    elastic_modulus_n_per_mm2: float = Field(gt=0)


class SectionProperties(StructuralModelBase):
    """Analysis-only cross-section data: just the second moment of area."""

    id: str = Field(min_length=1)
    second_moment_of_area_mm4: float = Field(gt=0)


class Member(StructuralModelBase):
    """A single straight structural member between two nodes.

    Length is deliberately not stored here -- it is derived from the
    referenced nodes' positions, so a member's geometry cannot silently
    disagree with the nodes it connects.
    """

    id: str = Field(min_length=1)
    start_node_id: str = Field(min_length=1)
    end_node_id: str = Field(min_length=1)
    material_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)


class PointLoad(StructuralModelBase):
    """A single transverse point load on one member.

    ``position_mm`` is measured from the member's start node, along its
    axis. ``magnitude_n`` follows a sagging-positive convention: positive
    is transverse, in whatever direction this 1D idealisation bends under
    load (the original benchmark's load happened to be gravity-downward;
    a mullion under wind pressure bends transversely too, just not
    vertically -- this field carries no 3D direction, only a sign). Load
    *combination* factors (FrameSizer's 1.5 ULS multiplier, EN 1990
    combinations, ...) are explicitly out of scope here -- this is the
    applied action, analysed directly.
    """

    member_id: str = Field(min_length=1)
    position_mm: float = Field(ge=0)
    magnitude_n: float


class DistributedLoad(StructuralModelBase):
    """A uniform transverse load over one explicit range of a member.

    ``start_position_mm``/``end_position_mm`` are measured from the
    member's start node, the same convention ``PointLoad.position_mm``
    uses. The range is deliberately explicit rather than assumed to be the
    whole span -- ``ClosedFormFormulaAnalysisAdapter`` currently only
    accepts a range that covers the full member length, and rejects a
    partial one explicitly rather than approximating it.
    """

    member_id: str = Field(min_length=1)
    start_position_mm: float = Field(ge=0)
    end_position_mm: float
    magnitude_n_per_mm: float

    @model_validator(mode="after")
    def _check_range(self) -> "DistributedLoad":
        if self.end_position_mm <= self.start_position_mm:
            raise ValueError(
                "DistributedLoad.end_position_mm must exceed start_position_mm; "
                f"got {self.start_position_mm} to {self.end_position_mm}."
            )
        return self


class LoadCase(StructuralModelBase):
    """One named set of loads to analyse together."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    point_loads: list[PointLoad] = Field(default_factory=list)
    distributed_loads: list[DistributedLoad] = Field(default_factory=list)


class StructuralModel(StructuralModelBase):
    """The solver-neutral structural idealisation.

    A flat, id-referenced collection -- nodes/members/supports/materials/
    sections all live at the top level and refer to each other by id, the
    same relational-by-id pattern the Study hierarchy already uses
    (``Result.experiment_id`` etc.), rather than nested/embedded objects.
    """

    id: str = Field(min_length=1)
    nodes: list[Node]
    members: list[Member]
    supports: list[Support]
    materials: list[Material]
    sections: list[SectionProperties]
