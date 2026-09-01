"""Maxwell.Structural: solver-neutral model + closed-form benchmark.

Benchmark: simply-supported single-span member, one central point load.
Expected values are the standard closed-form beam-theory results (see
``src/noam/domains/maxwell/structural/analysis.py``), computed here directly
from the equations rather than asserted only as rounded display figures.
FrameSizer is not imported or referenced by any code under test -- these
numbers were independently hand-verified in
``knowledge/restricted/framesizer_audit/`` and are treated as ground truth
in their own right, not as "the FrameSizer answer".
"""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from noam.domains.maxwell.structural import (
    ClosedFormFormulaAnalysisAdapter,
    LoadCase,
    Material,
    Member,
    Node,
    PointLoad,
    SectionProperties,
    StructuralModel,
    Support,
    SupportKind,
    UnsupportedStructuralModelError,
)


def _build_benchmark(
    *,
    length_mm: float = 3000.0,
    point_load_n: float = 500.0,
    elastic_modulus_n_per_mm2: float = 70_000.0,
    second_moment_of_area_mm4: float = 1_673_000.0,
    point_load_position_mm: float | None = None,
) -> tuple[StructuralModel, LoadCase]:
    """Builds the simply-supported / central-point-load benchmark model.

    ``point_load_position_mm`` defaults to midspan; pass an off-centre value
    to build a deliberately unsupported case (see the invalid-model test).
    """
    if point_load_position_mm is None:
        point_load_position_mm = length_mm / 2.0

    model = StructuralModel(
        id="SM-BENCH-001",
        nodes=[
            Node(id="N-A", position_mm=0.0),
            Node(id="N-B", position_mm=length_mm),
        ],
        members=[
            Member(
                id="M-001",
                start_node_id="N-A",
                end_node_id="N-B",
                material_id="MAT-001",
                section_id="SEC-001",
            )
        ],
        supports=[
            # PIN + ROLLER, not PIN + PIN -- see SupportKind's docstring.
            Support(id="SUP-A", node_id="N-A", kind=SupportKind.PIN),
            Support(id="SUP-B", node_id="N-B", kind=SupportKind.ROLLER),
        ],
        materials=[
            Material(id="MAT-001", elastic_modulus_n_per_mm2=elastic_modulus_n_per_mm2)
        ],
        sections=[
            SectionProperties(id="SEC-001", second_moment_of_area_mm4=second_moment_of_area_mm4)
        ],
    )

    load_case = LoadCase(
        id="LC-BENCH-001",
        name="Benchmark central point load",
        point_loads=[
            PointLoad(
                member_id="M-001",
                position_mm=point_load_position_mm,
                magnitude_n=point_load_n,
            )
        ],
    )

    return model, load_case


