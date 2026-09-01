"""Closed-form analysis for exactly two supported structural cases.

Both supported cases share the same structural idealisation: a single
straight member, PIN at one end and ROLLER at the other (the classical
"simply supported beam" -- see ``SupportKind`` in ``model.py`` for why PIN
at both ends is not the same thing). They differ only in the load:

    1. one transverse point load at midspan;
    2. one transverse uniformly distributed load over the full span.

This is deliberately not a general beam-analysis engine -- no stiffness
matrix, no multi-span, no partial-span distributed loads, no other support
kind. A model/load case that does not match one of these two exact shapes
is rejected explicitly (``UnsupportedStructuralModelError``), never
silently approximated.

This module calculates structural response only. It does not decide
whether a member is adequate for the load -- see ARCHITECTURE.md's
analysis/design-check boundary. Nothing here applies a partial factor, a
load combination, or a deflection limit; the load in the ``LoadCase`` is
analysed exactly as given.

The closed-form equations implemented are the standard simply-supported-
beam results (see e.g. Roark's Formulas for Stress and Strain):

    central point load P:
        R1 = R2 = P / 2
        M_max = P * L / 4                      (at midspan)
        delta_max = P * L**3 / (48 * E * I)     (at midspan)

    full-span UDL w:
        R1 = R2 = w * L / 2
        M_max = w * L**2 / 8                    (at midspan)
        delta_max = 5 * w * L**4 / (384 * E * I)  (at midspan)

The point-load case was chosen as the first Maxwell benchmark because it is
the one FrameSizer load case (``Analysis.ULSCheck.LC5`` / ``SLSCheck.LC5``,
the "access load" case) that matches a textbook closed form exactly -- see
``knowledge/restricted/framesizer_audit/``. The UDL case is the standard
idealisation for a wind-loaded mullion (S001's actual use case -- see
``idealisation.py``). Neither reproduces FrameSizer's own 1.5 ULS factor:
that belongs to a future load-combination/design-check layer, not here.
"""

from __future__ import annotations

from noam.domains.maxwell.structural.model import (
    DistributedLoad,
    LoadCase,
    Material,
    Node,
    PointLoad,
    SectionProperties,
    StructuralModel,
    Support,
    SupportKind,
)
from noam.domains.maxwell.structural.results import AnalysisResult, Reaction

ANALYSIS_METHOD_CENTRAL_POINT_LOAD = "closed_form_simply_supported_central_point_load"
ANALYSIS_METHOD_FULL_SPAN_UDL = "closed_form_simply_supported_full_span_udl"

# Absolute tolerance, in mm, for treating a load position/range boundary as
# matching an expected location (midspan, or a member end). Inputs in this
# spike are exact literals, so this only needs to absorb ordinary
# floating-point accumulation, not measurement uncertainty.
_POSITION_TOLERANCE_MM = 1e-6


class UnsupportedStructuralModelError(ValueError):
    """Raised when a model/load case does not match a supported case.

    This is a plain, explicit failure -- there is no fallback, approximation,
    or partial result. Callers must fix the model or load case, not catch
    this and proceed.
    """


