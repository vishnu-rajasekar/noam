"""Fixture-root confinement and symlink refusal (Codex round-1 finding 1).

The recorded backend must fail closed unless it is pointed at an explicitly
marked A5.1 fixture root. ``studies/`` and ``knowledge/restricted`` trees are
refused outright, every read stays beneath ``corpus/`` or ``recorded/`` after
path resolution, and no path component may be a symlink. None of these
refusals may read the target's content into a log line or an exception.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from _support import (
    FIXTURE_ROOT,
    A51TestCase,
    make_request,
    mutable_fixture_root,
)

from noam.proposals import (
    FIXTURE_ROOT_MARKER_NAME,
    RecordedFixtureBackend,
    run_proposal_intake,
)
from noam.proposals.errors import ProposalError
from noam.proposals.unresolved import ReasonCode

REPO_ROOT = Path(__file__).resolve().parents[2]
SYMLINK_TARGET = REPO_ROOT / "AGENTS.md"  # a real, non-restricted repo file


class FixtureRootAuthorisationTest(A51TestCase):
    def _reason(self, root: Path) -> ReasonCode:
        with self.assertRaises(ProposalError) as ctx:
            RecordedFixtureBackend(root).resolve(make_request("cw-basics"))
        self.assert_no_raw_content(str(ctx.exception), repr(ctx.exception))
        return ctx.exception.reason_code

    def test_nominal_checked_in_root_is_authorised(self) -> None:
        result = RecordedFixtureBackend(FIXTURE_ROOT).resolve(make_request("cw-basics"))
        self.assertEqual(result.provenance.fixture_id, "cw-basics")

    def test_bare_directory_without_marker_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                self._reason(Path(tmp)), ReasonCode.UNAUTHORISED_FIXTURE_ROOT
            )

    def test_copied_root_with_marker_deleted_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            (root / FIXTURE_ROOT_MARKER_NAME).unlink()
            self.assertEqual(self._reason(root), ReasonCode.UNAUTHORISED_FIXTURE_ROOT)

    def test_marker_with_tampered_content_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            (root / FIXTURE_ROOT_MARKER_NAME).write_bytes(b'{"a5_1_recorded_fixture_root":true}\n')
            self.assertEqual(self._reason(root), ReasonCode.UNAUTHORISED_FIXTURE_ROOT)

    def test_studies_s001_named_root_is_refused(self) -> None:
        with mutable_fixture_root(relative_name="studies/S001_airport_cw") as root:
            self.assertEqual(self._reason(root), ReasonCode.UNAUTHORISED_FIXTURE_ROOT)

    def test_knowledge_restricted_named_root_is_refused(self) -> None:
        with mutable_fixture_root(relative_name="knowledge/restricted") as root:
            self.assertEqual(self._reason(root), ReasonCode.UNAUTHORISED_FIXTURE_ROOT)

    def test_intake_returns_structured_unresolved_for_unauthorised_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outcome = run_proposal_intake(
                make_request("cw-basics"), RecordedFixtureBackend(Path(tmp))
            )
        self.assertFalse(outcome.ok)
        self.assertIsNone(outcome.response)
        self.assertEqual(
            [i.reason_code for i in outcome.unresolved.items],
            [ReasonCode.UNAUTHORISED_FIXTURE_ROOT],
        )
        self.assert_no_raw_content()


class SymlinkAndEscapeRefusalTest(A51TestCase):
    def _reason(self, root: Path, fixture_id: str = "cw-basics") -> ReasonCode:
        with self.assertRaises(ProposalError) as ctx:
            RecordedFixtureBackend(root).resolve(make_request(fixture_id))
        self.assert_no_raw_content(str(ctx.exception), repr(ctx.exception))
        return ctx.exception.reason_code

    def test_symlinked_corpus_file_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            target = root / "corpus" / "cw-basics.txt"
            target.unlink()
            target.symlink_to(SYMLINK_TARGET)
            self.assertEqual(self._reason(root), ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_symlinked_recorded_subdir_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            shutil.rmtree(root / "recorded")
            (root / "recorded").symlink_to(FIXTURE_ROOT / "recorded", target_is_directory=True)
            self.assertEqual(self._reason(root), ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_dotdot_in_recorded_source_file_is_refused(self) -> None:
        with mutable_fixture_root() as root:
            meta_path = root / "recorded" / "cw-basics.meta.json"
            meta = json.loads(meta_path.read_text())
            meta["source_file"] = "../AGENTS.md"
            meta_path.write_text(json.dumps(meta))
            self.assertEqual(self._reason(root), ReasonCode.MALFORMED_FIXTURE_RECORD)

    def test_intake_never_raises_for_symlink_escape(self) -> None:
        with mutable_fixture_root() as root:
            target = root / "corpus" / "cw-basics.txt"
            target.unlink()
            target.symlink_to(SYMLINK_TARGET)
            outcome = run_proposal_intake(
                make_request("cw-basics"), RecordedFixtureBackend(root)
            )
        self.assertFalse(outcome.ok)
        self.assertIsNone(outcome.response)
        self.assertEqual(
            [i.reason_code for i in outcome.unresolved.items],
            [ReasonCode.MALFORMED_FIXTURE_RECORD],
        )
        self.assert_no_raw_content()