class TestClosedFormSimplySupportedCentralPointLoad(unittest.TestCase):
    def test_nominal_benchmark_matches_closed_form_equations(self) -> None:
        length_mm, point_load_n = 3000.0, 500.0
        elastic_modulus, second_moment = 70_000.0, 1_673_000.0

        model, load_case = _build_benchmark(
            length_mm=length_mm,
            point_load_n=point_load_n,
            elastic_modulus_n_per_mm2=elastic_modulus,
            second_moment_of_area_mm4=second_moment,
        )

        result = ClosedFormFormulaAnalysisAdapter().analyze(model, load_case)

        expected_reaction = point_load_n / 2.0
        expected_moment = point_load_n * length_mm / 4.0
        expected_deflection = (point_load_n * length_mm**3) / (
            48.0 * elastic_modulus * second_moment
        )

        # Identity: which model/member/load case/method produced this.
        self.assertEqual(result.model_id, model.id)
        self.assertEqual(result.member_id, "M-001")
        self.assertEqual(result.load_case_id, load_case.id)
        self.assertEqual(
            result.analysis_method, "closed_form_simply_supported_central_point_load"
        )

        # Statics: sum of vertical forces is zero (R1 + R2 = P).
        self.assertEqual(len(result.reactions), 2)
        self.assertAlmostEqual(
            sum(r.force_n for r in result.reactions), point_load_n, places=9
        )
        for reaction in result.reactions:
            self.assertAlmostEqual(reaction.force_n, expected_reaction, places=9)

        # Exact analytical values, computed from the equations above --
        # not asserted only against the rounded 375,000 Nmm / 2.40 mm figures.
        self.assertAlmostEqual(result.max_bending_moment_n_mm, expected_moment, places=9)
        self.assertEqual(result.max_bending_moment_location_mm, length_mm / 2.0)
        self.assertAlmostEqual(result.max_deflection_mm, expected_deflection, places=9)
        self.assertEqual(result.max_deflection_location_mm, length_mm / 2.0)

        # Sanity check against the task's stated reference values.
        self.assertAlmostEqual(result.max_bending_moment_n_mm, 375_000.0, places=6)
        self.assertAlmostEqual(result.max_deflection_mm, 2.40, places=2)

    def test_load_scaling_doubles_reactions_moment_and_deflection(self) -> None:
        adapter = ClosedFormFormulaAnalysisAdapter()
        base_result = adapter.analyze(*_build_benchmark(point_load_n=500.0))
        doubled_result = adapter.analyze(*_build_benchmark(point_load_n=1000.0))

        self.assertAlmostEqual(
            sum(r.force_n for r in doubled_result.reactions),
            2 * sum(r.force_n for r in base_result.reactions),
            places=9,
        )
        self.assertAlmostEqual(
            doubled_result.max_bending_moment_n_mm,
            2 * base_result.max_bending_moment_n_mm,
            places=9,
        )
        self.assertAlmostEqual(
            doubled_result.max_deflection_mm,
            2 * base_result.max_deflection_mm,
            places=9,
        )

    def test_stiffness_scaling_halves_deflection_leaves_statics_unchanged(self) -> None:
        adapter = ClosedFormFormulaAnalysisAdapter()
        base_result = adapter.analyze(*_build_benchmark(elastic_modulus_n_per_mm2=70_000.0))
        stiffer_result = adapter.analyze(
            *_build_benchmark(elastic_modulus_n_per_mm2=140_000.0)
        )

        self.assertAlmostEqual(
            sum(r.force_n for r in stiffer_result.reactions),
            sum(r.force_n for r in base_result.reactions),
            places=9,
        )
        self.assertAlmostEqual(
            stiffer_result.max_bending_moment_n_mm,
            base_result.max_bending_moment_n_mm,
            places=9,
        )
        self.assertAlmostEqual(
            stiffer_result.max_deflection_mm,
            0.5 * base_result.max_deflection_mm,
            places=9,
        )

    def test_point_load_not_at_midspan_is_rejected_explicitly(self) -> None:
        # 3000 mm span, point load at 1000 mm -- a real, valid engineering
        # case, just not the one this adapter supports.
        model, load_case = _build_benchmark(point_load_position_mm=1000.0)

        with self.assertRaises(UnsupportedStructuralModelError):
            ClosedFormFormulaAnalysisAdapter().analyze(model, load_case)

    def test_pin_pin_is_rejected_not_treated_as_simply_supported(self) -> None:
        # The classical "simply supported beam" is PIN + ROLLER, not PIN +
        # PIN (two PINs over-restrain the member axially) -- see
        # SupportKind's docstring. The adapter must say so explicitly
        # rather than silently accepting PIN + PIN as equivalent.
        model, load_case = _build_benchmark()
        model = model.model_copy(
            update={
                "supports": [
                    Support(id="SUP-A", node_id="N-A", kind=SupportKind.PIN),
                    Support(id="SUP-B", node_id="N-B", kind=SupportKind.PIN),
                ]
            }
        )

        with self.assertRaises(UnsupportedStructuralModelError):
            ClosedFormFormulaAnalysisAdapter().analyze(model, load_case)

    def test_non_positive_elastic_modulus_is_rejected_at_construction(self) -> None:
        with self.assertRaises(ValidationError):
            Material(id="MAT-BAD", elastic_modulus_n_per_mm2=0.0)
        with self.assertRaises(ValidationError):
            Material(id="MAT-BAD", elastic_modulus_n_per_mm2=-70_000.0)

    def test_non_positive_second_moment_of_area_is_rejected_at_construction(self) -> None:
        with self.assertRaises(ValidationError):
            SectionProperties(id="SEC-BAD", second_moment_of_area_mm4=0.0)
        with self.assertRaises(ValidationError):
            SectionProperties(id="SEC-BAD", second_moment_of_area_mm4=-1_673_000.0)

    def test_zero_length_member_is_rejected(self) -> None:
        # Both nodes at the same position -- a real object shape, but not
        # a member the adapter can analyse.
        model, load_case = _build_benchmark(length_mm=3000.0)
        model = model.model_copy(
            update={
                "nodes": [
                    Node(id="N-A", position_mm=0.0),
                    Node(id="N-B", position_mm=0.0),
                ]
            }
        )

        with self.assertRaises(UnsupportedStructuralModelError):
            ClosedFormFormulaAnalysisAdapter().analyze(model, load_case)


if __name__ == "__main__":
    unittest.main()
