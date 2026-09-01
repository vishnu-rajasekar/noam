"""S001 vertical slice: facade geometry -> structural idealisation -> analysis.

Fixture (an engineering-model fixture only, not a contractual S001 design
load -- see the task this was built against):

    unit width = 1500 mm, unit height = 3000 mm
    left mullion: E = 70,000 N/mm^2, I = 1,673,000 mm^4
    facade pressure: p = 0.002 N/mm^2 (2.0 kPa)
    tributary width: 750 mm  ->  w = p * tributary_width = 1.5 N/mm

No FrameSizer or Rhino/Grasshopper import anywhere in this file or the
code under test.
"""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from noam.domains.maxwell.facade import (
    CurtainWallUnit,
    FacadeMember,
    FacadePressureLoad,
    MemberRole,
    Point,
    build_rectangular_unit,
)
from noam.domains.maxwell.idealisation import (
    CurtainWallStructuralIdealisationBuilder,
    MullionIdealisation,
    derive_mullion_line_load,
    to_full_span_distributed_load,
)
from noam.domains.maxwell.structural import (
    ANALYSIS_METHOD_FULL_SPAN_UDL,
    ClosedFormFormulaAnalysisAdapter,
    LoadCase,
    Material,
    SectionProperties,
    SupportKind,
    UnsupportedStructuralModelError,
)

UNIT_WIDTH_MM = 1500.0
UNIT_HEIGHT_MM = 3000.0
ELASTIC_MODULUS_N_PER_MM2 = 70_000.0
SECOND_MOMENT_MM4 = 1_673_000.0
PRESSURE_N_PER_MM2 = 0.002  # 2.0 kPa
TRIBUTARY_WIDTH_MM = 750.0


def _build_unit() -> CurtainWallUnit:
    return build_rectangular_unit(
        id="CW_UNIT_001",
        width_mm=UNIT_WIDTH_MM,
        height_mm=UNIT_HEIGHT_MM,
        left_mullion_id="MULLION_LEFT_001",
        right_mullion_id="MULLION_RIGHT_001",
        head_transom_id="TRANSOM_HEAD_001",
        sill_transom_id="TRANSOM_SILL_001",
    )


def _build_full_pipeline():
    """Runs the whole facade -> structural -> load -> analysis pipeline once.

    Returns (unit, idealisation_result, pressure, line_load, load_case, result).
    """
    unit = _build_unit()
    material = Material(id="MAT_001", elastic_modulus_n_per_mm2=ELASTIC_MODULUS_N_PER_MM2)
    section = SectionProperties(id="SEC_001", second_moment_of_area_mm4=SECOND_MOMENT_MM4)

    builder = CurtainWallStructuralIdealisationBuilder()
    idealisation_result = builder.build_left_mullion_model(
        unit,
        model_id="SM_001",
        member_id="AM_001",
        bottom_node_id="N_BOTTOM_001",
        top_node_id="N_TOP_001",
        bottom_support_id="SUP_BOTTOM_001",
        top_support_id="SUP_TOP_001",
        material=material,
        section=section,
    )

    pressure = FacadePressureLoad(
        id="WIND_FIXTURE_001",
        pressure_n_per_mm2=PRESSURE_N_PER_MM2,
        loaded_width_mm=UNIT_WIDTH_MM,
    )
    line_load = derive_mullion_line_load(
        line_load_id="DL_001",
        pressure=pressure,
        facade_member=unit.left_mullion,
        target_analysis_member_id=idealisation_result.analysis_member_id,
        tributary_width_mm=TRIBUTARY_WIDTH_MM,
    )
    distributed_load = to_full_span_distributed_load(line_load, span_mm=UNIT_HEIGHT_MM)
    load_case = LoadCase(
        id="LC_001", name="Wind UDL on left mullion", distributed_loads=[distributed_load]
    )

    result = ClosedFormFormulaAnalysisAdapter().analyze(
        idealisation_result.structural_model, load_case
    )

    return unit, idealisation_result, pressure, line_load, load_case, result


