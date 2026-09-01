"""Required proposal shape and claim provenance (Gate 2 criteria 2, 3)."""

from __future__ import annotations

import json

from _support import FIXTURE_ROOT, A51TestCase, make_request

from noam.proposals import RecordedFixtureBackend, run_proposal_intake

SECTION_NAMES = (
    "sourced_facts",
    "inferred_facts",
    "missing_information",
    "proposed_study_fields",
    "proposed_requirements",
    "proposed_model_hypothesis",
)


def _package_json(fixture_id: str) -> dict:
    outcome = run_proposal_intake(make_request(fixture_id), RecordedFixtureBackend(FIXTURE_ROOT))
    assert outcome.ok, fixture_id
    return json.loads(outcome.package_bytes)


class ProposalShapeTest(A51TestCase):
    def test_all_six_sections_plus_provenance_and_status_present(self) -> None:
        payload = _package_json("cw-basics")
        for name in SECTION_NAMES:
            self.assertIn(name, payload)
        self.assertEqual(payload["status"], "proposed")
        self.assertIn("provenance", payload)

    def test_empty_sections_are_empty_collections_not_omitted(self) -> None:
        payload = _package_json("sparse-notes")
        self.assertEqual(payload["inferred_facts"], [])
        self.assertEqual(payload["proposed_study_fields"], [])
        self.assertEqual(payload["proposed_requirements"], [])
        # still present, not merged away
        for name in SECTION_NAMES:
            self.assertIn(name, payload)
        self.assertFalse(payload["proposed_model_hypothesis"]["present"])

    def test_categories_are_not_collapsed(self) -> None:
        payload = _package_json("cw-basics")
        self.assertTrue(payload["sourced_facts"])
        self.assertTrue(payload["inferred_facts"])
        self.assertTrue(payload["missing_information"])
        sourced_ids = {c["claim_id"] for c in payload["sourced_facts"]}
        inferred_ids = {c["claim_id"] for c in payload["inferred_facts"]}
        self.assertTrue(sourced_ids.isdisjoint(inferred_ids))

    def test_every_claim_has_id_citation_category_and_bounded_confidence(self) -> None:
        payload = _package_json("cw-basics")
        known_sources = {s["source_id"] for s in payload["provenance"]["sources"]}
        claim_ids = []
        for section in ("sourced_facts", "inferred_facts"):
            for claim in payload[section]:
                claim_ids.append(claim["claim_id"])
                self.assertIn(claim["category"], ("sourced", "inferred"))
                self.assertGreaterEqual(len(claim["citations"]), 1)
                for citation in claim["citations"]:
                    self.assertIn(citation["source_id"], known_sources)
                    self.assertRegex(
                        citation["locator"],
                        r"^(line|lines|para|span|offset):[0-9]+(-[0-9]+)?$",
                    )
                self.assertGreaterEqual(claim["confidence"], 0.0)
                self.assertLessEqual(claim["confidence"], 1.0)
        self.assertEqual(len(claim_ids), len(set(claim_ids)))

    def test_inferred_facts_stay_inferred_even_though_cited(self) -> None:
        payload = _package_json("cw-basics")
        for claim in payload["inferred_facts"]:
            self.assertEqual(claim["category"], "inferred")
            self.assertTrue(claim["citations"])

    def test_present_model_hypothesis_carries_full_provenance(self) -> None:
        mh = _package_json("cw-basics")["proposed_model_hypothesis"]
        self.assertTrue(mh["present"])
        self.assertRegex(mh["ref"], r"^PM-\d{3}$")
        self.assertTrue(mh["purpose"] and mh["analysis_question"] and mh["idealisation"])
        self.assertGreaterEqual(len(mh["citations"]), 1)
        self.assertEqual(mh["status"], "proposed")

    def test_absent_model_hypothesis_has_no_ref(self) -> None:
        mh = _package_json("sparse-notes")["proposed_model_hypothesis"]
        self.assertFalse(mh["present"])
        self.assertEqual(mh["ref"], "")

    def test_response_envelope_identifies_versions_and_digests(self) -> None:
        outcome = run_proposal_intake(make_request("cw-basics"), RecordedFixtureBackend(FIXTURE_ROOT))
        response = outcome.response
        self.assertEqual(response.contract_version, "a5.1.0")
        self.assertEqual(response.backend_id, "recorded-fixture")
        for digest in (response.request_sha256, response.source_sha256, response.output_sha256):
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
