import tempfile
import unittest
from pathlib import Path
from unittest import mock

from noam.models import (
    Capability,
    Evidence,
    Experiment,
    Insight,
    ModelHypothesis,
    Precedent,
    Requirement,
    Result,
    Study,
)
from noam.models.common import ApprovalStatus, Domain
from noam.models.evidence import EvidenceKind
from noam.registry import index as index_mod
from noam.registry import store
from noam.registry.validate import validate_registry
from noam.studies.scaffold import create_study


class RegistryTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "pyproject.toml").write_text("", encoding="utf-8")
        (self.root / "studies").mkdir()
        (self.root / "domains" / "maxwell" / "capabilities").mkdir(parents=True)
        (self.root / "domains" / "maxwell" / "precedents").mkdir(parents=True)
        (self.root / "domains" / "joule" / "capabilities").mkdir(parents=True)
        (self.root / "domains" / "joule" / "precedents").mkdir(parents=True)
        (self.root / "registry").mkdir()

        patcher = mock.patch("noam.registry.paths.repo_root", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.study = Study(
            id="S001",
            title="Airport Unitised Curtain Wall",
            domain=Domain.MAXWELL,
            engineering_question="q",
            decision_required="d",
        )
        self.study_dir = create_study(self.study)


class TestIndex(RegistryTestBase):
    def test_build_index_counts_records(self) -> None:
        cap = Capability(
            id="CAP-001",
            domain=Domain.MAXWELL,
            name="Isolated mullion sizing",
            purpose="p",
        )
        store.save_record(cap, self.root / "domains" / "maxwell" / "capabilities" / "CAP-001.yaml")

        result = index_mod.build_index(db_path=self.root / "registry" / "noam.db")
        self.assertEqual(result.studies, 1)
        self.assertEqual(result.capabilities, 1)
        self.assertEqual(result.precedents, 0)

    def test_build_index_is_idempotent(self) -> None:
        db_path = self.root / "registry" / "noam.db"
        first = index_mod.build_index(db_path=db_path)
        second = index_mod.build_index(db_path=db_path)
        self.assertEqual(first, second)

    def test_search_filters_by_domain(self) -> None:
        db_path = self.root / "registry" / "noam.db"
        index_mod.build_index(db_path=db_path)
        rows = index_mod.search("studies", db_path=db_path, domain="maxwell")
        self.assertEqual(len(rows), 1)
        rows = index_mod.search("studies", db_path=db_path, domain="joule")
        self.assertEqual(rows, [])

    def test_search_rejects_unknown_table(self) -> None:
        db_path = self.root / "registry" / "noam.db"
        index_mod.build_index(db_path=db_path)
        with self.assertRaises(ValueError):
            index_mod.search("not_a_table", db_path=db_path)

    def test_search_rejects_unknown_filter(self) -> None:
        db_path = self.root / "registry" / "noam.db"
        index_mod.build_index(db_path=db_path)
        with self.assertRaises(ValueError):
            index_mod.search("studies", db_path=db_path, sql_injection_attempt="x")


class TestValidate(RegistryTestBase):
    def _add_capability(self, cap_id: str = "CAP-001", domain: str = "maxwell") -> Capability:
        cap = Capability(id=cap_id, domain=Domain(domain), name="n", purpose="p")
        store.save_record(cap, self.root / "domains" / domain / "capabilities" / f"{cap_id}.yaml")
        return cap

    def _add_precedent(self, pre_id: str = "PRE-001", domain: str = "maxwell") -> Precedent:
        pre = Precedent(id=pre_id, domain=Domain(domain), title="t")
        store.save_record(pre, self.root / "domains" / domain / "precedents" / f"{pre_id}.yaml")
        return pre

    def _set_study_list(self, field_name: str, values: list[str]) -> None:
        study = store.load_study("S001")
        setattr(study, field_name, values)
        store.save_study(study)

    def _add_approved_hypothesis(self, mh_id: str = "MH-001") -> ModelHypothesis:
        mh = ModelHypothesis(
            id=mh_id,
            study_id="S001",
            purpose="p",
            analysis_question="q",
            approval_status=ApprovalStatus.APPROVED,
        )
        store.save_record(mh, self.study_dir / "model" / f"{mh_id}.yaml")
        return mh

    def test_valid_registry_reports_ok(self) -> None:
        report = validate_registry()
        self.assertTrue(report.ok, report.problems)

    def test_fully_wired_registry_reports_ok(self) -> None:
        self._add_capability()
        self._add_approved_hypothesis()
        store.append_study_ref("S001", "model_hypothesis", "MH-001")
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-001",
            capability_ids=["CAP-001"],
            title="t",
        )
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        store.append_study_ref("S001", "experiment", "EXP-001")
        result = Result(id="RES-001", experiment_id="EXP-001", capability_id="CAP-001", result_type="deflection")
        store.save_record(result, self.study_dir / "results" / "RES-001.yaml")
        report = validate_registry()
        self.assertTrue(report.ok, report.problems)

    def test_detects_requirement_with_wrong_study_id(self) -> None:
        req = Requirement(id="REQ-001", study_id="S999", title="Wrong study")
        store.save_record(req, self.study_dir / "requirements" / "REQ-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("REQ-001" in p for p in report.problems))

    def test_detects_experiment_referencing_unknown_model_hypothesis(self) -> None:
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-999",
            title="Unlinked experiment",
        )
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("unknown model_hypothesis_id" in p for p in report.problems))

    def test_detects_experiment_referencing_unapproved_hypothesis(self) -> None:
        mh = ModelHypothesis(id="MH-001", study_id="S001", purpose="p", analysis_question="q")
        store.save_record(mh, self.study_dir / "model" / "MH-001.yaml")
        self.assertEqual(mh.approval_status, ApprovalStatus.DRAFT)
        exp = Experiment(id="EXP-001", study_id="S001", model_hypothesis_id="MH-001", title="t")
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("not approved" in p for p in report.problems))

    def test_detects_result_referencing_unknown_experiment(self) -> None:
        self._add_capability()
        result = Result(
            id="RES-001",
            experiment_id="EXP-999",
            capability_id="CAP-001",
            result_type="deflection",
        )
        store.save_record(result, self.study_dir / "results" / "RES-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("unknown experiment_id" in p for p in report.problems))

    def test_detects_result_referencing_unknown_capability(self) -> None:
        result = Result(
            id="RES-001",
            experiment_id="EXP-001",
            capability_id="CAP-999",
            result_type="deflection",
        )
        store.save_record(result, self.study_dir / "results" / "RES-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("unknown capability_id" in p for p in report.problems))

    def test_detects_experiment_referencing_unknown_capability(self) -> None:
        self._add_approved_hypothesis()
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-001",
            capability_ids=["CAP-999"],
            title="t",
        )
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("unknown capability_id" in p for p in report.problems))

    def test_detects_insight_with_wrong_study_id(self) -> None:
        ins = Insight(id="INS-001", study_id="S999", statement="x")
        store.save_record(ins, self.study_dir / "insights" / "INS-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("INS-001" in p for p in report.problems))

    def test_detects_evidence_with_wrong_study_id(self) -> None:
        ev = Evidence(id="EVD-001", study_id="S999", kind=EvidenceKind.DECISION, statement="x")
        store.save_record(ev, self.study_dir / "evidence" / "EVD-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("EVD-001" in p for p in report.problems))

    def test_detects_filename_id_mismatch(self) -> None:
        req = Requirement(id="REQ-001", study_id="S001", title="x")
        # saved under a filename that does not match the record's own id
        store.save_record(req, self.study_dir / "requirements" / "REQ-002.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("does not match record id" in p for p in report.problems))

    def test_detects_duplicate_study_id(self) -> None:
        other_dir = self.root / "studies" / "S001_duplicate"
        other_dir.mkdir()
        store.save_record(self.study, other_dir / "study.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("duplicate study id" in p for p in report.problems))

    def test_detects_duplicate_capability_id_across_domains(self) -> None:
        self._add_capability(cap_id="CAP-001", domain="maxwell")
        self._add_capability(cap_id="CAP-001", domain="joule")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("duplicate capability id" in p for p in report.problems))

    def test_detects_duplicate_requirement_id_across_studies(self) -> None:
        other_dir = self.root / "studies" / "S002_other"
        (other_dir / "requirements").mkdir(parents=True)
        other_study = Study(
            id="S002",
            title="Other",
            domain=Domain.MAXWELL,
            engineering_question="q",
            decision_required="d",
        )
        store.save_record(other_study, other_dir / "study.yaml")
        req_a = Requirement(id="REQ-001", study_id="S001", title="a")
        store.save_record(req_a, self.study_dir / "requirements" / "REQ-001.yaml")
        store.append_study_ref("S001", "requirement", "REQ-001")
        req_b = Requirement(id="REQ-001", study_id="S002", title="b")
        store.save_record(req_b, other_dir / "requirements" / "REQ-001.yaml")
        store.append_study_ref("S002", "requirement", "REQ-001")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(any("duplicate requirement id" in p for p in report.problems))

    def test_detects_capability_filed_under_wrong_domain_directory(self) -> None:
        # a joule-domain capability saved under domains/maxwell/capabilities/
        cap = Capability(id="CAP-001", domain=Domain.JOULE, name="n", purpose="p")
        store.save_record(
            cap, self.root / "domains" / "maxwell" / "capabilities" / "CAP-001.yaml"
        )
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any("filed under domains/maxwell/" in p for p in report.problems)
        )

    def test_detects_result_capability_not_declared_by_experiment(self) -> None:
        self._add_capability(cap_id="CAP-001")
        self._add_capability(cap_id="CAP-002")
        self._add_approved_hypothesis()
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-001",
            capability_ids=["CAP-001"],
            title="t",
        )
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        store.append_study_ref("S001", "experiment", "EXP-001")
        store.append_study_ref("S001", "model_hypothesis", "MH-001")
        result = Result(
            id="RES-001",
            experiment_id="EXP-001",
            capability_id="CAP-002",
            result_type="deflection",
        )
        store.save_record(result, self.study_dir / "results" / "RES-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any("not among experiment" in p for p in report.problems)
        )

    def test_detects_child_record_missing_from_study_index(self) -> None:
        req = Requirement(id="REQ-001", study_id="S001", title="x")
        store.save_record(req, self.study_dir / "requirements" / "REQ-001.yaml")
        # deliberately not calling append_study_ref
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any("not listed in study.requirement_ids" in p for p in report.problems)
        )

    def test_detects_study_index_listing_absent_child_record(self) -> None:
        store.append_study_ref("S001", "requirement", "REQ-404")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any(
                "study.requirement_ids lists REQ-404" in p for p in report.problems
            )
        )

    # -- review round 3: domain-scoped references must not cross domains ----

    def test_detects_study_capability_reference_crossing_domain(self) -> None:
        # S001 is a maxwell study; CAP-001 is a joule capability.
        self._add_capability(cap_id="CAP-001", domain="joule")
        self._set_study_list("capability_ids", ["CAP-001"])
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any("must not cross domains" in p and "CAP-001" in p for p in report.problems),
            report.problems,
        )

    def test_detects_study_precedent_reference_crossing_domain(self) -> None:
        self._add_precedent(pre_id="PRE-001", domain="joule")
        self._set_study_list("precedent_ids", ["PRE-001"])
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any("must not cross domains" in p and "PRE-001" in p for p in report.problems),
            report.problems,
        )

    def test_detects_experiment_capability_reference_crossing_domain(self) -> None:
        self._add_capability(cap_id="CAP-001", domain="joule")
        self._add_approved_hypothesis()
        store.append_study_ref("S001", "model_hypothesis", "MH-001")
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-001",
            capability_ids=["CAP-001"],
            title="t",
        )
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        store.append_study_ref("S001", "experiment", "EXP-001")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any("experiment EXP-001" in p and "must not cross domains" in p for p in report.problems),
            report.problems,
        )

    def test_detects_result_capability_reference_crossing_domain(self) -> None:
        self._add_capability(cap_id="CAP-001", domain="joule")
        self._add_approved_hypothesis()
        store.append_study_ref("S001", "model_hypothesis", "MH-001")
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-001",
            title="t",
        )
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        store.append_study_ref("S001", "experiment", "EXP-001")
        result = Result(
            id="RES-001",
            experiment_id="EXP-001",
            capability_id="CAP-001",
            result_type="deflection",
        )
        store.save_record(result, self.study_dir / "results" / "RES-001.yaml")
        report = validate_registry()
        self.assertFalse(report.ok)
        self.assertTrue(
            any("result RES-001" in p and "must not cross domains" in p for p in report.problems),
            report.problems,
        )

    def test_same_domain_capability_and_precedent_references_are_valid(self) -> None:
        self._add_capability(cap_id="CAP-001", domain="maxwell")
        self._add_precedent(pre_id="PRE-001", domain="maxwell")
        self._add_approved_hypothesis()
        store.append_study_ref("S001", "model_hypothesis", "MH-001")
        exp = Experiment(
            id="EXP-001",
            study_id="S001",
            model_hypothesis_id="MH-001",
            capability_ids=["CAP-001"],
            title="t",
        )
        store.save_record(exp, self.study_dir / "experiments" / "EXP-001.yaml")
        store.append_study_ref("S001", "experiment", "EXP-001")
        result = Result(
            id="RES-001",
            experiment_id="EXP-001",
            capability_id="CAP-001",
            result_type="deflection",
        )
        store.save_record(result, self.study_dir / "results" / "RES-001.yaml")
        self._set_study_list("capability_ids", ["CAP-001"])
        self._set_study_list("precedent_ids", ["PRE-001"])
        report = validate_registry()
        self.assertTrue(report.ok, report.problems)

    # -- review round 3: malformed authoring YAML is a structured problem ---

    def test_malformed_study_yaml_is_reported_not_raised(self) -> None:
        (self.study_dir / "study.yaml").write_text("id: S001\ntitle: [1, 2, 3", encoding="utf-8")
        report = validate_registry()  # must not raise
        self.assertFalse(report.ok)
        self.assertTrue(any("study.yaml" in p for p in report.problems), report.problems)

    def test_malformed_child_yaml_is_reported_and_scan_continues(self) -> None:
        (self.study_dir / "requirements" / "REQ-001.yaml").write_text(
            "title: [1, 2, 3", encoding="utf-8"
        )
        # a second, well-formed problem must still be found -> scan continued
        ins = Insight(id="INS-001", study_id="S999", statement="x")
        store.save_record(ins, self.study_dir / "insights" / "INS-001.yaml")
        report = validate_registry()  # must not raise
        self.assertFalse(report.ok)
        self.assertTrue(any("REQ-001.yaml" in p for p in report.problems), report.problems)
        self.assertTrue(any("INS-001" in p for p in report.problems), report.problems)


class TestAppendStudyRef(RegistryTestBase):
    def test_appends_and_is_idempotent(self) -> None:
        store.append_study_ref("S001", "requirement", "REQ-001")
        store.append_study_ref("S001", "requirement", "REQ-001")
        reloaded = store.load_study("S001")
        self.assertEqual(reloaded.requirement_ids, ["REQ-001"])

    def test_tracks_each_kind_in_its_own_field(self) -> None:
        store.append_study_ref("S001", "model_hypothesis", "MH-001")
        store.append_study_ref("S001", "experiment", "EXP-001")
        store.append_study_ref("S001", "insight", "INS-001")
        reloaded = store.load_study("S001")
        self.assertEqual(reloaded.model_hypothesis_ids, ["MH-001"])
        self.assertEqual(reloaded.experiment_ids, ["EXP-001"])
        self.assertEqual(reloaded.insight_ids, ["INS-001"])


if __name__ == "__main__":
    unittest.main()