class TestFacadeGeometry(unittest.TestCase):
    def test_unit_width_and_height(self) -> None:
        unit = _build_unit()
        self.assertEqual(unit.width_mm, UNIT_WIDTH_MM)
        self.assertEqual(unit.height_mm, UNIT_HEIGHT_MM)

    def test_member_roles_are_not_swapped(self) -> None:
        unit = _build_unit()
        self.assertEqual(unit.left_mullion.role, MemberRole.LEFT_MULLION)
        self.assertEqual(unit.right_mullion.role, MemberRole.RIGHT_MULLION)
        self.assertEqual(unit.head_transom.role, MemberRole.HEAD_TRANSOM)
        self.assertEqual(unit.sill_transom.role, MemberRole.SILL_TRANSOM)

    def test_mullion_and_transom_endpoints_follow_the_documented_convention(self) -> None:
        unit = _build_unit()

        # Origin = bottom-left corner; X across width, Y up the facade.
        self.assertEqual(unit.left_mullion.start_point, Point(x_mm=0.0, y_mm=0.0))
        self.assertEqual(unit.left_mullion.end_point, Point(x_mm=0.0, y_mm=UNIT_HEIGHT_MM))

        self.assertEqual(unit.right_mullion.start_point, Point(x_mm=UNIT_WIDTH_MM, y_mm=0.0))
        self.assertEqual(
            unit.right_mullion.end_point, Point(x_mm=UNIT_WIDTH_MM, y_mm=UNIT_HEIGHT_MM)
        )

        self.assertEqual(
            unit.head_transom.start_point, Point(x_mm=0.0, y_mm=UNIT_HEIGHT_MM)
        )
        self.assertEqual(
            unit.head_transom.end_point, Point(x_mm=UNIT_WIDTH_MM, y_mm=UNIT_HEIGHT_MM)
        )

        self.assertEqual(unit.sill_transom.start_point, Point(x_mm=0.0, y_mm=0.0))
        self.assertEqual(unit.sill_transom.end_point, Point(x_mm=UNIT_WIDTH_MM, y_mm=0.0))

    def test_a_member_with_a_mismatched_role_is_rejected_at_construction(self) -> None:
        unit = _build_unit()
        swapped_left_mullion = FacadeMember(
            id="MULLION_LEFT_001",
            role=MemberRole.RIGHT_MULLION,  # wrong on purpose
            start_point=unit.left_mullion.start_point,
            end_point=unit.left_mullion.end_point,
        )

        with self.assertRaises(ValidationError):
            CurtainWallUnit(
                id="CW_UNIT_BAD",
                width_mm=UNIT_WIDTH_MM,
                height_mm=UNIT_HEIGHT_MM,
                left_mullion=swapped_left_mullion,
                right_mullion=unit.right_mullion,
                head_transom=unit.head_transom,
                sill_transom=unit.sill_transom,
            )


class TestPhysicalToAnalyticalIdentity(unittest.TestCase):
    def test_left_mullion_maps_to_the_expected_analytical_member(self) -> None:
        unit, idealisation_result, _pressure, _line_load, _load_case, _result = (
            _build_full_pipeline()
        )

        self.assertEqual(idealisation_result.source_facade_member_id, unit.left_mullion.id)
        self.assertEqual(idealisation_result.analysis_member_id, "AM_001")
        self.assertEqual(idealisation_result.structural_model.members[0].id, "AM_001")
        self.assertEqual(
            idealisation_result.idealisation,
            MullionIdealisation.SIMPLY_SUPPORTED_INDEPENDENT_SPAN,
        )

    def test_result_traces_back_through_load_case_and_member(self) -> None:
        _unit, idealisation_result, _pressure, _line_load, load_case, result = (
            _build_full_pipeline()
        )

        self.assertEqual(result.model_id, idealisation_result.structural_model.id)
        self.assertEqual(result.member_id, idealisation_result.analysis_member_id)
        self.assertEqual(result.load_case_id, load_case.id)
        self.assertEqual(result.analysis_method, ANALYSIS_METHOD_FULL_SPAN_UDL)


class TestTributaryConversion(unittest.TestCase):
    def test_line_load_equals_pressure_times_tributary_width(self) -> None:
        unit, idealisation_result, pressure, line_load, _load_case, _result = (
            _build_full_pipeline()
        )

        self.assertEqual(
            line_load.magnitude_n_per_mm, PRESSURE_N_PER_MM2 * TRIBUTARY_WIDTH_MM
        )
        self.assertAlmostEqual(line_load.magnitude_n_per_mm, 1.5, places=9)

        # Provenance: which pressure, which physical member, which
        # analytical member, and what tributary width -- all explicit.
        self.assertEqual(line_load.source_pressure_load_id, pressure.id)
        self.assertEqual(line_load.source_facade_member_id, unit.left_mullion.id)
        self.assertEqual(
            line_load.target_analysis_member_id, idealisation_result.analysis_member_id
        )
        self.assertEqual(line_load.tributary_width_mm, TRIBUTARY_WIDTH_MM)


