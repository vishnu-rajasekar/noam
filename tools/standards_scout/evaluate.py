"""Evaluation - retrieval and reasoning measured *separately*.

Retrieval evaluation asks: was the expected evidence in the packet at all?
Answer evaluation asks: given whatever was retrieved, did the model cite
supportably, cover the expected concepts, abstain correctly, and avoid
unacceptable claims?

When expected evidence is absent from the packet, a downstream answer failure is
attributed to RETRIEVAL_FAILURE, not to model reasoning. Semantic "does this
clause truly support this claim" is left to the engineer - not scored here, and
never scored by the model itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .interfaces import EvidencePacket
from .validate import ValidationReport


@dataclass
class RetrievalScore:
    question_id: str
    expected_doc_clause: list[tuple[str, str]]
    expected_docs: list[str]
    recall_at_5: float
    recall_at_10: float
    mrr: float
    matched: list[str]
    missing: list[str]

    @property
    def any_expected(self) -> bool:
        return bool(self.expected_doc_clause or self.expected_docs)

    @property
    def full_recall(self) -> bool:
        return self.any_expected and not self.missing


@dataclass
class AnswerScore:
    question_id: str
    status: str
    expected_status: list[str]
    status_ok: bool
    concept_coverage: float
    concepts_hit: list[str]
    concepts_missed: list[str]
    unsupported_claim_count: int
    unacceptable_claim_hits: list[str]
    correct_abstention: bool
    incorrect_abstention: bool
    formula_match: bool | None
    citation_ok: bool


@dataclass
class QuestionOutcome:
    question_id: str
    limiting_factor: str  # RETRIEVAL_FAILURE | ANSWER_FAILURE | OK | UNCERTAIN
    retrieval: RetrievalScore
    answer: AnswerScore
    notes: list[str] = field(default_factory=list)


def _clause_key(document_id: str, clause: str) -> str:
    return f"{document_id}::{clause}".lower()


def evaluate_retrieval(
    packet: EvidencePacket,
    expected_doc_clause: list[tuple[str, str]],
    expected_docs: list[str],
    question_id: str,
) -> RetrievalScore:
    ranked = packet.items  # already best-first

    def hit_rank(pred) -> int | None:
        for idx, item in enumerate(ranked, start=1):
            if pred(item):
                return idx
        return None

    targets: list[tuple[str, object]] = []
    for doc_id, clause in expected_doc_clause:
        key = _clause_key(doc_id, clause)
        targets.append(
            (
                f"{doc_id} {clause}",
                lambda it, key=key: _clause_key(it.document_id, it.clause) == key,
            )
        )
    for doc_id in expected_docs:
        targets.append(
            (doc_id, lambda it, d=doc_id: it.document_id.lower() == d.lower())
        )

    ranks = {label: hit_rank(pred) for label, pred in targets}
    matched = [lbl for lbl, r in ranks.items() if r is not None]
    missing = [lbl for lbl, r in ranks.items() if r is None]
    total = len(targets) or 1

    def recall_at(k: int) -> float:
        got = sum(1 for r in ranks.values() if r is not None and r <= k)
        return round(got / total, 4)

    first_ranks = [r for r in ranks.values() if r is not None]
    mrr = round(sum(1.0 / r for r in first_ranks) / total, 4) if first_ranks else 0.0

    return RetrievalScore(
        question_id=question_id,
        expected_doc_clause=expected_doc_clause,
        expected_docs=expected_docs,
        recall_at_5=recall_at(5),
        recall_at_10=recall_at(10),
        mrr=mrr,
        matched=matched,
        missing=missing,
    )


def evaluate_answer(
    resp: dict,
    report: ValidationReport,
    gt: dict,
    question_id: str,
) -> AnswerScore:
    if not isinstance(resp, dict):
        resp = {}
    status = resp.get("status", "")
    if not isinstance(status, str):
        status = ""
    expected_status = list(gt.get("expected_status", []))
    answerable = bool(gt.get("answerability", {}).get("answerable", True))

    haystack = _response_text(resp).lower()
    concepts = [c for c in gt.get("expected_concepts", []) if c.strip()]
    hit = [c for c in concepts if c.lower() in haystack]
    missed = [c for c in concepts if c.lower() not in haystack]
    coverage = round(len(hit) / len(concepts), 4) if concepts else 0.0

    unacceptable_hits = [
        bad for bad in gt.get("unacceptable_claims", []) if bad.lower() in haystack
    ]

    unsupported = sum(
        1
        for f in report.findings
        if f.code in {"UNSUPPORTED_CLAIM", "PROSE_CITATION_UNBACKED", "MISSING_EVIDENCE"}
    )

    abstained = status == "INSUFFICIENT_EVIDENCE"
    correct_abstention = abstained and not answerable
    incorrect_abstention = abstained and answerable

    formula = gt.get("expected_formula")
    formula_match: bool | None
    if formula:
        formula_match = _normalise(formula) in _normalise(_response_text(resp))
    else:
        formula_match = None

    citation_ok = not any(
        f.code
        in {
            "UNKNOWN_EVIDENCE_ID",
            "EVIDENCE_NOT_IN_RUN",
            "DOC_ID_MISMATCH",
            "PAGE_NOT_FOUND",
            "CLAUSE_MISMATCH",
        }
        for f in report.findings
    )

    return AnswerScore(
        question_id=question_id,
        status=status,
        expected_status=expected_status,
        status_ok=status in expected_status if expected_status else False,
        concept_coverage=coverage,
        concepts_hit=hit,
        concepts_missed=missed,
        unsupported_claim_count=unsupported,
        unacceptable_claim_hits=unacceptable_hits,
        correct_abstention=correct_abstention,
        incorrect_abstention=incorrect_abstention,
        formula_match=formula_match,
        citation_ok=citation_ok,
    )


def classify_limiting_factor(
    retrieval: RetrievalScore, answer: AnswerScore, validation_ok: bool
) -> tuple[str, list[str]]:
    notes: list[str] = []
    answerable_expected = "INSUFFICIENT_EVIDENCE" not in answer.expected_status or len(
        answer.expected_status
    ) > 1

    if retrieval.any_expected and retrieval.missing:
        notes.append(f"expected evidence not retrieved: {', '.join(retrieval.missing)}")
        return "RETRIEVAL_FAILURE", notes

    answer_bad = (
        not answer.status_ok
        or not validation_ok
        or answer.unacceptable_claim_hits
        or answer.incorrect_abstention
        or (answer.formula_match is False)
    )
    if answer_bad:
        if not answer.status_ok:
            notes.append(f"status {answer.status!r} not in expected {answer.expected_status}")
        if not validation_ok:
            notes.append("deterministic validation failed")
        if answer.unacceptable_claim_hits:
            notes.append(f"unacceptable claim(s): {answer.unacceptable_claim_hits}")
        if answer.incorrect_abstention:
            notes.append("abstained on an answerable question")
        if answer.formula_match is False:
            notes.append("expected formula not reproduced")
        return "ANSWER_FAILURE", notes

    if not retrieval.any_expected and answerable_expected:
        notes.append("no expected evidence defined; cannot separate retrieval from reasoning")
        return "UNCERTAIN", notes

    return "OK", notes


def score_question(
    resp: dict,
    report: ValidationReport,
    packet: EvidencePacket,
    gt: dict,
) -> QuestionOutcome:
    qid = gt["question_id"]
    exp = gt.get("expected_evidence", {}) or {}
    doc_clause = [
        (c["document_id"], c["clause"]) for c in exp.get("clauses", []) or []
    ]
    docs = list(exp.get("documents", []) or [])
    retrieval = evaluate_retrieval(packet, doc_clause, docs, qid)
    answer = evaluate_answer(resp, report, gt, qid)
    factor, notes = classify_limiting_factor(retrieval, answer, report.ok)
    return QuestionOutcome(
        question_id=qid,
        limiting_factor=factor,
        retrieval=retrieval,
        answer=answer,
        notes=notes,
    )


def _response_text(resp: object) -> str:
    """Flatten model-produced text for substring scoring. Never raises on a
    malformed response - it just yields less text."""

    if not isinstance(resp, dict):
        return ""
    parts: list[str] = []

    def as_list(value: object) -> list:
        return value if isinstance(value, list) else []

    def as_strs(value: object) -> list[str]:
        return [str(x) for x in as_list(value)]

    for req in as_list(resp.get("requirements")):
        if not isinstance(req, dict):
            continue
        parts.append(str(req.get("claim", "")))
        parts += as_strs(req.get("applicability_conditions"))
        parts += as_strs(req.get("uncertainties"))
    for step in as_list(resp.get("verification_procedure")):
        if isinstance(step, dict):
            parts.append(str(step.get("action", "")))
    parts += as_strs(resp.get("missing_information"))
    for conf in as_list(resp.get("conflicts")):
        if isinstance(conf, dict):
            parts.append(str(conf.get("description", "")))
    return "\n".join(parts)


def _normalise(text: str) -> str:
    return "".join(ch for ch in text.lower() if not ch.isspace())
