"""Deterministic citation / unsupported-claim validator.

This is the harness's primary hallucination control. It establishes *citation
integrity*, not semantic correctness - a response that passes here is not
"verified", only structurally sound. Findings are hard failures (ERROR) unless
noted as WARNING.

Failure codes:
    SCHEMA_INVALID        response does not match the response schema
    UNKNOWN_EVIDENCE_ID   an evidence_id that was never issued this run
    EVIDENCE_NOT_IN_RUN   evidence_id not present in this question's packet
    DOC_ID_MISMATCH       cited item's document_id disagrees with stored metadata
    PAGE_NOT_FOUND        cited page not present for that document
    CLAUSE_MISMATCH       cited item's clause disagrees with stored chunk metadata
    UNSUPPORTED_CLAIM     a normative requirement with no evidence_ids
    MISSING_EVIDENCE      an EXPLICIT procedure step with no evidence_ids
    PROSE_CITATION_UNBACKED   a standard/clause id in free text with no cited
                              evidence item carrying it
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import _jsonschema_lite
from .interfaces import UNKNOWN_CLAUSE, Chunk, DocumentMeta, EvidencePacket

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "scout_response.schema.json"
_RESPONSE_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

# "EN 1999-1-1", "EN 1993", "ISO 12345", "clause 6.2.5", "§6.2", "table 6.1",
# "equation (6.10)"
_PROSE_CITATION_RE = re.compile(
    r"\b(?:EN|ISO|BS|ASTM|prEN)\s?\d[\d\-.]*"
    r"|\bclause\s+\d[\d.]*"
    r"|§\s?\d[\d.]*"
    r"|\b(?:table|figure|eq\.?|equation)\s*\(?\d[\d.]*\)?",
    re.IGNORECASE,
)
_CLAUSE_TOKEN_RE = re.compile(r"\d+(?:\.\d+){0,4}")


@dataclass
class Finding:
    code: str
    severity: str  # "ERROR" | "WARNING"
    location: str
    detail: str


@dataclass
class ValidationReport:
    question_id: str
    findings: list[Finding] = field(default_factory=list)

    def add(self, code: str, location: str, detail: str, severity: str = "ERROR") -> None:
        self.findings.append(Finding(code, severity, location, detail))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "ERROR"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def codes(self) -> list[str]:
        return sorted({f.code for f in self.findings})

    def as_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "ok": self.ok,
            "findings": [vars(f) for f in self.findings],
        }


def _check_schema(resp: object, report: ValidationReport) -> bool:
    """Fully validate the response against the committed
    ``schemas/scout_response.schema.json`` BEFORE any other code traverses
    model-produced data, so this can never drift from what the schema actually
    says. Untrusted output must always end up as a structured
    ``SCHEMA_INVALID`` result, never an exception - ``_jsonschema_lite.validate``
    never raises on ``resp``, only on a schema it can't interpret."""

    errors = _jsonschema_lite.validate(resp, _RESPONSE_SCHEMA)
    for path, msg in errors:
        report.add("SCHEMA_INVALID", path, msg)
    return not errors


def _iter_cited(resp: dict):
    """Yield (location, evidence_id) for every cited id. Only runs after
    ``_check_schema`` has passed, but stays defensive against odd values."""

    def ids(container: object) -> list:
        return [x for x in (container or []) if isinstance(x, str)]

    for i, req in enumerate(resp.get("requirements", []) or []):
        if isinstance(req, dict):
            for eid in ids(req.get("evidence_ids")):
                yield f"requirements[{i}]", eid
    for i, step in enumerate(resp.get("verification_procedure", []) or []):
        if isinstance(step, dict):
            for eid in ids(step.get("evidence_ids")):
                yield f"verification_procedure[{i}]", eid
    for i, conf in enumerate(resp.get("conflicts", []) or []):
        if isinstance(conf, dict):
            for eid in ids(conf.get("evidence_ids")):
                yield f"conflicts[{i}]", eid


