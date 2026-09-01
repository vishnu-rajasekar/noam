"""Lexical retrieval baseline: BM25 over SQLite FTS5 (standard library only).

This is the deterministic benchmark. The ``Retriever`` protocol is the seam for
a later Qwen3 Embedding + Reranker implementation; nothing downstream depends on
this class.
"""

from __future__ import annotations

import re
import sqlite3

from .interfaces import Chunk, EvidenceItem, EvidencePacket, Retriever

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*")


def _fts_query(text: str) -> str:
    """Turn free text into a safe OR-of-terms FTS5 MATCH expression."""

    terms = _TOKEN_RE.findall(text.lower())
    terms = [t for t in terms if len(t) > 1]
    if not terms:
        return '""'
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(terms))


class LexicalRetriever(Retriever):
    method_name = "lexical_bm25_fts5"

    def __init__(self) -> None:
        self._db = sqlite3.connect(":memory:")
        self._db.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "chunk_id UNINDEXED, document_id UNINDEXED, page UNINDEXED, "
            "clause UNINDEXED, heading, text, tokenize='porter unicode61')"
        )
        self._indexed = 0

    def index(self, chunks: list[Chunk]) -> None:
        self._db.execute("DELETE FROM chunks")
        self._db.executemany(
            "INSERT INTO chunks(chunk_id, document_id, page, clause, heading, text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (c.chunk_id, c.document_id, c.page, c.clause, c.heading, c.text)
                for c in chunks
            ],
        )
        self._db.commit()
        self._indexed = len(chunks)

    def search(self, query: str, k: int) -> list[EvidenceItem]:
        match = _fts_query(query)
        rows = self._db.execute(
            "SELECT chunk_id, document_id, page, clause, heading, text, "
            "bm25(chunks) AS score FROM chunks WHERE chunks MATCH ? "
            "ORDER BY score ASC, chunk_id ASC LIMIT ?",
            (match, k),
        ).fetchall()
        items: list[EvidenceItem] = []
        for rank, (chunk_id, document_id, page, clause, _heading, text, score) in enumerate(
            rows, start=1
        ):
            items.append(
                EvidenceItem(
                    evidence_id=f"E{rank:03d}",
                    document_id=document_id,
                    page=int(page),
                    clause=clause,
                    chunk_id=chunk_id,
                    retrieval_score=round(-float(score), 6),  # higher = better
                    text=text,
                )
            )
        return items


def build_packet(
    retriever: Retriever, query: str, k: int, run_id: str
) -> EvidencePacket:
    items = retriever.search(query, k)
    return EvidencePacket(
        query=query,
        run_id=run_id,
        retrieval_method=getattr(retriever, "method_name", retriever.__class__.__name__),
        retrieval_params={"k": k},
        items=items,
    )
