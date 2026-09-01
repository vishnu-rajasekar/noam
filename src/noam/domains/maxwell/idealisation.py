"""Facade -> structural idealisation for one S001 curtain-wall unit.

This is the middle layer of the target architecture:

    physical facade model  ->  structural idealisation  ->  analysis model
                                        (this module)

It is the only module in ``noam.domains.maxwell`` allowed to import from
both ``facade/`` and ``structural/`` -- that is its entire job: translate
physical facade entities into the solver-neutral structural vocabulary,
under one explicit, named modelling hypothesis. It performs no analysis
itself (no reactions, moments, or deflections are calculated here); see
``structural.analysis.ClosedFormFormulaAnalysisAdapter`` for that. It is
deliberately not called a "solver adapter" for the same reason.

Modelling hypothesis implemented (S001-specific, not a universal curtain-
wall truth -- see ``MullionIdealisation``):

    Each vertical mullion is idealised independently as a prismatic,
    simply-supported (PIN + ROLLER) beam spanning between its top and
    bottom support locations. For this slice, "support locations" are
    taken to coincide with the physical mullion's own end points (i.e. the
    sill and head transom intersections) -- no separate bracket/anchor
    offset is modelled yet.

Scope for this task: only the left mullion can be idealised
(``build_left_mullion_model``); the physical ``CurtainWallUnit`` still
represents all four perimeter members, but analysing more than one of them
is a later task's job, not this one's.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from noam.domains.maxwell.facade.loads import FacadePressureLoad
from noam.domains.maxwell.facade.unit import CurtainWallUnit, FacadeMember
from noam.domains.maxwell.structural.model import (
    DistributedLoad,
    Material,
    Member,
    Node,
    SectionProperties,
    StructuralModel,
    StructuralModelBase,
    Support,
    SupportKind,
)


class MullionIdealisation(str, Enum):
    """The one modelling hypothesis this builder currently implements.

    This is an S001-specific engineering assumption, not a claim that
    every mullion in every curtain wall is always simply supported.
    Adding a second value here (e.g. continuous-over-transom, or fixed-
    base) is a future task's decision -- ``CurtainWallStructuralIdealisationBuilder``
    rejects any value it does not implement rather than silently
    defaulting to this one.
    """

    SIMPLY_SUPPORTED_INDEPENDENT_SPAN = "simply_supported_independent_span"


class MullionIdealisationResult(StructuralModelBase):
    """The structural model produced for one physical mullion, plus its provenance.

    ``source_facade_member_id``/``analysis_member_id`` make the physical ->
    analytical identity mapping explicit and queryable -- never
    reconstructed later by position or by matching a computed value.
    """

    structural_model: StructuralModel
    idealisation: MullionIdealisation
    source_facade_member_id: str = Field(min_length=1)
    analysis_member_id: str = Field(min_length=1)


class TributaryLineLoad(StructuralModelBase):
    """Provenance record for one facade-pressure -> line-load conversion.

    Every id involved, and the tributary width used, are stored explicitly
    -- see ``derive_mullion_line_load``. This is not itself a structural
    load; ``to_full_span_distributed_load`` turns it into one.
    """

    id: str = Field(min_length=1)
    source_pressure_load_id: str = Field(min_length=1)
    source_facade_member_id: str = Field(min_length=1)
    target_analysis_member_id: str = Field(min_length=1)
    tributary_width_mm: float = Field(gt=0)
    magnitude_n_per_mm: float


class CurtainWallStructuralIdealisationBuilder:
    """Translates one physical facade member into a solver-neutral ``StructuralModel``.

    A mapper, not a solver adapter -- it does no analysis. See the module
    docstring for the one modelling hypothesis it implements.
    """

    def build_left_mullion_model(
        self,
        unit: CurtainWallUnit,
        *,
        model_id: str,
        member_id: str,
        bottom_node_id: str,
        top_node_id: str,
        bottom_support_id: str,
        top_support_id: str,
        material: Material,
        section: SectionProperties,
        idealisation: MullionIdealisation = (
            MullionIdealisation.SIMPLY_SUPPORTED_INDEPENDENT_SPAN
        ),
    ) -> MullionIdealisationResult:
        if idealisation is not MullionIdealisation.SIMPLY_SUPPORTED_INDEPENDENT_SPAN:
            raise NotImplementedError(
                "CurtainWallStructuralIdealisationBuilder does not implement "
                f"{idealisation!r}; only SIMPLY_SUPPORTED_INDEPENDENT_SPAN "
                "exists for this S001 slice."
            )

        facade_member = unit.left_mullion
        span_mm = self._facade_member_length_mm(facade_member)

        bottom_node = Node(id=bottom_node_id, position_mm=0.0)
        top_node = Node(id=top_node_id, position_mm=span_mm)

        member = Member(
            id=member_id,
            start_node_id=bottom_node.id,
            end_node_id=top_node.id,
            material_id=material.id,
            section_id=section.id,
        )

        # PIN at the sill, ROLLER at the head -- the classical "simply
        # supported" idealisation (see SupportKind's docstring); the choice
        # of which end is which is arbitrary for the closed-form formulas,
        # fixed here for a consistent, documented convention.
        supports = [
            Support(id=bottom_support_id, node_id=bottom_node.id, kind=SupportKind.PIN),
            Support(id=top_support_id, node_id=top_node.id, kind=SupportKind.ROLLER),
        ]

        structural_model = StructuralModel(
            id=model_id,
            nodes=[bottom_node, top_node],
            members=[member],
            supports=supports,
            materials=[material],
            sections=[section],
        )

        return MullionIdealisationResult(
            structural_model=structural_model,
            idealisation=idealisation,
            source_facade_member_id=facade_member.id,
            analysis_member_id=member.id,
        )

    @staticmethod
    def _facade_member_length_mm(facade_member: FacadeMember) -> float:
        dx = facade_member.end_point.x_mm - facade_member.start_point.x_mm
        dy = facade_member.end_point.y_mm - facade_member.start_point.y_mm
        dz = facade_member.end_point.z_mm - facade_member.start_point.z_mm
        return (dx**2 + dy**2 + dz**2) ** 0.5


def derive_mullion_line_load(
    *,
    line_load_id: str,
    pressure: FacadePressureLoad,
    facade_member: FacadeMember,
    target_analysis_member_id: str,
    tributary_width_mm: float,
) -> TributaryLineLoad:
    """Converts a facade pressure into a line load on one analytical member.

        line_load [N/mm] = pressure [N/mm^2] x tributary_width [mm]

    the one transformation this function performs, computed explicitly so
    it is never buried inside a solver formula (see the FrameSizer audit's
    "fragile provenance" finding for why that matters). ``pressure.direction``
    is not yet applied as a sign here -- see ``PressureDirection``'s
    docstring.
    """
    magnitude_n_per_mm = pressure.pressure_n_per_mm2 * tributary_width_mm
    return TributaryLineLoad(
        id=line_load_id,
        source_pressure_load_id=pressure.id,
        source_facade_member_id=facade_member.id,
        target_analysis_member_id=target_analysis_member_id,
        tributary_width_mm=tributary_width_mm,
        magnitude_n_per_mm=magnitude_n_per_mm,
    )


def to_full_span_distributed_load(
    line_load: TributaryLineLoad, *, span_mm: float
) -> DistributedLoad:
    """Turns a derived line load into the full-span structural UDL it represents."""
    return DistributedLoad(
        member_id=line_load.target_analysis_member_id,
        start_position_mm=0.0,
        end_position_mm=span_mm,
        magnitude_n_per_mm=line_load.magnitude_n_per_mm,
    )
