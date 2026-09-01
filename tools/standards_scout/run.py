"""Pipeline orchestrator: ingest -> retrieve -> run -> validate -> evaluate,
plus a reproducibility manifest and repeated-run stability for probe questions.

Everything is offline unless ``--runner ollama`` is chosen (which needs loopback
network and cannot run inside the Noam sandbox).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from dataclasses import asdict
from pathlib import Path

from . import PROMPT_VERSION, RESPONSE_SCHEMA_VERSION, __version__
from ._loaders import load_structured, resolve_one
from .evaluate import score_question
from .ingest import ingest_library
from .interfaces import Chunk, DocumentMeta, ScoutRequest, sha256_text
from .qwen_runner import make_runner
from .report import render_question_report, render_summary
from .retrieve import LexicalRetriever, build_packet
from .validate import validate_response

_HERE = Path(__file__).parent
_SCHEMA_PATH = _HERE / "schemas" / "scout_response.schema.json"
_PROMPT_PATH = _HERE / "prompts" / f"system_prompt_{PROMPT_VERSION}.md"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def _restricted_ancestor(path: Path) -> Path | None:
    """Nearest ancestor of ``path`` that is a ``knowledge/restricted`` tree."""

    parts = path.resolve().parts
    for i in range(len(parts) - 1):
        if parts[i].lower() == "knowledge" and parts[i + 1].lower() == "restricted":
            return Path(*parts[: i + 2])
    return None


class RestrictedOutputError(SystemExit):
    """Raised (fail-closed) when a run would write outside its restricted input
    boundary - never let restricted-derived evidence land in the worktree."""


def _confinement_and_out(args: argparse.Namespace, inputs: list[Path], run_ts: str) -> Path:
    """Decide the output directory and enforce that a restricted run stays
    inside its boundary. Returns the resolved (not yet created) out dir."""

    if args.root:
        confine: Path | None = Path(args.root)
    else:
        confine = next((a for a in map(_restricted_ancestor, inputs) if a is not None), None)

    stamp = run_ts.replace(":", "").replace("-", "")
    if args.out:
        out_dir = Path(args.out)
    elif args.root:
        out_dir = Path(args.root) / "runs" / stamp
    elif confine is not None:
        out_dir = confine / "standards_scout" / "runs" / stamp
    else:
        out_dir = Path("./_scout_out")

    if confine is not None and not _path_within(out_dir, confine):
        raise RestrictedOutputError(
            f"refusing to run: output {out_dir} is outside the restricted input "
            f"boundary {confine}. Restricted runs must write only inside that tree "
            f"(pass --out to a path within it, or omit --out for the default "
            f"'{confine}/.../runs/<timestamp>')."
        )
    return out_dir


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    if args.root:
        root = Path(args.root)
        return (
            root / "documents",
            resolve_one(root / "metadata", "documents.yaml", "documents.json"),
            resolve_one(root / "ground_truth", "airport_eval.yaml", "airport_eval.json"),
        )
    return Path(args.docs), Path(args.metadata), Path(args.ground_truth)


def run(args: argparse.Namespace) -> dict:
    run_ts = _now()
    docs_dir, metadata_path, gt_path = _resolve_paths(args)
    out_dir = _confinement_and_out(args, [docs_dir, metadata_path, gt_path], run_ts)
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt_hash = sha256_text(system_prompt)
    schema_hash = sha256_text(json.dumps(schema, sort_keys=True))

    chunks, metas, limitations = ingest_library(docs_dir, metadata_path)
    chunk_index: dict[str, Chunk] = {c.chunk_id: c for c in chunks}
    doc_meta: dict[str, DocumentMeta] = {m.document_id: m for m in metas}

    retriever = LexicalRetriever()
    retriever.index(chunks)

    gt_raw = gt_path.read_text(encoding="utf-8")
    gt_doc = load_structured(gt_path) or {}
    questions = gt_doc.get("questions", [])

    runner = make_runner(
        args.runner,
        responses_dir=Path(args.stub_responses) if args.stub_responses else None,
        base_url=args.base_url,
        model=args.model,
        provider_label=args.provider_label,
    )

    manifest: dict = {
        "timestamp": run_ts,
        "output_dir": str(out_dir),
        "harness_version": __version__,
        "runner": {
            "kind": args.runner,
            "provider_label": runner.provider_label,
            "model_id": runner.model_id,
            "provider_is_local": runner.provider_is_local,
            "generation_settings": runner.generation_settings,
            "base_url": getattr(runner, "base_url", None),
        },
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": prompt_hash,
        "response_schema_version": RESPONSE_SCHEMA_VERSION,
        "response_schema_sha256": schema_hash,
        "retrieval_method": retriever.method_name,
        "retrieval_params": {"k": args.k},
        "documents": [
            {"document_id": m.document_id, "sha256": m.sha256, "type": m.document_type}
            for m in metas
        ],
        "ground_truth_sha256": sha256_text(gt_raw),
        "ground_truth_version": gt_doc.get("dataset_version"),
        "extraction_limitations": limitations,
        "questions": [],
    }

    outcomes = []
    for gt in questions:
        qid = gt["question_id"]
        query = gt["question"]
        packet = build_packet(retriever, query, args.k, run_id=f"{qid}@{manifest['timestamp']}")
        request = ScoutRequest(
            question_id=qid,
            question=query,
            project_context=gt.get("project_context", ""),
            packet=packet,
            system_prompt=system_prompt,
            system_prompt_version=PROMPT_VERSION,
            response_schema=schema,
            response_schema_version=RESPONSE_SCHEMA_VERSION,
        )

        reps = args.repeats if gt.get("stability_probe") else 1
        rep_records = []
        for rep in range(reps):
            resp = runner.run(request)
            report = validate_response(
                resp, packet, doc_meta, chunk_index, question_id=qid
            )
            outcome = score_question(resp, report, packet, gt)
            rep_records.append(
                {
                    "rep": rep,
                    "raw_response": resp,
                    "validation": report.as_dict(),
                    "scores": {
                        "limiting_factor": outcome.limiting_factor,
                        "retrieval": asdict(outcome.retrieval),
                        "answer": asdict(outcome.answer),
                        "notes": outcome.notes,
                    },
                }
            )
            if rep == 0:
                (out_dir / f"{qid}.md").write_text(
                    render_question_report(gt, packet, resp, report, outcome),
                    encoding="utf-8",
                )
                outcomes.append(outcome)

        manifest["questions"].append(
            {
                "question_id": qid,
                "query": query,
                "retrieved_evidence_ids": packet.evidence_ids,
                "evidence": [asdict(i) for i in packet.items],
                "repetitions": rep_records,
                "stability": _stability(rep_records) if reps > 1 else None,
            }
        )

    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "summary.md").write_text(render_summary(outcomes), encoding="utf-8")
    return manifest


def _stability(rep_records: list[dict]) -> dict:
    statuses = {
        r["raw_response"].get("status") if isinstance(r["raw_response"], dict) else None
        for r in rep_records
    }
    cited = {
        tuple(sorted(_all_cited(r["raw_response"]))) for r in rep_records
    }
    unsupported_counts = {
        r["scores"]["answer"]["unsupported_claim_count"] for r in rep_records
    }
    return {
        "status_changes": len(statuses) > 1,
        "statuses_seen": sorted(s for s in statuses if s),
        "cited_evidence_changes": len(cited) > 1,
        "unsupported_claims_intermittent": len(unsupported_counts) > 1,
        "unsupported_claim_counts": sorted(unsupported_counts),
    }


def _all_cited(resp: object) -> set[str]:
    out: set[str] = set()
    if not isinstance(resp, dict):
        return out
    for key in ("requirements", "verification_procedure"):
        seq = resp.get(key)
        if not isinstance(seq, list):
            continue
        for entry in seq:
            if isinstance(entry, dict) and isinstance(entry.get("evidence_ids"), list):
                out.update(x for x in entry["evidence_ids"] if isinstance(x, str))
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Standards Scout evaluation pipeline")
    ap.add_argument("--root", help="restricted layout root (documents/, metadata/, ground_truth/)")
    ap.add_argument("--docs", help="documents directory (if --root not given)")
    ap.add_argument("--metadata", help="documents.yaml (if --root not given)")
    ap.add_argument("--ground-truth", dest="ground_truth", help="ground truth yaml")
    ap.add_argument(
        "--out",
        default=None,
        help="output directory. Default: '<root>/runs/<ts>' in --root mode, "
        "'<restricted-tree>/standards_scout/runs/<ts>' if inputs are restricted, "
        "else './_scout_out'. A restricted run refuses an --out outside its tree.",
    )
    ap.add_argument("--k", type=int, default=10, help="evidence packet size")
    ap.add_argument("--repeats", type=int, default=3, help="reps for stability_probe questions")
    ap.add_argument("--runner", choices=["stub", "ollama"], default="stub")
    ap.add_argument("--stub-responses", help="dir of <question_id>.json canned responses")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--model", default="qwen3:4b")
    ap.add_argument("--provider-label", default="ollama-openai-compat")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.root and not (args.docs and args.metadata and args.ground_truth):
        build_parser().error("give --root, or all of --docs --metadata --ground-truth")
    manifest = run(args)
    print(
        f"wrote {manifest['output_dir']}/run_manifest.json  "
        f"({len(manifest['questions'])} questions)"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
