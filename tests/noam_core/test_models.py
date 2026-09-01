import unittest

from pydantic import ValidationError

from noam.models import (
    Capability,
    Evidence,
    Experiment,
    Insight,
    ModelHypothesis,
    Precedent,
    Requirement,
    Result,
    RuleCard,
    Study,
)
from noam.models.common import Confidentiality, Domain, ProjectStage, StudyStatus


class TestStudy(unittest.TestCase):
    def test_creates_with_minimum_fields(self) -> None:
        study = Study(
            id="S001",
            title="Airport Unitised Curtain Wall",
            domain=Domain.MAXWELL,
            engineering_question="What governs mullion sizing?",
            decision_required="Preliminary mullion/transom sizing strategy",
        )
        self.assertEqual(study.status, StudyStatus.DRAFT)
        self.assertEqual(study.project_stage, ProjectStage.UNKNOWN)
        self.assertEqual(study.confidentiality, Confidentiality.INTERNAL)

    def test_accepts_explicit_stage_and_confidentiality(self) -> None:
        study = Study(
            id="S001",
            title="Airport Unitised Curtain Wall",
            domain=Domain.MAXWELL,
            project_stage=ProjectStage.STAGE_2,
            confidentiality=Confidentiality.RESTRICTED,
            engineering_question="q",
            decision_required="d",
        )
        self.assertEqual(study.project_stage.value, "2")
        self.assertEqual(study.confidentiality.value, "restricted")

    def test_rejects_invalid_id(self) -> None:
        with self.assertRaises(ValidationError):
            Study(
                id="airport-cw",
                title="x",
                domain=Domain.MAXWELL,
                engineering_question="q",
                decision_required="d",
            )

    def test_rejects_invalid_domain(self) -> None:
        with self.assertRaises(ValidationError):
            Study(
                id="S001",
                title="x",
                domain="not-a-domain",
                engineering_question="q",
                decision_required="d",
            )

    def test_rejects_invalid_stage(self) -> None:
        with self.assertRaises(ValidationError):
            Study(
                id="S001",
                title="x",
                domain=Domain.MAXWELL,
                project_stage="six",
                engineering_question="q",
                decision_required="d",
            )

    def test_rejects_unknown_field(self) -> None:
        with self.assertRaises(ValidationError):
            Study(
                id="S001",
                title="x",
                domain=Domain.MAXWELL,
                engineering_question="q",
                decision_required="d",
                made_up_field="nope",
            )


class TestOtherRecords(unittest.TestCase):
    def test_requirement(self) -> None:
        req = Requirement(id="REQ-001", study_id="S001", title="Wind load basis")
        self.assertEqual(req.status.value, "proposed")

    def test_model_hypothesis(self) -> None:
        mh = ModelHypothesis(
            id="MH-001",
            study_id="S001",
            purpose="Bound mullion sizing",
            analysis_question="What section is adequate for span L?",
        )
        self.assertEqual(mh.approval_status.value, "draft")
        self.assertEqual(mh.supports, "unknown")

    def test_capability(self) -> None:
        cap = Capability(
            id="CAP-001",
            domain=Domain.MAXWELL,
            name="Isolated mullion sizing",
            purpose="Preliminary member sizing from conventional formulas",
        )
        self.assertEqual(cap.status.value, "proposed")

    def test_experiment_and_result_linkage(self) -> None:
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-001",
            title="Mullion span sweep",
        )
        result = Result(
            id="RES-001",
            experiment_id=exp.id,
            capability_id="CAP-001",
            result_type="deflection",
            units="mm",
            value=12.3,
        )
        self.assertEqual(result.experiment_id, "EXP-001")
        self.assertEqual(exp.model_hypothesis_id, "MH-001")

    def test_experiment_requires_model_hypothesis_id(self) -> None:
        with self.assertRaises(ValidationError):
            Experiment(id="EXP-001", study_id="S001", title="Mullion span sweep")

    def test_result_tracks_software_and_numerical_validation_separately(self) -> None:
        from noam.models.common import ValidationStatus

        result = Result(
            id="RES-001",
            experiment_id="EXP-001",
            capability_id="CAP-001",
            result_type="deflection",
            software_validation_status=ValidationStatus.PASSED,
            numerical_validation_status=ValidationStatus.PENDING,
        )
        self.assertEqual(result.software_validation_status, ValidationStatus.PASSED)
        self.assertEqual(result.numerical_validation_status, ValidationStatus.PENDING)

    def test_insight(self) -> None:
        insight = Insight(id="INS-001", study_id="S001", statement="Overhang depth dominates cooling")
        self.assertEqual(insight.reuse_status.value, "candidate")

    def test_precedent(self) -> None:
        prec = Precedent(id="PRE-001", domain=Domain.MAXWELL, title="Unitised CW isolated-member strategy")
        self.assertEqual(prec.validation_state.value, "experimental")

    def test_evidence(self) -> None:
        from noam.models.evidence import EvidenceKind

        ev = Evidence(
            id="EVD-001",
            study_id="S001",
            kind=EvidenceKind.DECISION,
            statement="Adopted isolated-member sizing for Stage 2",
        )
        self.assertFalse(ev.approved)

    def test_rule_card_is_metadata_only(self) -> None:
        rc = RuleCard(id="RC-001", standard="EN 1999-1-1")
        self.assertEqual(rc.approval_status.value, "draft")


if __name__ == "__main__":
    unittest.main()
