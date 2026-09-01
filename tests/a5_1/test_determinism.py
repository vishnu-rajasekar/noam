"""Byte stability across fresh instances, and equality with the checked-in
recorded artefacts and their declared SHA-256 (Gate 2 criterion 7)."""

from __future__ import annotations

import json

from _support import (
    FIXTURE_ROOT,
    PACKAGE_FIXTURE_IDS,
    RECORDED,
    UNRESOLVED_FIXTURE_IDS,
    A51TestCase,
    make_request,
)

from noam.proposals import RecordedFixtureBackend, run_proposal_intake, sha256_hex


class DeterminismTest(A51TestCase):
    def test_two_fresh_backends_produce_identical_success_bytes(self) -> None:
        req = make_request("cw-basics")
        first = run_proposal_intake(req, RecordedFixtureBackend(FIXTURE_ROOT))
        second = run_proposal_intake(req, RecordedFixtureBackend(FIXTURE_ROOT))
        self.assertTrue(first.ok and second.ok)
        self.assertEqual(first.package_bytes, second.package_bytes)
        self.assertEqual(
            first.response.model_dump_json(), second.response.model_dump_json()
        )

    def test_success_bytes_equal_checked_in_recorded_output_and_digest(self) -> None:
        outcome = run_proposal_intake(make_request("cw-basics"), RecordedFixtureBackend(FIXTURE_ROOT))
        recorded = (RECORDED / "cw-basics.package.json").read_bytes()
        self.assertEqual(outcome.package_bytes, recorded)
        meta = json.loads((RECORDED / "cw-basics.meta.json").read_text())
        self.assertEqual(sha256_hex(outcome.package_bytes), meta["output_sha256"])
        self.assertEqual(outcome.response.output_sha256, meta["output_sha256"])

    def test_every_package_fixture_round_trips_byte_stably(self) -> None:
        for fixture_id in PACKAGE_FIXTURE_IDS:
            if fixture_id == "digest-drift":
                continue  # deliberately unresolved: no stable success output
            outcome = run_proposal_intake(
                make_request(fixture_id), RecordedFixtureBackend(FIXTURE_ROOT)
            )
            recorded = (RECORDED / f"{fixture_id}.package.json").read_bytes()
            self.assertTrue(outcome.ok, fixture_id)
            self.assertEqual(outcome.package_bytes, recorded, fixture_id)

    def test_recorded_request_digest_matches_live_request(self) -> None:
        outcome = run_proposal_intake(make_request("cw-basics"), RecordedFixtureBackend(FIXTURE_ROOT))
        meta = json.loads((RECORDED / "cw-basics.meta.json").read_text())
        self.assertEqual(outcome.response.request_sha256, meta["request_sha256"])

    def test_recorded_unresolved_bytes_are_stable_and_hashed(self) -> None:
        for fixture_id in UNRESOLVED_FIXTURE_IDS:
            outcome = run_proposal_intake(
                make_request(fixture_id), RecordedFixtureBackend(FIXTURE_ROOT)
            )
            self.assertFalse(outcome.ok)
            recorded = (RECORDED / f"{fixture_id}.unresolved.json").read_bytes()
            meta = json.loads((RECORDED / f"{fixture_id}.meta.json").read_text())
            self.assertEqual(sha256_hex(recorded), meta["output_sha256"])
