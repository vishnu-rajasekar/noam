"""Restricted-input runs must not write output into the repository worktree.

These tests exercise the pure path-confinement decision in
``run._confinement_and_out`` - no filesystem tree is created.
"""

from __future__ import annotations

import argparse
import unittest
from pathlib import Path

from tools.standards_scout.run import RestrictedOutputError, _confinement_and_out

TS = "2026-09-01T12:00:00Z"


def _args(**kw) -> argparse.Namespace:
    base = dict(root=None, docs=None, metadata=None, ground_truth=None, out=None)
    base.update(kw)
    return argparse.Namespace(**base)


class TestConfinement(unittest.TestCase):
    def test_root_mode_default_out_is_inside_root(self) -> None:
        root = "knowledge/restricted/standards_scout"
        out = _confinement_and_out(_args(root=root), [Path(root) / "documents"], TS)
        self.assertTrue(
            out.resolve().is_relative_to(Path(root).resolve()),
            f"{out} escaped {root}",
        )
        self.assertIn("runs", out.parts)

    def test_root_mode_rejects_out_outside_root(self) -> None:
        root = "knowledge/restricted/standards_scout"
        with self.assertRaises(RestrictedOutputError):
            _confinement_and_out(_args(root=root, out="./_scout_out"), [Path(root)], TS)

    def test_root_mode_allows_explicit_out_inside_root(self) -> None:
        root = "knowledge/restricted/standards_scout"
        out = _confinement_and_out(_args(root=root, out=f"{root}/runs/manual"), [Path(root)], TS)
        self.assertTrue(out.resolve().is_relative_to(Path(root).resolve()))

    def test_restricted_inputs_without_root_are_confined(self) -> None:
        docs = Path("knowledge/restricted/standards_scout/documents")
        meta = Path("knowledge/restricted/standards_scout/metadata/documents.json")
        gt = Path("knowledge/restricted/standards_scout/ground_truth/airport_eval.json")
        out = _confinement_and_out(_args(docs=str(docs), metadata=str(meta), ground_truth=str(gt)),
                                   [docs, meta, gt], TS)
        self.assertTrue(
            out.resolve().is_relative_to(Path("knowledge/restricted").resolve()),
            f"{out} is outside knowledge/restricted",
        )

    def test_restricted_inputs_reject_worktree_out(self) -> None:
        docs = Path("knowledge/restricted/standards_scout/documents")
        with self.assertRaises(RestrictedOutputError):
            _confinement_and_out(
                _args(docs=str(docs), metadata="x", ground_truth="y", out="reports/leak"),
                [docs, Path("x"), Path("y")],
                TS,
            )

    def test_synthetic_inputs_use_plain_scout_out(self) -> None:
        docs = Path("tools/standards_scout/fixtures/synthetic/documents")
        out = _confinement_and_out(
            _args(docs=str(docs), metadata="m", ground_truth="g"),
            [docs, Path("m"), Path("g")],
            TS,
        )
        self.assertEqual(out, Path("./_scout_out"))


if __name__ == "__main__":
    unittest.main()
