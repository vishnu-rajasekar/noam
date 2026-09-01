"""Ingestion preserves document / page / chunk identity and never invents a
clause."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.standards_scout.ingest import (
    UnsupportedFormatError,
    extract_document,
    extract_text_document,
    ingest_library,
)
from tools.standards_scout.interfaces import UNKNOWN_CLAUSE

FIX = Path(__file__).resolve().parents[2] / "tools" / "standards_scout" / "fixtures" / "synthetic"


class TestExtraction(unittest.TestCase):
    def test_clause_and_heading_detected(self) -> None:
        res = extract_document(FIX / "documents" / "SYN-SSGC-2024.txt", "SYN-SSGC-2024")
        clauses = {c.clause for c in res.chunks}
        self.assertIn("5.2", clauses)
        self.assertIn("4.3", clauses)
        self.assertIn("6.2", clauses)
        c52 = next(c for c in res.chunks if c.clause == "5.2")
        self.assertEqual(c52.document_id, "SYN-SSGC-2024")
        self.assertIn("deflection", c52.heading.lower())
        self.assertIn("span/175", c52.text)

    def test_annex_prefixed_clause_preserved(self) -> None:
        res = extract_document(FIX / "documents" / "SYN-NA-2024.txt", "SYN-NA-2024")
        clauses = {c.clause for c in res.chunks}
        self.assertIn("NA.4.3", clauses)
        self.assertIn("NA.6.2", clauses)

    def test_chunk_ids_are_unique_and_stable(self) -> None:
        res1 = extract_document(FIX / "documents" / "SYN-SPEC-A.txt", "SYN-SPEC-A")
        res2 = extract_document(FIX / "documents" / "SYN-SPEC-A.txt", "SYN-SPEC-A")
        ids1 = [c.chunk_id for c in res1.chunks]
        self.assertEqual(len(ids1), len(set(ids1)), "chunk ids must be unique")
        self.assertEqual(ids1, [c.chunk_id for c in res2.chunks], "extraction must be deterministic")
        for c in res1.chunks:
            self.assertTrue(c.chunk_id.startswith("SYN-SPEC-A_"))

    def test_pages_from_formfeed_are_tracked(self) -> None:
        text = "1 First\nalpha beta\n\f2 Second\ngamma delta\n"
        res = extract_text_document(text, "DOC")
        pages = sorted({c.page for c in res.chunks})
        self.assertEqual(pages, [1, 2])
        self.assertTrue(any("gamma" in c.text and c.page == 2 for c in res.chunks))

    def test_unknown_clause_not_invented(self) -> None:
        text = "This paragraph has no heading at all.\nJust prose about widgets.\n"
        res = extract_text_document(text, "DOC")
        self.assertTrue(res.chunks)
        self.assertTrue(all(c.clause == UNKNOWN_CLAUSE for c in res.chunks))
        self.assertTrue(any("no clause" in lim for lim in res.limitations))

    def test_pdf_is_rejected_not_degraded(self) -> None:
        with self.assertRaises(UnsupportedFormatError):
            extract_document(Path("something.pdf"), "DOC")


class TestLibraryIngestion(unittest.TestCase):
    def test_ingest_library_verifies_hashes(self) -> None:
        chunks, metas, _ = ingest_library(FIX / "documents", FIX / "documents.json")
        self.assertEqual({m.document_id for m in metas}, {"SYN-SSGC-2024", "SYN-NA-2024", "SYN-SPEC-A"})
        self.assertTrue(any(c.document_id == "SYN-NA-2024" for c in chunks))

    def test_hash_mismatch_is_fatal(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs").mkdir()
            (root / "docs" / "x.txt").write_text("1 Scope\nhello world\n", encoding="utf-8")
            (root / "meta.json").write_text(
                json.dumps(
                    {
                        "documents": [
                            {
                                "document_id": "X",
                                "title": "X",
                                "document_type": "guidance",
                                "source_file": "x.txt",
                                "sha256": "0" * 64,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                ingest_library(root / "docs", root / "meta.json")


if __name__ == "__main__":
    unittest.main()
