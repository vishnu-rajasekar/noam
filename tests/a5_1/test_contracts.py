"""Strict runtime DTO behaviour (Gate 2 criteria 1, 3, 4)."""

from __future__ import annotations

from _support import A51TestCase

from pydantic import ValidationError

from noam.proposals import (
    Citation,
    Claim,
    ProposalPackage,
    ProposalRequest,
    ProposedModelHypothesis,
    UnresolvedState,
)


def _cite(src="cw-basics", loc="line:1"):
    return {"source_id": src, "locator": loc}


class RequestContractTest(A51TestCase):
    def test_rejects_unknown_field(self) -> None:
        with self.assertRaises(ValidationError):
            ProposalRequest(
                contract_version="a5.1.0",
                backend_id="recorded-fixture",
                fixture_id="cw-basics",
                expected_source_sha256="a" * 64,
                surprise=1,
            )

    def test_rejects_non_hex_source_digest(self) -> None:
        with self.assertRaises(ValidationError):
            ProposalRequest(
                contract_version="a5.1.0",
                backend_id="recorded-fixture",
                fixture_id="cw-basics",
                expected_source_sha256="not-a-digest",
            )

    def test_request_is_frozen(self) -> None:
        req = ProposalRequest(
            contract_version="a5.1.0",
            backend_id="recorded-fixture",
            fixture_id="cw-basics",
            expected_source_sha256="a" * 64,
        )
        with self.assertRaises(ValidationError):
            req.fixture_id = "other"


class CitationContractTest(A51TestCase):
    def test_locator_must_be_machine_checkable(self) -> None:
        Citation(source_id="s1", locator="line:3")
        Citation(source_id="s1", locator="lines:3-9")
        Citation(source_id="s1", locator="span:10-42")
        with self.assertRaises(ValidationError):
            Citation(source_id="s1", locator="somewhere near the top")
        with self.assertRaises(ValidationError):
            Citation(source_id="s1", locator="line:")


class ClaimContractTest(A51TestCase):
    def test_confidence_must_be_in_unit_interval(self) -> None:
        for bad in (-0.01, 1.01, 2.0):
            with self.assertRaises(ValidationError):
                Claim(
                    claim_id="SF-001",
                    category="sourced",
                    statement="x",
                    citations=[_cite()],
                    confidence=bad,
                )

    def test_confidence_is_quantised_on_ingest(self) -> None:
        claim = Claim(
            claim_id="SF-001",
            category="sourced",
            statement="x",
            citations=[_cite()],
            confidence=0.123456,
        )
        self.assertEqual(claim.confidence, 0.123)

    def test_at_least_one_citation_required(self) -> None:
        with self.assertRaises(ValidationError):
            Claim(
                claim_id="SF-001",
                category="sourced",
                statement="x",
                citations=[],
                confidence=0.5,
            )

    def test_inferred_claim_keeps_its_label_even_when_cited(self) -> None:
        claim = Claim(
            claim_id="IF-002",
            category="inferred",
            statement="derived, but cited",
            citations=[_cite(loc="para:2")],
            confidence=0.4,
        )
        self.assertEqual(claim.category, "inferred")

    def test_claim_id_prefix_must_match_category(self) -> None:
        with self.assertRaises(ValidationError):
            Claim(
                claim_id="SF-001",
                category="inferred",
                statement="x",
                citations=[_cite()],
                confidence=0.4,
            )
        with self.assertRaises(ValidationError):
            Claim(
                claim_id="IF-001",
                category="sourced",
                statement="x",
                citations=[_cite()],
                confidence=0.4,
            )


class ProposedModelHypothesisContractTest(A51TestCase):
    def test_absent_must_be_entirely_empty(self) -> None:
        ProposedModelHypothesis(present=False)
        with self.assertRaises(ValidationError):
            ProposedModelHypothesis(present=False, purpose="sneaky")
        with self.assertRaises(ValidationError):
            ProposedModelHypothesis(present=False, ref="PM-001")

    def test_present_needs_full_content_and_citation(self) -> None:
        with self.assertRaises(ValidationError):
            ProposedModelHypothesis(present=True, ref="PM-001", purpose="p")
        mh = ProposedModelHypothesis(
            present=True,
            ref="PM-001",
            purpose="p",
            analysis_question="q",
            idealisation="i",
            category="inferred",
            citations=[_cite(loc="line:3")],
            confidence=0.5,
        )
        self.assertEqual(mh.status, "proposed")

    def test_present_needs_a_stable_ref(self) -> None:
        for bad_ref in ("", "PM-1", "pm-001", "MH-001", "PM-0001"):
            with self.assertRaises(ValidationError):
                ProposedModelHypothesis(
                    present=True,
                    ref=bad_ref,
                    purpose="p",
                    analysis_question="q",
                    idealisation="i",
                    category="inferred",
                    citations=[_cite(loc="line:3")],
                    confidence=0.5,
                )

    def test_status_literal_is_fixed(self) -> None:
        with self.assertRaises(ValidationError):
            ProposedModelHypothesis(
                present=True,
                ref="PM-001",
                purpose="p",
                analysis_question="q",
                idealisation="i",
                category="inferred",
                citations=[_cite(loc="line:3")],
                confidence=0.5,
                status="approved",
            )


