"""Restricted inputs/outputs cannot accidentally become committed fixtures."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCOUT = REPO / "tools" / "standards_scout"


class TestRestrictedIsolation(unittest.TestCase):
    def test_gitignore_still_covers_restricted_tree(self) -> None:
        rules = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("knowledge/restricted/", rules,
                      "the broad restricted-tree ignore rule must remain intact")

    def test_default_run_root_is_inside_the_ignored_tree(self) -> None:
        # run.py documents knowledge/restricted/standards_scout as the --root;
        # confirm git would ignore anything written there.
        target = REPO / "knowledge" / "restricted" / "standards_scout" / "runs" / "example.json"
        res = subprocess.run(
            ["git", "check-ignore", "-q", str(target)],
            cwd=REPO, capture_output=True, text=True,
        )
        self.assertEqual(res.returncode, 0,
                         "git does not ignore the restricted standards_scout run dir")

    def test_committed_fixtures_are_synthetic_only(self) -> None:
        fixtures = SCOUT / "fixtures"
        self.assertTrue((fixtures / "synthetic").is_dir())
        for path in fixtures.rglob("*"):
            rel = path.relative_to(fixtures).as_posix()
            self.assertTrue(
                rel.startswith("synthetic/") or rel == "synthetic",
                f"unexpected non-synthetic fixture path: {rel}",
            )
        for txt in (fixtures / "synthetic" / "documents").glob("*.txt"):
            head = txt.read_text(encoding="utf-8")[:400].lower()
            self.assertIn("synthetic", head)
            self.assertIn("invented", head)

    def test_fixtures_hold_no_restricted_document_content(self) -> None:
        # A doc-comment may *mention* the restricted tree; what must never appear
        # is restricted source content or the restricted audit artefact name.
        banned = ("S001_framesizer_maxwell_audit", "CONFIDENTIAL", "knowledge/restricted/framesizer")
        for path in (SCOUT / "fixtures").rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                for marker in banned:
                    self.assertNotIn(marker, text, f"{path} contains restricted marker {marker!r}")


if __name__ == "__main__":
    unittest.main()
