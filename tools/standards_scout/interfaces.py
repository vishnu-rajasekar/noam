"""Stable data shapes and the two replaceable seams of the harness.

The pipeline is: ingest -> retrieve -> run (model) -> validate -> evaluate.
Only ``Retriever`` and ``ModelRunner`` are meant to be swapped (e.g. a semantic
Qwen3 Embedding + Reranker retriever, or a different local inference provider).
Everything downstream consumes the dataclasses below, not a concrete class.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

UNKNOWN_CLAUSE = "unknown"


@dataclass(frozen=True)
class DocumentMeta:
    """Stable identity + provenance for one source document."""

    document_id: str
    title: str
    document_type: str
    source_file: str
    sha256: str
    edition: str | None = None
    applicable_to: tuple[str, ...] = ()


@dataclass(frozen=True)
class Chunk:
    """A provenance-tagged unit of source text.

    ``clause`` is ``UNKNOWN_CLAUSE`` when reliable detection was not possible -
    it is never invented.
    """

    chunk_id: str
    document_id: str
    page: int
    clause: str
    heading: str
    text: str


@dataclass(frozen=True)
class EvidenceItem:
    """One retrieved chunk, labelled with a run-local evidence id (E001, ...)."""

    evidence_id: str
    document_id: str
    page: int
    clause: str
    chunk_id: str
    retrieval_score: float
    text: str


@dataclass
class EvidencePacket:
    """The complete, closed set of evidence a model may use for one question."""

    query: str
    run_id: str
    retrieval_method: str
    retrieval_params: dict
    items: list[EvidenceItem] = field(default_factory=list)

    def by_id(self, evidence_id: str) -> EvidenceItem | None:
        for item in self.items:
            if item.evidence_id == evidence_id:
                return item
        return None

    @property
    def evidence_ids(self) -> list[str]:
        return [i.evidence_id for i in self.items]


@dataclass(frozen=True)
class ScoutRequest:
    """Everything needed to invoke the model for one question."""

    question_id: str
    question: str
    project_context: str
    packet: EvidencePacket
    system_prompt: str
    system_prompt_version: str
    response_schema: dict
    response_schema_version: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            h.update(block)
    return h.hexdigest()


@runtime_checkable
class Retriever(Protocol):
    """Deterministic evidence retrieval. Swap for a semantic implementation
    without changing anything downstream."""

    method_name: str

    def index(self, chunks: list[Chunk]) -> None:
        """Load the corpus. Must be idempotent for a given chunk list."""

    def search(self, query: str, k: int) -> list[EvidenceItem]:
        """Return up to ``k`` evidence items, best first, with stable
        ``evidence_id`` values assigned by rank (E001, E002, ...)."""


@runtime_checkable
class ModelRunner(Protocol):
    """Invokes the model on a fully-formed request and returns the raw parsed
    JSON object it produced. No validation happens here."""

    provider_label: str
    model_id: str
    provider_is_local: bool
    generation_settings: dict

    def run(self, request: ScoutRequest) -> dict:
        ...
