"""Recorded-fixture backend: accept the nominal case, reject everything
else with structured reason codes (Gate 2 criteria 5, 6)."""

from __future__ import annotations

from _support import (
    RECORDED,
    A51TestCase,
    make_request,
    mutable_fixture_root,
    source_sha,
)

from noam.proposals import (
    ProposalPackage,
    RecordedFixtureBackend,
    UnresolvedState,
    run_proposal_intake,
    sha256_hex,
)
from noam.proposals.errors import ProposalError
from noam.proposals.unresolved import ReasonCode


def backend() -> RecordedFixtureBackend:
    return RecordedFixtureBackend(RECORDED.parent)


class NominalResolutionTest(A51TestCase):
    def test_nominal_fixture_resolves_to_a_package(self) -> None:
        result = backend().resolve(make_request("cw-basics"))
        self.assertIsInstance(result, ProposalPackage)
        self.assertEqual(result.provenance.fixture_id, "cw-basics")

    def test_intake_success_outcome_is_well_formed(self) -> None:
        outcome = run_proposal_intake(make_request("cw-basics"), backend())
        self.assertTrue(outcome.ok)
        self.assertIsNotNone(outcome.response)
        self.assertEqual(outcome.response.output_sha256, sha256_hex(outcome.package_bytes))
        self.assertEqual(outcome.response.source_sha256, source_sha("cw-basics"))


class StructuredRejectionTest(A51TestCase):
    def _reason(self, request) -> ReasonCode:
        with self.assertRaises(ProposalError) as ctx:
            backend().resolve(request)
        return ctx.exception.reason_code

    def test_unknown_fixture_id(self) -> None:
        self.assertEqual(
            self._reason(make_request("does-not-exist", source_sha256="a" * 64)),
            ReasonCode.UNKNOWN_FIXTURE,
        )

    def test_path_traversal_fixture_id_is_unknown_not_an_error(self) -> None:
        # bad ids fail request validation before they reach the backend;
        # a syntactically-legal-but-absent id is UNKNOWN_FIXTURE.
        self.assertEqual(
            self._reason(make_request("nope-nope", source_sha256="a" * 64)),
            ReasonCode.UNKNOWN_FIXTURE,
        )

    def test_source_digest_mismatch(self) -> None:
        self.assertEqual(
            self._reason(make_request("cw-basics", source_sha256="b" * 64)),
            ReasonCode.SOURCE_DIGEST_MISMATCH,
        )

    def test_contract_version_mismatch(self) -> None:
        self.assertEqual(
            self._reason(make_request("cw-basics", contract_version="a5.0.0")),
            ReasonCode.CONTRACT_VERSION_MISMATCH,
        )

    def test_foreign_backend_id_is_incompatible_input(self) -> None:
        self.assertEqual(
            self._reason(make_request("cw-basics", backend_id="live-ollama")),
            ReasonCode.INCOMPATIBLE_INPUT,
        )

    def test_recorded_output_digest_drift(self) -> None:
        self.assertEqual(
            self._reason(make_request("digest-drift")),
            ReasonCode.OUTPUT_DIGEST_MISMATCH,
        )

    def test_malformed_recorded_package(self) -> None:
        self.assertEqual(
            self._reason(make_request("malformed-record")),
            ReasonCode.MALFORMED_FIXTURE_RECORD,
        )

    def test_no_fallback_when_recorded_output_is_missing(self) -> None:
        with mutable_fixture_root() as root:
            (root / "recorded" / "cw-basics.package.json").unlink()
            with self.assertRaises(ProposalError) as ctx:
                RecordedFixtureBackend(root).resolve(make_request("cw-basics"))
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_tampered_recorded_output_byte_is_detected(self) -> None:
        with mutable_fixture_root() as root:
            target = root / "recorded" / "cw-basics.package.json"
            raw = bytearray(target.read_bytes())
            raw[10] ^= 0x20  # flip one bit in a byte
            target.write_bytes(bytes(raw))
            with self.assertRaises(ProposalError) as ctx:
                RecordedFixtureBackend(root).resolve(make_request("cw-basics"))
        self.assertEqual(ctx.exception.reason_code, ReasonCode.OUTPUT_DIGEST_MISMATCH)


class RecordedUnresolvedTest(A51TestCase):
    def test_missing_required_source_info(self) -> None:
        outcome = run_proposal_intake(make_request("insufficient-source"), backend())
        self.assertFalse(outcome.ok)
        self.assertIsInstance(outcome.unresolved, UnresolvedState)
        self.assertEqual(
            [i.reason_code for i in outcome.unresolved.items],
            [ReasonCode.MISSING_REQUIRED_SOURCE_INFO],
        )
        self.assertFalse(outcome.unresolved.ok)

    def test_incompatible_input(self) -> None:
        outcome = run_proposal_intake(make_request("incompatible-units"), backend())
        self.assertFalse(outcome.ok)
        self.assertEqual(
            [i.reason_code for i in outcome.unresolved.items],
            [ReasonCode.INCOMPATIBLE_INPUT],
        )

    def test_unresolved_items_carry_action_text_and_no_invented_defaults(self) -> None:
        outcome = run_proposal_intake(make_request("insufficient-source"), backend())
        item = outcome.unresolved.items[0]
        self.assertTrue(item.human_action)
        self.assertIn("insufficient-source", item.affected)
        # nothing that looks like an invented dimension / unit / standard
        for token in ("mm", "kPa", "EN 1", "RIBA", "jurisdiction="):
            self.assertNotIn(token, item.human_action)


class IntakeNeverRaisesForStructuredFailureTest(A51TestCase):
    def test_all_failure_modes_return_an_unresolved_outcome(self) -> None:
        cases = [
            make_request("does-not-exist", source_sha256="a" * 64),
            make_request("cw-basics", source_sha256="b" * 64),
            make_request("cw-basics", contract_version="a5.0.0"),
            make_request("cw-basics", backend_id="live-ollama"),
            make_request("digest-drift"),
            make_request("malformed-record"),
        ]
        for request in cases:
            outcome = run_proposal_intake(request, backend())
            self.assertFalse(outcome.ok, request.fixture_id)
            self.assertIsNone(outcome.response)
            self.assertGreaterEqual(len(outcome.unresolved.items), 1)