class ClosedFormFormulaAnalysisAdapter:
    """Analyses one of two supported structural cases using closed-form beam formulas."""

    def analyze(self, model: StructuralModel, load_case: LoadCase) -> AnalysisResult:
        member = self._require_single_member(model)
        start_node, end_node = self._require_two_end_nodes(model, member)
        length_mm = self._require_positive_length(start_node, end_node)
        self._require_pin_and_roller_supports_at_both_ends(model, member, start_node, end_node)
        material = self._resolve(model.materials, member.material_id, "Material")
        section = self._resolve(model.sections, member.section_id, "SectionProperties")
        supports = self._supports_for(model, member)

        has_point_loads = len(load_case.point_loads) > 0
        has_distributed_loads = len(load_case.distributed_loads) > 0

        if has_point_loads and has_distributed_loads:
            raise UnsupportedStructuralModelError(
                "ClosedFormFormulaAnalysisAdapter supports a load case with "
                "either point loads or a distributed load, not both."
            )

        if has_point_loads:
            point_load = self._require_single_central_point_load(load_case, member, length_mm)
            return self._solve_central_point_load(
                model=model,
                member_id=member.id,
                load_case_id=load_case.id,
                length_mm=length_mm,
                supports=supports,
                material=material,
                section=section,
                point_load_n=point_load.magnitude_n,
            )

        if has_distributed_loads:
            udl = self._require_single_full_span_udl(load_case, member, length_mm)
            return self._solve_full_span_udl(
                model=model,
                member_id=member.id,
                load_case_id=load_case.id,
                length_mm=length_mm,
                supports=supports,
                material=material,
                section=section,
                udl_n_per_mm=udl.magnitude_n_per_mm,
            )

        raise UnsupportedStructuralModelError(
            "Load case has no point loads or distributed loads; nothing to analyse."
        )

    # ---- model validation -------------------------------------------------

    @staticmethod
    def _require_single_member(model: StructuralModel):
        if len(model.members) != 1:
            raise UnsupportedStructuralModelError(
                "ClosedFormFormulaAnalysisAdapter supports exactly one member "
                f"per model; got {len(model.members)}."
            )
        return model.members[0]

    @staticmethod
    def _require_two_end_nodes(model: StructuralModel, member) -> tuple[Node, Node]:
        nodes_by_id = {node.id: node for node in model.nodes}
        if len(nodes_by_id) != len(model.nodes):
            raise UnsupportedStructuralModelError("Duplicate node id in model.nodes.")
        if set(nodes_by_id) != {member.start_node_id, member.end_node_id}:
            raise UnsupportedStructuralModelError(
                "Model must contain exactly the member's two end nodes "
                f"({member.start_node_id!r}, {member.end_node_id!r}); "
                f"got {sorted(nodes_by_id)!r}."
            )
        return nodes_by_id[member.start_node_id], nodes_by_id[member.end_node_id]

    @staticmethod
    def _require_positive_length(start_node: Node, end_node: Node) -> float:
        length_mm = end_node.position_mm - start_node.position_mm
        if length_mm <= 0:
            raise UnsupportedStructuralModelError(
                "Member length must be positive (end_node.position_mm must "
                f"exceed start_node.position_mm); got {length_mm} mm."
            )
        return length_mm

    @classmethod
    def _require_pin_and_roller_supports_at_both_ends(
        cls, model: StructuralModel, member, start_node: Node, end_node: Node
    ) -> None:
        supports = cls._supports_for(model, member)
        supports_by_node = {s.node_id: s for s in supports}
        if len(supports) != 2 or len(supports_by_node) != 2:
            raise UnsupportedStructuralModelError(
                "Model must define exactly one support at each of the "
                f"member's two end nodes; got {len(supports)} support(s)."
            )
        for node in (start_node, end_node):
            if node.id not in supports_by_node:
                raise UnsupportedStructuralModelError(
                    f"No support is defined at node {node.id!r}."
                )
        kinds = sorted(s.kind.value for s in supports)
        expected = sorted([SupportKind.PIN.value, SupportKind.ROLLER.value])
        if kinds != expected:
            raise UnsupportedStructuralModelError(
                "ClosedFormFormulaAnalysisAdapter requires one PIN and one "
                "ROLLER support (the standard 'simply supported' "
                f"idealisation, not PIN+PIN); got {kinds!r}."
            )

    @staticmethod
    def _supports_for(model: StructuralModel, member) -> list[Support]:
        end_node_ids = {member.start_node_id, member.end_node_id}
        return [s for s in model.supports if s.node_id in end_node_ids]

    @staticmethod
    def _resolve(items, item_id: str, label: str):
        for item in items:
            if item.id == item_id:
                return item
        raise UnsupportedStructuralModelError(f"{label} {item_id!r} not found in model.")

    # ---- load validation ---------------------------------------------------

    @classmethod
    def _require_single_central_point_load(
        cls, load_case: LoadCase, member, length_mm: float
    ) -> PointLoad:
        loads_on_member = [pl for pl in load_case.point_loads if pl.member_id == member.id]
        if len(load_case.point_loads) != 1 or len(loads_on_member) != 1:
            raise UnsupportedStructuralModelError(
                "ClosedFormFormulaAnalysisAdapter supports exactly one point "
                f"load on the member; got {len(load_case.point_loads)} in the "
                "load case."
            )
        point_load = loads_on_member[0]
        midspan_mm = length_mm / 2.0
        if abs(point_load.position_mm - midspan_mm) > _POSITION_TOLERANCE_MM:
            raise UnsupportedStructuralModelError(
                "ClosedFormFormulaAnalysisAdapter only supports a point load "
                f"at midspan ({midspan_mm} mm from the start node); got a "
                f"point load at {point_load.position_mm} mm."
            )
        return point_load

    @classmethod
    def _require_single_full_span_udl(
        cls, load_case: LoadCase, member, length_mm: float
    ) -> DistributedLoad:
        loads_on_member = [
            dl for dl in load_case.distributed_loads if dl.member_id == member.id
        ]
        if len(load_case.distributed_loads) != 1 or len(loads_on_member) != 1:
            raise UnsupportedStructuralModelError(
                "ClosedFormFormulaAnalysisAdapter supports exactly one "
                "distributed load on the member; got "
                f"{len(load_case.distributed_loads)} in the load case."
            )
        udl = loads_on_member[0]
        starts_at_zero = abs(udl.start_position_mm - 0.0) <= _POSITION_TOLERANCE_MM
        ends_at_span = abs(udl.end_position_mm - length_mm) <= _POSITION_TOLERANCE_MM
        if not (starts_at_zero and ends_at_span):
            raise UnsupportedStructuralModelError(
                "ClosedFormFormulaAnalysisAdapter only supports a distributed "
                f"load spanning the full member length (0 to {length_mm} mm); "
                f"got {udl.start_position_mm} to {udl.end_position_mm} mm."
            )
        return udl

    # ---- closed-form solutions ---------------------------------------------

    @staticmethod
    def _reactions(supports: list[Support], reaction_n: float) -> list[Reaction]:
        return [
            Reaction(node_id=support.node_id, support_id=support.id, force_n=reaction_n)
            for support in sorted(supports, key=lambda s: s.node_id)
        ]

    @classmethod
    def _solve_central_point_load(
        cls,
        *,
        model: StructuralModel,
        member_id: str,
        load_case_id: str,
        length_mm: float,
        supports: list[Support],
        material: Material,
        section: SectionProperties,
        point_load_n: float,
    ) -> AnalysisResult:
        midspan_mm = length_mm / 2.0
        max_moment_n_mm = point_load_n * length_mm / 4.0
        max_deflection_mm = (point_load_n * length_mm**3) / (
            48.0 * material.elastic_modulus_n_per_mm2 * section.second_moment_of_area_mm4
        )

        return AnalysisResult(
            model_id=model.id,
            member_id=member_id,
            load_case_id=load_case_id,
            analysis_method=ANALYSIS_METHOD_CENTRAL_POINT_LOAD,
            reactions=cls._reactions(supports, point_load_n / 2.0),
            max_bending_moment_n_mm=max_moment_n_mm,
            max_bending_moment_location_mm=midspan_mm,
            max_deflection_mm=max_deflection_mm,
            max_deflection_location_mm=midspan_mm,
        )

    @classmethod
    def _solve_full_span_udl(
        cls,
        *,
        model: StructuralModel,
        member_id: str,
        load_case_id: str,
        length_mm: float,
        supports: list[Support],
        material: Material,
        section: SectionProperties,
        udl_n_per_mm: float,
    ) -> AnalysisResult:
        total_load_n = udl_n_per_mm * length_mm
        midspan_mm = length_mm / 2.0
        max_moment_n_mm = udl_n_per_mm * length_mm**2 / 8.0
        max_deflection_mm = (5.0 * udl_n_per_mm * length_mm**4) / (
            384.0 * material.elastic_modulus_n_per_mm2 * section.second_moment_of_area_mm4
        )

        return AnalysisResult(
            model_id=model.id,
            member_id=member_id,
            load_case_id=load_case_id,
            analysis_method=ANALYSIS_METHOD_FULL_SPAN_UDL,
            reactions=cls._reactions(supports, total_load_n / 2.0),
            max_bending_moment_n_mm=max_moment_n_mm,
            max_bending_moment_location_mm=midspan_mm,
            max_deflection_mm=max_deflection_mm,
            max_deflection_location_mm=midspan_mm,
        )