class PackageContractTest(A51TestCase):
    def _minimal_payload(self) -> dict:
        return {
            "status": "proposed",
            "provenance": {
                "contract_version": "a5.1.0",
                "backend_id": "recorded-fixture",
                "backend_version": "a5.1.0",
                "fixture_id": "cw-basics",
                "sources": [
                    {
                        "source_id": "cw-basics",
                        "origin": "o",
                        "locator": "whole-file",
                        "author_or_publisher": "a",
                        "licence": "CC0-1.0",
                        "created_or_retrieved": "2026-09-01",
                        "byte_length": 10,
                        "sha256": "b" * 64,
                        "redistribution_rationale": "r",
                    }
                ],
            },
            "sourced_facts": [],
            "inferred_facts": [],
            "missing_information": [],
            "proposed_study_fields": [],
            "proposed_requirements": [],
            "proposed_model_hypothesis": {"present": False},
        }

    def test_minimal_package_is_valid_and_sections_present(self) -> None:
        pkg = ProposalPackage.model_validate(self._minimal_payload())
        for name in (
            "sourced_facts",
            "inferred_facts",
            "missing_information",
            "proposed_study_fields",
            "proposed_requirements",
        ):
            self.assertEqual(getattr(pkg, name), ())
        self.assertFalse(pkg.proposed_model_hypothesis.present)

    def test_claim_cannot_cite_unknown_source(self) -> None:
        payload = self._minimal_payload()
        payload["sourced_facts"] = [
            {
                "claim_id": "SF-001",
                "category": "sourced",
                "statement": "x",
                "citations": [{"source_id": "ghost", "locator": "line:1"}],
                "confidence": 0.5,
            }
        ]
        with self.assertRaises(ValidationError):
            ProposalPackage.model_validate(payload)

    def test_section_membership_must_match_category(self) -> None:
        payload = self._minimal_payload()
        payload["sourced_facts"] = [
            {
                "claim_id": "IF-001",
                "category": "inferred",
                "statement": "x",
                "citations": [{"source_id": "cw-basics", "locator": "line:1"}],
                "confidence": 0.5,
            }
        ]
        with self.assertRaises(ValidationError):
            ProposalPackage.model_validate(payload)

    def test_status_literal_rejects_approved(self) -> None:
        payload = self._minimal_payload()
        payload["status"] = "approved"
        with self.assertRaises(ValidationError):
            ProposalPackage.model_validate(payload)

    def test_unknown_top_level_field_is_rejected(self) -> None:
        payload = self._minimal_payload()
        payload["override_status"] = "approved"
        with self.assertRaises(ValidationError):
            ProposalPackage.model_validate(payload)

    def test_duplicate_source_id_in_provenance_is_rejected(self) -> None:
        payload = self._minimal_payload()
        payload["provenance"]["sources"].append(
            dict(payload["provenance"]["sources"][0])
        )
        with self.assertRaises(ValidationError):
            ProposalPackage.model_validate(payload)

    def test_present_model_hypothesis_needs_a_ref(self) -> None:
        payload = self._minimal_payload()
        payload["proposed_model_hypothesis"] = {
            "present": True,
            "purpose": "p",
            "analysis_question": "q",
            "idealisation": "i",
            "category": "inferred",
            "citations": [{"source_id": "cw-basics", "locator": "line:1"}],
            "confidence": 0.5,
        }
        with self.assertRaises(ValidationError):
            ProposalPackage.model_validate(payload)
        payload["proposed_model_hypothesis"]["ref"] = "PM-001"
        pkg = ProposalPackage.model_validate(payload)
        self.assertEqual(pkg.proposed_model_hypothesis.ref, "PM-001")


class UnresolvedContractTest(A51TestCase):
    def test_requires_at_least_one_item(self) -> None:
        with self.assertRaises(ValidationError):
            UnresolvedState(contract_version="a5.1.0", backend_id="recorded-fixture", items=[])

    def test_ok_is_always_false(self) -> None:
        with self.assertRaises(ValidationError):
            UnresolvedState(
                ok=True,
                contract_version="a5.1.0",
                backend_id="recorded-fixture",
                items=[
                    {
                        "reason_code": "unknown_fixture",
                        "affected": "request.fixture_id",
                        "human_action": "x",
                    }
                ],
            )
