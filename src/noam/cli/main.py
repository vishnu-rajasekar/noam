"""``noam`` CLI. Argparse, not Typer/Click: it must run with zero extra
dependencies beyond the stdlib + Pydantic + PyYAML, on a freshly copied
work-PC checkout, before ``uv sync`` has necessarily been run (see the
migration report for why Typer was deferred rather than adopted tonight).
"""

from __future__ import annotations

import argparse
import sys

from pydantic import ValidationError

from noam.models import Capability, Experiment, Insight, ModelHypothesis, Requirement, Study
from noam.models.common import Confidentiality, Domain, ProjectStage
from noam.registry import index as index_mod
from noam.registry import paths, store
from noam.registry.validate import validate_registry
from noam.studies.scaffold import create_study
from noam.utils.ids import existing_ids_in, next_id


def _err(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


# -- study ---------------------------------------------------------------


def cmd_study_new(args: argparse.Namespace) -> int:
    study_id = args.id or next_id("S", [s.id for s in store.list_studies()], dashed=False)
    try:
        study = Study(
            id=study_id,
            title=args.title,
            domain=Domain(args.domain),
            project_stage=ProjectStage(args.stage),
            confidentiality=Confidentiality(args.confidentiality),
            engineering_question=args.question,
            decision_required=args.decision,
            jurisdiction=args.jurisdiction or "unknown",
        )
    except ValidationError as exc:
        return _err(str(exc))
    try:
        directory = create_study(study, slug=args.slug)
    except FileExistsError as exc:
        return _err(str(exc))
    print(f"created {study.id} at {directory.relative_to(paths.repo_root())}")
    return 0


def cmd_study_list(args: argparse.Namespace) -> int:
    studies = store.list_studies()
    if args.domain:
        studies = [s for s in studies if s.domain.value == args.domain]
    if args.status:
        studies = [s for s in studies if s.status.value == args.status]
    if args.stage:
        studies = [s for s in studies if s.project_stage.value == args.stage]
    if not studies:
        print("no studies found")
        return 0
    for s in studies:
        print(f"{s.id}  [{s.domain.value}]  {s.status.value:9s}  stage {s.project_stage.value:7s}  {s.title}")
    return 0


def cmd_study_show(args: argparse.Namespace) -> int:
    try:
        study = store.load_study(args.study_id)
    except FileNotFoundError as exc:
        return _err(str(exc))
    directory = paths.find_study_dir(study.id)
    print(f"{study.id} — {study.title}")
    print(f"  domain:            {study.domain.value}")
    print(f"  status:            {study.status.value}")
    print(f"  project_stage:     {study.project_stage.value}")
    print(f"  confidentiality:   {study.confidentiality.value}")
    print(f"  jurisdiction:      {study.jurisdiction}")
    print(f"  engineering_question: {study.engineering_question}")
    print(f"  decision_required:    {study.decision_required}")
    print(f"  folder:            {directory}")
    return 0


# -- requirement / hypothesis / experiment / insight / capability --------


def cmd_requirement_add(args: argparse.Namespace) -> int:
    directory = paths.find_study_dir(args.study_id)
    if directory is None:
        return _err(f"no study directory found for {args.study_id}")
    req_dir = directory / "requirements"
    req_id = next_id("REQ", existing_ids_in(req_dir))
    req = Requirement(
        id=req_id,
        study_id=args.study_id,
        title=args.title,
        description=args.description or "",
        category=args.category or "",
    )
    store.save_record(req, req_dir / f"{req_id}.yaml")
    store.append_study_ref(args.study_id, "requirement", req_id)
    print(f"created {req_id} in {req_dir.relative_to(paths.repo_root())}")
    return 0


def cmd_hypothesis_new(args: argparse.Namespace) -> int:
    directory = paths.find_study_dir(args.study_id)
    if directory is None:
        return _err(f"no study directory found for {args.study_id}")
    model_dir = directory / "model"
    mh_id = next_id("MH", existing_ids_in(model_dir))
    mh = ModelHypothesis(
        id=mh_id,
        study_id=args.study_id,
        purpose=args.purpose,
        analysis_question=args.question,
    )
    store.save_record(mh, model_dir / f"{mh_id}.yaml")
    store.append_study_ref(args.study_id, "model_hypothesis", mh_id)
    print(f"created {mh_id} in {model_dir.relative_to(paths.repo_root())}")
    return 0


def cmd_experiment_new(args: argparse.Namespace) -> int:
    directory = paths.find_study_dir(args.study_id)
    if directory is None:
        return _err(f"no study directory found for {args.study_id}")
    exp_dir = directory / "experiments"
    exp_id = next_id("EXP", existing_ids_in(exp_dir))
    try:
        exp = Experiment(
            id=exp_id,
            study_id=args.study_id,
            model_hypothesis_id=args.model_hypothesis_id,
            title=args.title,
        )
    except ValidationError as exc:
        return _err(str(exc))
    store.save_record(exp, exp_dir / f"{exp_id}.yaml")
    store.append_study_ref(args.study_id, "experiment", exp_id)
    print(f"created {exp_id} in {exp_dir.relative_to(paths.repo_root())}")
    return 0


def cmd_insight_add(args: argparse.Namespace) -> int:
    directory = paths.find_study_dir(args.study_id)
    if directory is None:
        return _err(f"no study directory found for {args.study_id}")
    ins_dir = directory / "insights"
    ins_id = next_id("INS", existing_ids_in(ins_dir))
    ins = Insight(id=ins_id, study_id=args.study_id, statement=args.statement)
    store.save_record(ins, ins_dir / f"{ins_id}.yaml")
    store.append_study_ref(args.study_id, "insight", ins_id)
    print(f"created {ins_id} in {ins_dir.relative_to(paths.repo_root())}")
    return 0


def cmd_capability_new(args: argparse.Namespace) -> int:
    cap_dir = paths.domain_capabilities_dir(args.domain)
    cap_id = next_id("CAP", existing_ids_in(cap_dir))
    cap = Capability(
        id=cap_id,
        domain=Domain(args.domain),
        name=args.name,
        purpose=args.purpose,
    )
    store.save_record(cap, cap_dir / f"{cap_id}.yaml")
    print(f"created {cap_id} in {cap_dir.relative_to(paths.repo_root())}")
    return 0


# -- registry --------------------------------------------------------------


def cmd_registry_validate(args: argparse.Namespace) -> int:
    report = validate_registry()
    if report.ok:
        print("registry valid: no problems found")
        return 0
    print(f"registry INVALID: {len(report.problems)} problem(s)")
    for p in report.problems:
        print(f"  - {p}")
    return 1


def cmd_registry_index(args: argparse.Namespace) -> int:
    result = index_mod.build_index()
    print(
        f"indexed {result.studies} studies, {result.capabilities} capabilities, "
        f"{result.precedents} precedents, {result.insights} insights "
        f"-> {paths.index_db_path().relative_to(paths.repo_root())}"
    )
    return 0


# -- search ------------------------------------------------------------


def _print_rows(rows: list[dict]) -> None:
    if not rows:
        print("no matches")
        return
    for row in rows:
        print("  ".join(f"{k}={v}" for k, v in row.items()))


def cmd_search(args: argparse.Namespace) -> int:
    filters = {}
    if args.domain:
        filters["domain"] = args.domain
    if args.status and args.table in ("studies", "capabilities"):
        filters["status"] = args.status
    try:
        rows = index_mod.search(args.table, **filters)
    except ValueError as exc:
        return _err(str(exc))
    _print_rows(rows)
    return 0


# -- parser ----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="noam", description="Noam engineering orchestrator CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    study = sub.add_parser("study", help="manage studies")
    study_sub = study.add_subparsers(dest="study_command", required=True)

    p = study_sub.add_parser("new", help="create a new study")
    p.add_argument("--id", default=None, help="e.g. S002 (default: next available)")
    p.add_argument("--title", required=True)
    p.add_argument("--slug", default=None, help="short folder slug, e.g. airport_cw (default: derived from title)")
    p.add_argument("--domain", required=True, choices=[d.value for d in Domain])
    p.add_argument("--stage", default="unknown", choices=[s.value for s in ProjectStage])
    p.add_argument("--confidentiality", default="internal", choices=[c.value for c in Confidentiality])
    p.add_argument("--question", required=True, dest="question")
    p.add_argument("--decision", required=True, dest="decision")
    p.add_argument("--jurisdiction", default=None)
    p.set_defaults(func=cmd_study_new)

    p = study_sub.add_parser("list", help="list studies")
    p.add_argument("--domain", default=None, choices=[d.value for d in Domain])
    p.add_argument("--status", default=None)
    p.add_argument("--stage", default=None, choices=[s.value for s in ProjectStage])
    p.set_defaults(func=cmd_study_list)

    p = study_sub.add_parser("show", help="show one study")
    p.add_argument("study_id")
    p.set_defaults(func=cmd_study_show)

    p = sub.add_parser("requirement", help="manage requirements").add_subparsers(dest="req_command", required=True) \
        .add_parser("add", help="add a requirement to a study")
    p.add_argument("study_id")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default=None)
    p.add_argument("--category", default=None)
    p.set_defaults(func=cmd_requirement_add)

    p = sub.add_parser("hypothesis", help="manage model hypotheses").add_subparsers(dest="mh_command", required=True) \
        .add_parser("new", help="create a model hypothesis for a study")
    p.add_argument("study_id")
    p.add_argument("--purpose", required=True)
    p.add_argument("--question", required=True)
    p.set_defaults(func=cmd_hypothesis_new)

    p = sub.add_parser("experiment", help="manage experiments").add_subparsers(dest="exp_command", required=True) \
        .add_parser("new", help="create an experiment for a study")
    p.add_argument("study_id")
    p.add_argument("--title", required=True)
    p.add_argument(
        "--model-hypothesis-id",
        required=True,
        dest="model_hypothesis_id",
        help="the reviewed ModelHypothesis this experiment runs against, e.g. MH-001",
    )
    p.set_defaults(func=cmd_experiment_new)

    p = sub.add_parser("insight", help="manage insights").add_subparsers(dest="ins_command", required=True) \
        .add_parser("add", help="add an insight to a study")
    p.add_argument("study_id")
    p.add_argument("--statement", required=True)
    p.set_defaults(func=cmd_insight_add)

    p = sub.add_parser("capability", help="manage capabilities").add_subparsers(dest="cap_command", required=True) \
        .add_parser("new", help="create a capability")
    p.add_argument("--domain", required=True, choices=[d.value for d in Domain])
    p.add_argument("--name", required=True)
    p.add_argument("--purpose", required=True)
    p.set_defaults(func=cmd_capability_new)

    registry = sub.add_parser("registry", help="registry maintenance")
    registry_sub = registry.add_subparsers(dest="registry_command", required=True)
    p = registry_sub.add_parser("validate", help="validate all authoring files")
    p.set_defaults(func=cmd_registry_validate)
    p = registry_sub.add_parser("index", help="rebuild the local search index")
    p.set_defaults(func=cmd_registry_index)

    search = sub.add_parser("search", help="structured search over the index")
    search_sub = search.add_subparsers(dest="search_target", required=True)
    for target in ("studies", "capabilities", "precedents", "insights"):
        p = search_sub.add_parser(target, help=f"search {target}")
        p.add_argument("--domain", default=None)
        p.add_argument("--status", default=None)
        p.set_defaults(func=cmd_search, table=target)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
