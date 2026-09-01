"""Proposal-only authority and side-effect freedom (Gate 2 criteria 4, 12)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from _support import (
    ALL_FIXTURE_IDS,
    FIXTURE_ROOT,
    A51TestCase,
    make_request,
)

from noam.proposals import RecordedFixtureBackend, run_proposal_intake

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCHED_DIRS = ("studies", "domains", "registry", "src/noam/models")


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(root)).encode("utf-8"))
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def backend() -> RecordedFixtureBackend:
    return RecordedFixtureBackend(FIXTURE_ROOT)


class AuthorityStatusTest(A51TestCase):
    def test_every_status_field_in_a_success_package_is_proposed(self) -> None:
        outcome = run_proposal_intake(make_request("cw-basics"), backend())
        payload = json.loads(outcome.package_bytes)

        def walk(node):
            if isinstance(node, dict):
                if "status" in node:
                    self.assertEqual(node["status"], "proposed")
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(payload)
        self.assertEqual(payload["status"], "proposed")

    def test_recorded_content_claiming_approval_does_not_change_authority(self) -> None:
        # the injection fixture's source text asserts APPROVED / COMPLIANT /
        # a human sign-off; the package it maps to stays proposed with no
        # such fields.
        outcome = run_proposal_intake(make_request("injection"), backend())
        self.assertTrue(outcome.ok)
        payload = json.loads(outcome.package_bytes)
        self.assertEqual(payload["status"], "proposed")
        self.assertNotIn("override_status", payload)
        blob = outcome.package_bytes.decode("utf-8")
        for token in ("approved", "compliant", "sign off", "signs off"):
            self.assertNotIn(token, blob.lower())


class SideEffectFreedomTest(A51TestCase):
    def test_intake_writes_nothing_to_authoring_state(self) -> None:
        before = {d: _tree_digest(REPO_ROOT / d) for d in WATCHED_DIRS}
        for fixture_id in ALL_FIXTURE_IDS:
            run_proposal_intake(make_request(fixture_id), backend())
        after = {d: _tree_digest(REPO_ROOT / d) for d in WATCHED_DIRS}
        self.assertEqual(before, after)

    def test_intake_does_not_import_the_registry_or_models_write_paths(self) -> None:
        import noam.proposals.backend as backend_mod
        import noam.proposals.intake as intake_mod

        for module in (backend_mod, intake_mod):
            source = Path(module.__file__).read_text()
            self.assertNotIn("noam.registry", source)
            self.assertNotIn("noam.models", source)
            self.assertNotIn("noam.studies", source)

    def test_outcome_is_data_only_no_callable_side_channel(self) -> None:
        outcome = run_proposal_intake(make_request("cw-basics"), backend())
        self.assertTrue(outcome.ok)
        self.assertIsInstance(outcome.package_bytes, bytes)
        # frozen dataclass -> cannot be mutated in place
        with self.assertRaises(Exception):
            outcome.ok = False
