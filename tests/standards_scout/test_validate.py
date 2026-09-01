"""Deterministic citation / unsupported-claim validator."""

from __future__ import annotations

import unittest

from tools.standards_scout.interfaces import (
    Chunk,
    DocumentMeta,
    EvidenceItem,
    EvidencePacket,
)
from tools.standards_scout.validate import validate_response


def _packet() -> EvidencePacket:
    items = [
        EvidenceItem("E001", "SYN-SSGC-2024", 1, "5.2", "SYN-SSGC-2024_5.2_006", 3.1,
                     "the maximum lateral deflection of a mullion ... shall not exceed span/175"),
        EvidenceItem("E002", "SYN-SPEC-A", 1, "3.1", "SYN-SPEC-A_3.1_002", 2.4,
                     "limit the lateral deflection ... to span/250 and to 15 mm absolute"),
    ]
    return EvidencePacket("q", "RID", "lexical_bm25_fts5", {"k": 10}, items)


def _meta():
    return {
        "SYN-SSGC-2024": DocumentMeta("SYN-SSGC-2024", "code", "normative_standard", "a.txt", "0" * 64),
        "SYN-SPEC-A": DocumentMeta("SYN-SPEC-A", "spec", "project_specification", "b.txt", "1" * 64),
    }


def _chunks():
    return {
        "SYN-SSGC-2024_5.2_006": Chunk("SYN-SSGC-2024_5.2_006", "SYN-SSGC-2024", 1, "5.2", "Mullion", "..."),
        "SYN-SPEC-A_3.1_002": Chunk("SYN-SPEC-A_3.1_002", "SYN-SPEC-A", 1, "3.1", "Mullion deflection", "..."),
    }


def _good_response():
    return {
        "question_id": "Q",
        "status": "ANSWERED",
        "requirements": [
            {
                "claim_id": "C001",
                "claim": "The project specification limits mullion deflection to span/250 and 15 mm.",
                "classification": "EXPLICIT_REQUIREMENT",
                "evidence_ids": ["E002"],
                "applicability_conditions": [],
                "uncertainties": [],
            }
        ],
        "verification_procedure": [
            {"step": 1, "action": "Check mullion deflection against span/250.",
             "evidence_ids": ["E002"], "classification": "EXPLICIT"}
        ],
        "missing_information": [],
        "conflicts": [],
    }


class TestValidator(unittest.TestCase):
    def setUp(self) -> None:
        self.packet, self.meta, self.chunks = _packet(), _meta(), _chunks()

    def _run(self, resp):
        return validate_response(resp, self.packet, self.meta, self.chunks, question_id="Q")

    def test_good_response_passes(self) -> None:
        rep = self._run(_good_response())
        self.assertTrue(rep.ok, rep.codes())

    def test_unknown_evidence_id_rejected(self) -> None:
        resp = _good_response()
        resp["requirements"][0]["evidence_ids"] = ["E999"]
        rep = self._run(resp)
        self.assertIn("UNKNOWN_EVIDENCE_ID", rep.codes())
        self.assertFalse(rep.ok)

    def test_claim_without_evidence_rejected(self) -> None:
        resp = _good_response()
        resp["requirements"][0]["evidence_ids"] = []
        rep = self._run(resp)
        self.assertIn("UNSUPPORTED_CLAIM", rep.codes())

    def test_clause_mismatch_detected(self) -> None:
        # cite E001 but claim it is clause 9.9 via a doctored packet item
        bad_item = EvidenceItem("E001", "SYN-SSGC-2024", 1, "9.9", "SYN-SSGC-2024_5.2_006", 3.1, "x")
        self.packet.items[0] = bad_item
        rep = validate_response(
            _good_response() | {"requirements": [
                {"claim_id": "C1", "claim": "x", "classification": "INTERPRETATION",
                 "evidence_ids": ["E001"], "applicability_conditions": [], "uncertainties": []}
            ]},
            self.packet, self.meta, self.chunks, question_id="Q",
        )
        self.assertIn("CLAUSE_MISMATCH", rep.codes())

    def test_page_mismatch_detected(self) -> None:
        self.packet.items[0] = EvidenceItem(
            "E001", "SYN-SSGC-2024", 7, "5.2", "SYN-SSGC-2024_5.2_006", 3.1, "x"
        )
        resp = _good_response()
        resp["requirements"][0]["evidence_ids"] = ["E001"]
        rep = self._run(resp)
        self.assertIn("PAGE_NOT_FOUND", rep.codes())

    def test_prose_citation_without_matching_evidence_flagged(self) -> None:
        resp = _good_response()
        resp["requirements"][0]["claim"] = "Per EN 1999-1-1 clause 6.2.5 the member is adequate."
        resp["requirements"][0]["evidence_ids"] = ["E002"]  # E002 has no such clause
        rep = self._run(resp)
        self.assertIn("PROSE_CITATION_UNBACKED", rep.codes())

    def test_insufficient_evidence_response_validates(self) -> None:
        resp = {
            "question_id": "Q",
            "status": "INSUFFICIENT_EVIDENCE",
            "requirements": [],
            "verification_procedure": [],
            "missing_information": ["No supplied evidence addresses seismic detailing."],
            "conflicts": [],
        }
        rep = self._run(resp)
        self.assertTrue(rep.ok, rep.codes())

    def test_broken_schema_reported(self) -> None:
        rep = self._run({"question_id": "Q", "status": "MAYBE"})
        self.assertIn("SCHEMA_INVALID", rep.codes())
        self.assertFalse(rep.ok)

    def test_explicit_step_without_evidence_flagged(self) -> None:
        resp = _good_response()
        resp["verification_procedure"][0]["evidence_ids"] = []
        rep = self._run(resp)
        self.assertIn("MISSING_EVIDENCE", rep.codes())


