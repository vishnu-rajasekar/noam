"""Deterministic text extraction into provenance-tagged chunks.

Scope of this spike: UTF-8 ``.txt`` / ``.md`` source only. Real text-based PDF
extraction needs a library that is not available in the sandbox; ``.pdf`` raises
``UnsupportedFormatError`` on purpose rather than silently degrading.

Chunking is clause/section aware where a heading can be detected reliably, and
falls back to page-scoped paragraph windows (``clause = UNKNOWN_CLAUSE``)
otherwise. A page break in plain text is a form-feed (``\\f``); with none, the
whole document is page 1.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from ._loaders import load_structured
from .interfaces import UNKNOWN_CLAUSE, Chunk, DocumentMeta, sha256_file

TEXT_SUFFIXES = {".txt", ".md", ".text"}

# A clause heading is a number (optionally an annex-style prefix of up to 3
# letters, kept in the clause) followed by a short Title-style phrase:
#   "6.2.5  Title of clause"   "A.3 Title"   "NA.4.3 Wind action factor"
# The heading text must start with a capital or digit so that a prose line like
# "clause 4.3 shall be taken as ..." is NOT mistaken for a heading.
_CLAUSE_RE = re.compile(
    r"^\s*(?P<clause>(?:[A-Za-z]{1,3}\.)?\d+(?:\.\d+){0,4})\)?"
    r"\s+(?P<heading>[A-Z0-9]\S*(?:\s+\S+)*?)\s*$"
)
_MAX_CHARS = 1400


class UnsupportedFormatError(RuntimeError):
    """Raised for inputs this spike deliberately does not handle (e.g. PDF)."""


@dataclass
class ExtractionResult:
    chunks: list[Chunk]
    limitations: list[str]


def _sanitise(token: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "-", token).strip("-") or "x"


def _looks_like_heading(line: str) -> tuple[str, str] | None:
    m = _CLAUSE_RE.match(line)
    if not m:
        return None
    heading = m.group("heading").strip()
    # Reject prose sentences that merely start with a number / clause reference.
    if heading.endswith((".", ",", ";", ":")) or len(heading.split()) > 12:
        return None
    if "=" in heading or " shall " in f" {heading.lower()} ":
        return None
    return m.group("clause"), heading


def _split_pages(text: str) -> list[str]:
    return text.split("\f") if "\f" in text else [text]


def extract_text_document(text: str, document_id: str) -> ExtractionResult:
    """Split raw text into clause/section-aware chunks with stable ids."""

    chunks: list[Chunk] = []
    limitations: list[str] = []
    seq = 0
    detected_any_clause = False

    for page_no, page_text in enumerate(_split_pages(text), start=1):
        cur_clause = UNKNOWN_CLAUSE
        cur_heading = ""
        buf: list[str] = []

        def flush() -> None:
            nonlocal seq, buf
            body = "\n".join(buf).strip()
            buf = []
            if not body:
                return
            # window over-long sections so a chunk stays reviewable
            for start in range(0, len(body), _MAX_CHARS):
                seq += 1
                piece = body[start : start + _MAX_CHARS]
                key = cur_clause if cur_clause != UNKNOWN_CLAUSE else f"p{page_no}"
                chunks.append(
                    Chunk(
                        chunk_id=f"{_sanitise(document_id)}_{_sanitise(key)}_{seq:03d}",
                        document_id=document_id,
                        page=page_no,
                        clause=cur_clause,
                        heading=cur_heading,
                        text=piece,
                    )
                )

        for raw in page_text.splitlines():
            line = raw.rstrip()
            head = _looks_like_heading(line)
            if head is not None:
                flush()
                cur_clause, cur_heading = head
                detected_any_clause = True
                continue
            buf.append(line)
        flush()

    if not detected_any_clause:
        limitations.append(
            f"{document_id}: no clause/section headings detected; all chunks "
            f"carry clause={UNKNOWN_CLAUSE!r}."
        )
    if "\f" not in text:
        limitations.append(f"{document_id}: no page breaks in source; all chunks on page 1.")
    return ExtractionResult(chunks=chunks, limitations=limitations)


def extract_document(path: Path, document_id: str) -> ExtractionResult:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raise UnsupportedFormatError(
            f"{path.name}: PDF extraction is out of scope for this spike. Provide a "
            f"pre-extracted UTF-8 .txt, or record a limitation to add a text-PDF "
            f"extractor under a separate approval."
        )
    if suffix not in TEXT_SUFFIXES:
        raise UnsupportedFormatError(f"{path.name}: unsupported source type {suffix!r}")
    return extract_text_document(path.read_text(encoding="utf-8"), document_id)


def load_document_library(metadata_path: Path) -> list[DocumentMeta]:
    data = load_structured(metadata_path) or {}
    out: list[DocumentMeta] = []
    for row in data.get("documents", []):
        out.append(
            DocumentMeta(
                document_id=row["document_id"],
                title=row["title"],
                document_type=row["document_type"],
                source_file=row["source_file"],
                sha256=row["sha256"],
                edition=row.get("edition"),
                applicable_to=tuple(row.get("applicable_to", []) or ()),
            )
        )
    return out


def ingest_library(
    docs_dir: Path, metadata_path: Path
) -> tuple[list[Chunk], list[DocumentMeta], list[str]]:
    """Extract every document named in the metadata file, verifying its SHA-256."""

    metas = load_document_library(metadata_path)
    all_chunks: list[Chunk] = []
    limitations: list[str] = []
    for meta in metas:
        src = docs_dir / meta.source_file
        if not src.exists():
            raise FileNotFoundError(f"{meta.document_id}: source file missing: {src}")
        actual = sha256_file(src)
        if actual != meta.sha256:
            raise ValueError(
                f"{meta.document_id}: sha256 mismatch (metadata {meta.sha256[:12]}..., "
                f"file {actual[:12]}...). Update metadata deliberately."
            )
        result = extract_document(src, meta.document_id)
        all_chunks.extend(result.chunks)
        limitations.extend(result.limitations)
    return all_chunks, metas, limitations


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Standards Scout ingestion helper")
    ap.add_argument("--hash", type=Path, help="print sha256 of a file and exit")
    ap.add_argument("--docs", type=Path, help="documents directory")
    ap.add_argument("--metadata", type=Path, help="documents.yaml")
    args = ap.parse_args(argv)
    if args.hash:
        print(sha256_file(args.hash))
        return 0
    if args.docs and args.metadata:
        chunks, metas, limitations = ingest_library(args.docs, args.metadata)
        print(f"{len(metas)} documents, {len(chunks)} chunks")
        for lim in limitations:
            print(f"  limitation: {lim}")
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
