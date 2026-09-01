"""Recorded-request integrity, strict metadata typing, and one-to-one source
provenance (Codex round-1 findings 2, 3, 4).

* the recorded ``request.json`` bytes, their digest and their canonical form
  are enforced, so ``meta.request_sha256`` is load-bearing;
* every metadata field is validated against a strict typed contract; a wrong
  type is always a structured ``MALFORMED_FIXTURE_RECORD``, never a traceback;
* a recorded package must declare exactly the one source the backend verified.
"""

from __future__ import annotations

import json

from _support import (
    RECORDED,
    A51TestCase,
    make_request,
    mutable_fixture_root,
    read_recorded_meta,
    rewrite_recorded_output,
    write_recorded_meta,
)

from noam.proposals import (
    ProposalPackage,
    RecordedFixtureBackend,
    canonical_bytes,
    run_proposal_intake,
    sha256_hex,
)
from noam.proposals.errors import ProposalError
from noam.proposals.unresolved import ReasonCode


def _resolve(root):
    return RecordedFixtureBackend(root).resolve(make_request("cw-basics"))


class RecordedRequestIntegrityTest(A51TestCase):
    def test_tampered_meta_request_sha_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            meta = read_recorded_meta(root, "cw-basics")
            meta["request_sha256"] = "a" * 64
            write_recorded_meta(root, "cw-basics", meta)
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)
        self.assert_no_raw_content(str(ctx.exception))

    def test_tampered_recorded_request_bytes_are_refused(self) -> None:
        with mutable_fixture_root() as root:
            path = root / "recorded" / "cw-basics.request.json"
            raw = bytearray(path.read_bytes())
            raw[5] ^= 0x20
            path.write_bytes(bytes(raw))
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_noncanonical_recorded_request_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            path = root / "recorded" / "cw-basics.request.json"
            data = json.loads(path.read_bytes())
            # valid content, deliberately non-canonical byte form
            noncanon = (json.dumps(data, indent=2) + "\n").encode("utf-8")
            path.write_bytes(noncanon)
            meta = read_recorded_meta(root, "cw-basics")
            meta["request_sha256"] = sha256_hex(noncanon)
            write_recorded_meta(root, "cw-basics", meta)
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_intake_never_raises_for_request_integrity_failure(self) -> None:
        with mutable_fixture_root() as root:
            meta = read_recorded_meta(root, "cw-basics")
            meta["request_sha256"] = "a" * 64
            write_recorded_meta(root, "cw-basics", meta)
            outcome = run_proposal_intake(
                make_request("cw-basics"), RecordedFixtureBackend(root)
            )
        self.assertFalse(outcome.ok)
        self.assertIsNone(outcome.response)
        self.assertEqual(
            [i.reason_code for i in outcome.unresolved.items],
            [ReasonCode.MALFORMED_FIXTURE_RECORD],
        )


# Every metadata field, with representative wrong-typed / out-of-contract
# values. Each must produce a structured failure and never a raw exception.
_BAD_META_VALUES = {
    "fixture_id": [123, ["cw-basics"], "Cw-Basics", "cw_basics", ""],
    "kind": ["other", 5, None, ["package"]],
    "contract_version": [1, None, ["a5.1.0"], ""],
    "backend_id": [[], 0, None],
    "backend_version": [{}, 1, None],
    "source_id": [["cw-basics"], 123, None, "cw basics"],
    "source_file": [123, "../AGENTS.md", "sub/dir.txt", None, ""],
    "source_sha256": [123, "zz" * 32, "4F84" + "a" * 60, None],
    "source_byte_length": ["627", True, -1, 1.5, None],
    "request_sha256": [123, "short", None],
    "output_sha256": [None, 123, "nothex" * 10],
}


class StrictMetadataContractTest(A51TestCase):
    def test_every_field_wrong_type_is_a_structured_failure(self) -> None:
        for field, bad_values in _BAD_META_VALUES.items():
            for bad in bad_values:
                with self.subTest(field=field, bad=repr(bad)):
                    with mutable_fixture_root() as root:
                        meta = read_recorded_meta(root, "cw-basics")
                        meta[field] = bad
                        write_recorded_meta(root, "cw-basics", meta)
                        with self.assertRaises(ProposalError) as ctx:
                            _resolve(root)
                        self.assertEqual(
                            ctx.exception.reason_code,
                            ReasonCode.MALFORMED_FIXTURE_RECORD,
                        )
                        outcome = run_proposal_intake(
                            make_request("cw-basics"), RecordedFixtureBackend(root)
                        )
                        self.assertFalse(outcome.ok)
                        self.assertIsNone(outcome.response)
        self.assert_no_raw_content()

    def test_unknown_meta_key_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            meta = read_recorded_meta(root, "cw-basics")
            meta["surprise"] = 1
            write_recorded_meta(root, "cw-basics", meta)
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_missing_meta_key_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            meta = read_recorded_meta(root, "cw-basics")
            del meta["source_file"]
            write_recorded_meta(root, "cw-basics", meta)
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)


class OneToOneSourceProvenanceTest(A51TestCase):
    def _package_dict(self) -> dict:
        return json.loads((RECORDED / "cw-basics.package.json").read_bytes())

    def test_duplicate_source_entry_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            data = self._package_dict()
            data["provenance"]["sources"].append(dict(data["provenance"]["sources"][0]))
            rewrite_recorded_output(
                root, "cw-basics", "package.json", json.dumps(data).encode("utf-8")
            )
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_extra_distinct_source_entry_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            data = self._package_dict()
            extra = dict(data["provenance"]["sources"][0])
            extra["source_id"] = "extra-src"
            data["provenance"]["sources"].append(extra)
            canon = canonical_bytes(ProposalPackage.model_validate(data))
            rewrite_recorded_output(root, "cw-basics", "package.json", canon)
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)
        self.assertEqual(ctx.exception.affected, "fixture.package.sources")

    def test_package_not_declaring_the_verified_source_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            data = self._package_dict()
            data["provenance"]["sources"][0]["source_id"] = "somethingelse"
            rewrite_recorded_output(
                root, "cw-basics", "package.json", json.dumps(data).encode("utf-8")
            )
            with self.assertRaises(ProposalError) as ctx:
                _resolve(root)
        self.assertEqual(ctx.exception.reason_code, ReasonCode.MALFORMED_FIXTURE_RECORD)