class TestMalformedResponsesNeverRaise(unittest.TestCase):
    """Untrusted model output must always become a structured SCHEMA_INVALID
    result - never an exception that terminates the run."""

    def setUp(self) -> None:
        self.packet, self.meta, self.chunks = _packet(), _meta(), _chunks()

    def _run(self, resp):
        rep = validate_response(resp, self.packet, self.meta, self.chunks, question_id="Q")
        self.assertFalse(rep.ok)
        self.assertIn("SCHEMA_INVALID", rep.codes())
        return rep

    def test_top_level_not_an_object(self) -> None:
        for resp in (["not", "an", "object"], "bad", 7, None):
            self._run(resp)

    def test_conflicts_is_a_string(self) -> None:
        resp = _good_response()
        resp["conflicts"] = "bad"
        self._run(resp)

    def test_conflicts_has_scalar_entries(self) -> None:
        resp = _good_response()
        resp["conflicts"] = [123, "x", None]
        self._run(resp)

    def test_requirements_is_a_string(self) -> None:
        resp = _good_response()
        resp["requirements"] = "bad"
        self._run(resp)

    def test_requirements_has_scalar_entries(self) -> None:
        resp = _good_response()
        resp["requirements"] = ["nope", 5]
        self._run(resp)

    def test_evidence_ids_is_a_string(self) -> None:
        resp = _good_response()
        resp["requirements"][0]["evidence_ids"] = "E002"
        self._run(resp)

    def test_nested_list_field_wrong_type(self) -> None:
        resp = _good_response()
        resp["requirements"][0]["applicability_conditions"] = "should be a list"
        self._run(resp)

    def test_missing_information_has_non_strings(self) -> None:
        resp = _good_response()
        resp["missing_information"] = [{"nested": "object"}]
        self._run(resp)

    def test_verification_step_not_integer(self) -> None:
        resp = _good_response()
        resp["verification_procedure"][0]["step"] = "one"
        self._run(resp)

    def test_downstream_scoring_survives_malformed_response(self) -> None:
        from tools.standards_scout.evaluate import score_question
        from tools.standards_scout.report import render_question_report

        gt = {
            "question_id": "Q",
            "question": "q?",
            "answerability": {"answerable": True},
            "expected_evidence": {"documents": ["SYN-SPEC-A"], "clauses": []},
            "expected_concepts": ["span/250"],
            "unacceptable_claims": [],
            "expected_status": ["ANSWERED"],
        }
        for resp in ("bad", {"question_id": "Q", "status": "ANSWERED", "conflicts": "bad"}):
            rep = validate_response(resp, self.packet, self.meta, self.chunks, question_id="Q")
            outcome = score_question(resp, rep, self.packet, gt)  # must not raise
            text = render_question_report(gt, self.packet, resp, rep, outcome)  # must not raise
            self.assertIn("VALIDATOR FINDINGS", text)


if __name__ == "__main__":
    unittest.main()
