"""Evaluation separates a retrieval miss from a reasoning failure."""

from __future__ import annotations

import unittest

from tools.standards_scout.evaluate import score_question
from tools.standards_scout.interfaces import EvidenceItem, EvidencePacket
from tools.standards_scout.validate import validate_response


def _packet(*triples) -> EvidencePacket:
    items = [
        EvidenceItem(f"E{n:03d}", d, 1, c, f"{d}_{c}_00{n}", 1.0, txt)
        for n, (d, c, txt) in enumerate(triples, start=1)
    ]
    return EvidencePacket("q", "RID", "lexical_bm25_fts5", {"k": 10}, items)


def _abstain(qid="Q"):
    return {
        "question_id": qid, "status": "INSUFFICIENT_EVIDENCE",
        "requirements": [], "verification_procedure": [],
        "missing_information": ["nothing retrieved"], "conflicts": [],
    }


def _answer(qid, claim, evidence_ids):
    return {
        "question_id": qid, "status": "ANSWERED",
        "requirements": [{
            "claim_id": "C001", "claim": claim, "classification": "EXPLICIT_REQUIREMENT",
            "evidence_ids": evidence_ids, "applicability_conditions": [], "uncertainties": [],
        }],
        "verification_procedure": [], "missing_information": [], "conflicts": [],
    }


GT = {
    "question_id": "Q",
    "question": "deflection limit?",
    "answerability": {"answerable": True},
    "expected_evidence": {"documents": ["SYN-SPEC-A"],
                          "clauses": [{"document_id": "SYN-SPEC-A", "clause": "3.1"}]},
    "expected_concepts": ["span/250", "15 mm"],
    "unacceptable_claims": ["span/175 governs"],
    "expected_status": ["ANSWERED", "PARTIAL"],
}


class TestLimitingFactor(unittest.TestCase):
    def _score(self, packet, resp, gt=GT):
        rep = validate_response(resp, packet, {}, {}, question_id=gt["question_id"])
        return score_question(resp, rep, packet, gt)

    def test_missing_expected_evidence_is_retrieval_failure(self) -> None:
        packet = _packet(("SYN-SSGC-2024", "6.2", "sealant bite text"))  # wrong clause
        outcome = self._score(packet, _abstain())
        self.assertEqual(outcome.limiting_factor, "RETRIEVAL_FAILURE")
        self.assertTrue(outcome.retrieval.missing)

    def test_evidence_present_but_wrong_answer_is_answer_failure(self) -> None:
        packet = _packet(("SYN-SPEC-A", "3.1", "limit to span/250 and 15 mm absolute"))
        outcome = self._score(packet, _answer("Q", "span/175 governs the mullion", ["E001"]))
        self.assertEqual(outcome.limiting_factor, "ANSWER_FAILURE")
        self.assertIn("span/175 governs", outcome.answer.unacceptable_claim_hits)

    def test_evidence_present_and_good_answer_is_ok(self) -> None:
        packet = _packet(("SYN-SPEC-A", "3.1", "limit to span/250 and 15 mm absolute"))
        outcome = self._score(
            packet, _answer("Q", "SYN-SPEC-A limits deflection to span/250 and 15 mm", ["E001"])
        )
        self.assertEqual(outcome.limiting_factor, "OK")
        self.assertTrue(outcome.answer.status_ok)
        self.assertEqual(outcome.answer.concept_coverage, 1.0)

    def test_false_abstention_counts_against_answer(self) -> None:
        packet = _packet(("SYN-SPEC-A", "3.1", "limit to span/250 and 15 mm absolute"))
        outcome = self._score(packet, _abstain())
        self.assertTrue(outcome.answer.incorrect_abstention)
        self.assertEqual(outcome.limiting_factor, "ANSWER_FAILURE")

    def test_correct_abstention_on_unanswerable(self) -> None:
        gt = dict(GT)
        gt["answerability"] = {"answerable": False}
        gt["expected_evidence"] = {"documents": [], "clauses": []}
        gt["expected_status"] = ["INSUFFICIENT_EVIDENCE"]
        gt["expected_concepts"] = []
        packet = _packet(("SYN-SSGC-2024", "6.2", "sealant text"))
        outcome = self._score(packet, _abstain(), gt)
        self.assertTrue(outcome.answer.correct_abstention)
        self.assertEqual(outcome.limiting_factor, "OK")

    def test_retrieval_metrics_values(self) -> None:
        packet = _packet(
            ("X", "1", "noise"), ("SYN-SPEC-A", "3.1", "the target"), ("Y", "2", "noise"),
        )
        outcome = self._score(packet, _answer("Q", "span/250 and 15 mm", ["E002"]))
        self.assertEqual(outcome.retrieval.recall_at_5, 1.0)
        self.assertAlmostEqual(outcome.retrieval.mrr, 0.5, places=3)


if __name__ == "__main__":
    unittest.main()
