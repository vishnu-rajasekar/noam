"""Retrieval returns stable, rank-assigned evidence IDs."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.standards_scout.ingest import ingest_library
from tools.standards_scout.retrieve import LexicalRetriever, build_packet

FIX = Path(__file__).resolve().parents[2] / "tools" / "standards_scout" / "fixtures" / "synthetic"


class TestLexicalRetriever(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks, _, _ = ingest_library(FIX / "documents", FIX / "documents.json")
        self.r = LexicalRetriever()
        self.r.index(self.chunks)

    def test_evidence_ids_assigned_by_rank(self) -> None:
        items = self.r.search("mullion deflection limit serviceability wind", k=5)
        self.assertTrue(items)
        self.assertEqual([i.evidence_id for i in items], [f"E00{n}" for n in range(1, len(items) + 1)])

    def test_retrieval_is_deterministic(self) -> None:
        q = "structural sealant bite formula"
        a = self.r.search(q, k=10)
        b = self.r.search(q, k=10)
        self.assertEqual([(i.evidence_id, i.chunk_id) for i in a],
                         [(i.evidence_id, i.chunk_id) for i in b])

    def test_reindex_same_corpus_same_result(self) -> None:
        q = "wind action combination factor"
        before = self.r.search(q, k=10)
        self.r.index(self.chunks)
        after = self.r.search(q, k=10)
        self.assertEqual([i.chunk_id for i in before], [i.chunk_id for i in after])

    def test_relevant_clause_is_retrieved(self) -> None:
        items = self.r.search("mullion transom deflection span serviceability wind", k=10)
        hit = [i for i in items if i.document_id == "SYN-SSGC-2024" and i.clause == "5.2"]
        self.assertTrue(hit, "expected SSGC 5.2 in the packet")

    def test_packet_carries_method_and_params(self) -> None:
        packet = build_packet(self.r, "glue line thickness", k=7, run_id="RID")
        self.assertEqual(packet.retrieval_method, "lexical_bm25_fts5")
        self.assertEqual(packet.retrieval_params, {"k": 7})
        self.assertEqual(packet.run_id, "RID")


if __name__ == "__main__":
    unittest.main()