def validate_response(
    resp: dict,
    packet: EvidencePacket,
    doc_meta: dict[str, DocumentMeta],
    chunk_index: dict[str, Chunk],
    *,
    question_id: str,
    issued_evidence_ids: set[str] | None = None,
) -> ValidationReport:
    """Run every deterministic check. ``issued_evidence_ids`` defaults to the
    ids in ``packet`` (the closed set for this question)."""

    report = ValidationReport(question_id=question_id)
    issued = issued_evidence_ids or set(packet.evidence_ids)
    packet_ids = set(packet.evidence_ids)

    schema_ok = _check_schema(resp, report)
    if not schema_ok:
        return report  # further checks would be noise (or unsafe) on a broken shape

    if resp.get("question_id") not in (None, question_id):
        report.add(
            "SCHEMA_INVALID",
            "question_id",
            f"response question_id {resp.get('question_id')!r} != {question_id!r}",
        )

    # --- citation integrity -------------------------------------------------
    for loc, eid in _iter_cited(resp):
        if eid not in issued:
            report.add("UNKNOWN_EVIDENCE_ID", loc, f"{eid!r} was never issued this run")
            continue
        if eid not in packet_ids:
            report.add("EVIDENCE_NOT_IN_RUN", loc, f"{eid!r} not in this question's packet")
            continue
        item = packet.by_id(eid)
        meta = doc_meta.get(item.document_id)
        if doc_meta and meta is None:
            report.add("DOC_ID_MISMATCH", loc, f"{eid}: unknown document_id {item.document_id!r}")
        chunk = chunk_index.get(item.chunk_id)
        if chunk is not None:
            if chunk.document_id != item.document_id:
                report.add(
                    "DOC_ID_MISMATCH",
                    loc,
                    f"{eid}: packet says {item.document_id!r}, chunk says {chunk.document_id!r}",
                )
            if chunk.page != item.page:
                report.add(
                    "PAGE_NOT_FOUND",
                    loc,
                    f"{eid}: packet page {item.page} != chunk page {chunk.page}",
                )
            if chunk.clause != UNKNOWN_CLAUSE and chunk.clause != item.clause:
                report.add(
                    "CLAUSE_MISMATCH",
                    loc,
                    f"{eid}: packet clause {item.clause!r} != chunk clause {chunk.clause!r}",
                )

    # --- support requirements --------------------------------------------------
    for i, req in enumerate(resp.get("requirements", []) or []):
        loc = f"requirements[{i}]"
        eids = req.get("evidence_ids", []) or []
        if not eids:
            report.add(
                "UNSUPPORTED_CLAIM",
                loc,
                f"requirement {req.get('claim_id')!r} ({req.get('classification')}) "
                f"cites no evidence",
            )
        _check_prose_citation(req.get("claim", ""), eids, packet, loc, report)

    for i, step in enumerate(resp.get("verification_procedure", []) or []):
        loc = f"verification_procedure[{i}]"
        eids = step.get("evidence_ids", []) or []
        if step.get("classification") == "EXPLICIT" and not eids:
            report.add(
                "MISSING_EVIDENCE",
                loc,
                f"step {step.get('step')} is EXPLICIT but cites no evidence",
            )
        _check_prose_citation(step.get("action", ""), eids, packet, loc, report)

    return report


def _check_prose_citation(
    text: str,
    cited_ids: list[str],
    packet: EvidencePacket,
    loc: str,
    report: ValidationReport,
) -> None:
    """If free text names a standard/clause/table/equation, at least one cited
    evidence item must plausibly carry it."""

    for hit in _PROSE_CITATION_RE.findall(text or ""):
        tokens = set(_CLAUSE_TOKEN_RE.findall(hit))
        backed = False
        for eid in cited_ids:
            item = packet.by_id(eid)
            if item is None:
                continue
            hay = f"{item.clause} {item.text}".lower()
            if hit.lower() in hay or (tokens and any(t in hay for t in tokens)):
                backed = True
                break
        if not backed:
            report.add(
                "PROSE_CITATION_UNBACKED",
                loc,
                f"free-text reference {hit!r} not found in any cited evidence item",
            )