class TestSupportSemantics(unittest.TestCase):
    def test_analytical_member_has_pin_and_roller_supports(self) -> None:
        _unit, idealisation_result, *_rest = _build_full_pipeline()

        kinds = sorted(s.kind for s in idealisation_result.structural_model.supports)
        self.assertEqual(kinds, sorted([SupportKind.PIN, SupportKind.ROLLER]))


class TestFullSpanUdlAnalysis(unittest.TestCase):
    def test_reactions_moment_and_deflection_match_closed_form_equations(self) -> None:
        *_rest, result = _build_full_pipeline()

        w = PRESSURE_N_PER_MM2 * TRIBUTARY_WIDTH_MM  # N/mm
        length_mm = UNIT_HEIGHT_MM
        expected_total_load_n = w * length_mm
        expected_reaction_n = w * length_mm / 2.0
        expected_moment_n_mm = w * length_mm**2 / 8.0
        expected_deflection_mm = (5.0 * w * length_mm**4) / (
            384.0 * ELASTIC_MODULUS_N_PER_MM2 * SECOND_MOMENT_MM4
        )

        # Sum of vertical forces equals the total applied UDL.
        self.assertEqual(len(result.reactions), 2)
        self.assertAlmostEqual(
            sum(r.force_n for r in result.reactions), expected_total_load_n, places=9
        )
        for reaction in result.reactions:
            self.assertAlmostEqual(reaction.force_n, expected_reaction_n, places=9)

        self.assertAlmostEqual(result.max_bending_moment_n_mm, expected_moment_n_mm, places=9)
        self.assertEqual(result.max_bending_moment_location_mm, length_mm / 2.0)
        self.assertAlmostEqual(result.max_deflection_mm, expected_deflection_mm, places=9)
        self.assertEqual(result.max_deflection_location_mm, length_mm / 2.0)


class TestUnsupportedModelIsRejectedExplicitly(unittest.TestCase):
    def test_partial_span_udl_is_rejected(self) -> None:
        unit = _build_unit()
        material = Material(id="MAT_001", elastic_modulus_n_per_mm2=ELASTIC_MODULUS_N_PER_MM2)
        section = SectionProperties(id="SEC_001", second_moment_of_area_mm4=SECOND_MOMENT_MM4)
        idealisation_result = CurtainWallStructuralIdealisationBuilder().build_left_mullion_model(
            unit,
            model_id="SM_BAD",
            member_id="AM_BAD",
            bottom_node_id="N_BOTTOM_BAD",
            top_node_id="N_TOP_BAD",
            bottom_support_id="SUP_BOTTOM_BAD",
            top_support_id="SUP_TOP_BAD",
            material=material,
            section=section,
        )

        pressure = FacadePressureLoad(
            id="WIND_FIXTURE_BAD",
            pressure_n_per_mm2=PRESSURE_N_PER_MM2,
            loaded_width_mm=UNIT_WIDTH_MM,
        )
        line_load = derive_mullion_line_load(
            line_load_id="DL_BAD",
            pressure=pressure,
            facade_member=unit.left_mullion,
            target_analysis_member_id=idealisation_result.analysis_member_id,
            tributary_width_mm=TRIBUTARY_WIDTH_MM,
        )
        # Only the bottom half of the span -- a real, valid engineering
        # case, just not the one this adapter supports.
        partial_span_load = to_full_span_distributed_load(
            line_load, span_mm=UNIT_HEIGHT_MM / 2.0
        )
        load_case = LoadCase(
            id="LC_BAD", name="Partial-span UDL", distributed_loads=[partial_span_load]
        )

        with self.assertRaises(UnsupportedStructuralModelError):
            ClosedFormFormulaAnalysisAdapter().analyze(
                idealisation_result.structural_model, load_case
            )

    def test_unimplemented_modelling_hypothesis_is_rejected(self) -> None:
        unit = _build_unit()
        material = Material(id="MAT_001", elastic_modulus_n_per_mm2=ELASTIC_MODULUS_N_PER_MM2)
        section = SectionProperties(id="SEC_001", second_moment_of_area_mm4=SECOND_MOMENT_MM4)

        with self.assertRaises(NotImplementedError):
            CurtainWallStructuralIdealisationBuilder().build_left_mullion_model(
                unit,
                model_id="SM_BAD",
                member_id="AM_BAD",
                bottom_node_id="N_BOTTOM_BAD",
                top_node_id="N_TOP_BAD",
                bottom_support_id="SUP_BOTTOM_BAD",
                top_support_id="SUP_TOP_BAD",
                material=material,
                section=section,
                idealisation="some_future_hypothesis",  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
