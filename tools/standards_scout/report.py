"""Per-question side-by-side review report for the engineer.

Deliberately shows only local document/page/clause references plus short evidence
excerpts - not large blocks of copyrighted standard text.
"""

from __future__ import annotations

from .evaluate import QuestionOutcome
from .interfaces import EvidencePacket
from .validate import ValidationReport

_EXCERPT = 240


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _EXCERPT else text[:_EXCERPT] + " ..."


def render_question_report(
    gt: dict,
    packet: EvidencePacket,
    resp: dict,
    report: ValidationReport,
    outcome: QuestionOutcome,
) -> str:
    qid = gt["question_id"]
    lines: list[str] = [f"# {qid}", "", "## QUESTION", gt["question"].strip(), ""]
    if gt.get("project_context"):
        lines += ["## PROJECT CONTEXT", gt["project_context"].strip(), ""]

    lines += ["## GROUND TRUTH", ""]
    exp = gt.get("expected_evidence", {}) or {}
    lines.append(f"- answerable: {gt.get('answerability', {}).get('answerable')}")
    lines.append(f"- expected status: {', '.join(gt.get('expected_status', []))}")
    if exp.get("documents"):
        lines.append(f"- expected documents: {', '.join(exp['documents'])}")
    for c in exp.get("clauses", []) or []:
        lines.append(f"- expected clause: {c['document_id']} {c['clause']}")
    for concept in gt.get("expected_concepts", []) or []:
        lines.append(f"- expected concept: {concept}")
    for bad in gt.get("unacceptable_claims", []) or []:
        lines.append(f"- unacceptable claim: {bad}")
    if gt.get("expected_formula"):
        lines.append(f"- expected formula: {gt['expected_formula']}")
    lines.append("")

    lines += ["## RETRIEVED EVIDENCE", ""]
    if not packet.items:
        lines.append("_(none retrieved)_")
    for item in packet.items:
        lines.append(
            f"- **{item.evidence_id}** rank-scored {item.retrieval_score} | "
            f"{item.document_id} p{item.page} clause {item.clause} "
            f"(`{item.chunk_id}`)"
        )
        lines.append(f"  > {_excerpt(item.text)}")
    lines.append("")

    if not isinstance(resp, dict):
        resp = {}

    def _list(value: object) -> list:
        return value if isinstance(value, list) else []

    lines += ["## QWEN OUTPUT", "", f"- status: **{resp.get('status')}**"]
    for req in _list(resp.get("requirements")):
        if not isinstance(req, dict):
            lines.append(f"- (malformed requirement entry: {req!r})")
            continue
        lines.append(
            f"- claim `{req.get('claim_id')}` [{req.get('classification')}] "
            f"evidence {req.get('evidence_ids')}: {_excerpt(str(req.get('claim', '')))}"
        )
    for step in _list(resp.get("verification_procedure")):
        if not isinstance(step, dict):
            lines.append(f"- (malformed procedure entry: {step!r})")
            continue
        lines.append(
            f"- step {step.get('step')} [{step.get('classification')}] "
            f"evidence {step.get('evidence_ids')}: {_excerpt(str(step.get('action', '')))}"
        )
    for mi in _list(resp.get("missing_information")):
        lines.append(f"- missing_information: {mi}")
    for conf in _list(resp.get("conflicts")):
        if not isinstance(conf, dict):
            lines.append(f"- (malformed conflict entry: {conf!r})")
            continue
        lines.append(f"- conflict {conf.get('evidence_ids')}: {conf.get('description')}")
    lines.append("")

    lines += ["## VALIDATOR FINDINGS", ""]
    if not report.findings:
        lines.append("_none - citation integrity checks passed_")
    for f in report.findings:
        lines.append(f"- **{f.severity} {f.code}** at `{f.location}` - {f.detail}")
    lines.append("")

    a = outcome.answer
    r = outcome.retrieval
    lines += [
        "## SCORES",
        "",
        f"- limiting factor: **{outcome.limiting_factor}**",
        f"- retrieval Recall@5 {r.recall_at_5} | Recall@10 {r.recall_at_10} | MRR {r.mrr}",
        f"- retrieval missing: {', '.join(r.missing) or 'none'}",
        f"- status expected {a.expected_status} got {a.status} -> {'OK' if a.status_ok else 'MISMATCH'}",
        f"- concept coverage: {a.concept_coverage} (missed: {', '.join(a.concepts_missed) or 'none'})",
        f"- unsupported claims: {a.unsupported_claim_count}",
        f"- unacceptable claim hits: {', '.join(a.unacceptable_claim_hits) or 'none'}",
        f"- correct abstention: {a.correct_abstention} | incorrect abstention: {a.incorrect_abstention}",
        f"- formula match: {a.formula_match}",
    ]
    for note in outcome.notes:
        lines.append(f"- note: {note}")
    lines += [
        "",
        "## ENGINEER VERDICT",
        "",
        "- [ ] correct",
        "- [ ] partially correct",
        "- [ ] incorrect",
        "- [ ] dangerous",
        "",
        "Engineer notes:",
        "",
        "> ",
        "",
    ]
    return "\n".join(lines)


def render_summary(outcomes: list[QuestionOutcome]) -> str:
    n = len(outcomes) or 1
    by_factor: dict[str, int] = {}
    for o in outcomes:
        by_factor[o.limiting_factor] = by_factor.get(o.limiting_factor, 0) + 1
    correct_abst = sum(1 for o in outcomes if o.answer.correct_abstention)
    false_abst = sum(1 for o in outcomes if o.answer.incorrect_abstention)
    unsupported = sum(o.answer.unsupported_claim_count for o in outcomes)
    dangerous = sum(1 for o in outcomes if o.answer.unacceptable_claim_hits)
    mean_r5 = round(sum(o.retrieval.recall_at_5 for o in outcomes) / n, 4)

    lines = [
        "# Standards Scout run summary",
        "",
        f"- questions: {len(outcomes)}",
        f"- mean Recall@5: {mean_r5}",
        f"- limiting factor: {by_factor}",
        f"- successful abstentions: {correct_abst}",
        f"- false abstentions: {false_abst}",
        f"- total unsupported/unbacked claims: {unsupported}",
        f"- answers containing an unacceptable claim: {dangerous}",
        "",
        "| question | limiting factor | R@5 | status ok | unsupported | dangerous |",
        "|---|---|---|---|---|---|",
    ]
    for o in outcomes:
        lines.append(
            f"| {o.question_id} | {o.limiting_factor} | {o.retrieval.recall_at_5} | "
            f"{o.answer.status_ok} | {o.answer.unsupported_claim_count} | "
            f"{'YES' if o.answer.unacceptable_claim_hits else ''} |"
        )
    return "\n".join(lines)
