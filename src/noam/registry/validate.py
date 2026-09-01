"""``noam registry validate`` -- re-parses every authoring file through its
Pydantic model and checks cross-references. Raises no exceptions itself;
callers (the CLI) decide how to report a non-empty problem list.

Phase A closure (2026-09-02) closed several traceability gaps found on
inspection: filename/id mismatches and duplicate ids were invisible, Insight
and Evidence records were not cross-checked (Evidence was not even loaded),
Result.capability_id and Experiment.capability_ids were never checked
against real Capability records, and an Experiment could reference a
ModelHypothesis that had never actually been reviewed -- letting an
unapproved draft masquerade as the idealisation that governed a result.

The 2026-09-02 review round 1 closed four more: bare child ids are now
unique across every study (not only within one); a promoted Capability or
Precedent's declared ``domain`` must match the ``domains/<domain>/``
directory it is filed under; a Result's ``capability_id`` must be one its
own Experiment declared (when the Experiment lists any); and the
``Study.<x>_ids`` convenience index is reconciled against the authoritative
child files on disk (an empty study with no children still reconciles).
All of those are checked below.

Review round 3 (2026-09-02) closed two more: a domain-scoped reference
(``Study``/``Experiment``/``Result`` capability, ``Study`` precedent) whose
target lives in a different domain than the containing study is now
rejected instead of passing on bare-id existence alone; and a malformed
authoring YAML file is reported as a path-specific problem -- the scan
continues over the remaining files and the CLI exits non-zero -- rather
than raising an uncaught parser traceback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from noam.models import (
    Capability,
    Evidence,
    Experiment,
    Insight,
    ModelHypothesis,
    Precedent,
    Requirement,
    Result,
    Study,
)
from noam.models.common import ApprovalStatus
from noam.registry import paths, store


@dataclass
class ValidationReport:
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


@dataclass
class _Loaded:
    """One successfully parsed record plus the file it came from."""

    record: BaseModel
    path: Path


def _load_all(model_cls: type[BaseModel], directory: Path) -> tuple[list[_Loaded], list[str]]:
    """Load every ``*.yaml`` in ``directory`` as ``model_cls``.

    Two checks happen here, not only in the caller, because they apply
    identically to every record type: a parse failure is reported per file,
    and the file's stem must equal the record's own ``id`` -- otherwise a
    file named ``REQ-002.yaml`` could silently contain ``id: REQ-001``,
    which is a duplicate id hidden behind a different filename.
    """
    problems: list[str] = []
    loaded: list[_Loaded] = []
    if not directory.is_dir():
        return loaded, problems
    for p in sorted(directory.glob("*.yaml")):
        try:
            record = store.load_record(model_cls, p)
        except (ValidationError, yaml.YAMLError) as exc:
            # A malformed authoring file is a validation problem for that
            # path, not a reason to abort the whole scan with a traceback
            # (PROTOCOLS.md structured-failure rule).
            problems.append(f"{p}: {exc}")
            continue
        record_id = getattr(record, "id", None)
        if record_id != p.stem:
            problems.append(
                f"{p}: filename does not match record id {record_id!r} "
                "(a mismatched filename can hide a duplicate id)"
            )
            continue
        loaded.append(_Loaded(record=record, path=p))
    return loaded, problems


def _check_duplicate_ids(loaded: list[_Loaded], label: str) -> list[str]:
    seen: dict[str, Path] = {}
    problems: list[str] = []
    for item in loaded:
        record_id = item.record.id  # type: ignore[attr-defined]
        if record_id in seen:
            problems.append(
                f"duplicate {label} id {record_id}: {seen[record_id]} and {item.path}"
            )
        else:
            seen[record_id] = item.path
    return problems


def _check_domain_matches_dir(
    loaded: list[_Loaded], domain_name: str, label: str
) -> list[str]:
    """A promoted ``Capability``/``Precedent`` carries its own ``domain``
    field; it must equal the ``domains/<domain>/`` directory it is filed
    under, or a Joule capability could sit in ``domains/maxwell/`` and be
    read as a Maxwell one."""
    problems: list[str] = []
    for item in loaded:
        declared = getattr(item.record, "domain", None)
        declared_value = getattr(declared, "value", declared)
        if declared_value != domain_name:
            problems.append(
                f"{item.path}: {label} {item.record.id} declares domain "  # type: ignore[attr-defined]
                f"{declared_value!r} but is filed under domains/{domain_name}/"
            )
    return problems


def _reconcile_study_index(
    study_folder: Path,
    field_name: str,
    declared_ids: list[str],
    on_disk_ids: list[str],
    label: str,
) -> list[str]:
    """``Study.<field_name>`` is a convenience index over the authoritative
    child files. The folder scan stays authoritative, but the two must not
    silently disagree (ROADMAP.md Phase A exit condition claims a
    ``Study``↔child check). An empty study with no child files still
    reconciles cleanly (empty == empty)."""
    problems: list[str] = []
    declared = set(declared_ids)
    on_disk = set(on_disk_ids)
    for missing in sorted(on_disk - declared):
        problems.append(
            f"{study_folder}: {label} {missing} has a record file but is not "
            f"listed in study.{field_name}"
        )
    for dangling in sorted(declared - on_disk):
        problems.append(
            f"{study_folder}: study.{field_name} lists {dangling} but no "
            f"matching {label} record file exists"
        )
    return problems


def _records(loaded: list[_Loaded]) -> list:
    return [item.record for item in loaded]


def _domain_value(record: BaseModel) -> str | None:
    """The record's ``domain`` as a plain string (``Domain`` is a ``str``
    enum, but be tolerant of either form)."""
    declared = getattr(record, "domain", None)
    return getattr(declared, "value", declared)


def _check_reference_domain(
    ref_id: str,
    ref_domain: str | None,
    study_domain: str | None,
    where: str,
    kind: str,
) -> list[str]:
    """Reject a domain-scoped reference whose target sits in a different
    domain than the study that names it. Callers only pass ids that are
    already known to exist, so a ``None`` target domain here means the
    record genuinely declares no domain and is reported as a mismatch."""
    if ref_domain == study_domain:
        return []
    return [
        f"{where}: {kind} {ref_id} belongs to domain {ref_domain!r}, but the "
        f"study's domain is {study_domain!r} -- a domain-scoped reference must "
        "not cross domains"
    ]


def validate_registry() -> ValidationReport:
    report = ValidationReport()

    # -- capabilities / precedents (domain-scoped, but ids must be globally
    # unique so a bare Result.capability_id / Experiment.capability_ids
    # string is never ambiguous about which domain it came from) --------
    all_capabilities: list[_Loaded] = []
    all_precedents: list[_Loaded] = []
    for domain_name in ("maxwell", "joule"):
        loaded, problems = _load_all(Capability, paths.domain_capabilities_dir(domain_name))
        report.problems.extend(problems)
        report.problems.extend(_check_domain_matches_dir(loaded, domain_name, "capability"))
        all_capabilities.extend(loaded)
        loaded, problems = _load_all(Precedent, paths.domain_precedents_dir(domain_name))
        report.problems.extend(problems)
        report.problems.extend(_check_domain_matches_dir(loaded, domain_name, "precedent"))
        all_precedents.extend(loaded)
    report.problems.extend(_check_duplicate_ids(all_capabilities, "capability"))
    report.problems.extend(_check_duplicate_ids(all_precedents, "precedent"))
    capability_ids = {c.record.id for c in all_capabilities}  # type: ignore[attr-defined]
    precedent_ids = {p.record.id for p in all_precedents}  # type: ignore[attr-defined]
    # Records are retained by id together with their declared domain so a
    # bare, domain-scoped reference can be rejected when it points across a
    # domain boundary (review round 3), not only when the id is unknown.
    capability_domain = {
        c.record.id: _domain_value(c.record)  # type: ignore[attr-defined]
        for c in all_capabilities
    }
    precedent_domain = {
        p.record.id: _domain_value(p.record)  # type: ignore[attr-defined]
        for p in all_precedents
    }

    if not paths.studies_dir().is_dir():
        return report

    # Bare child ids (REQ-001, EXP-001, ...) are referenced without a study
    # qualifier, so they must be unique across every study, not only within
    # one. These accumulate across the study loop and are checked once at the
    # end.
    cross_study: dict[str, list[_Loaded]] = {
        "requirement": [],
        "model hypothesis": [],
        "experiment": [],
        "result": [],
        "insight": [],
        "evidence": [],
    }

    study_ids: dict[str, Path] = {}
    for study_folder in sorted(paths.studies_dir().iterdir()):
        if not study_folder.is_dir():
            continue
        study_file = study_folder / "study.yaml"
        if not study_file.is_file():
            report.problems.append(f"{study_folder}: missing study.yaml")
            continue
        try:
            study: Study | None = store.load_record(Study, study_file)
        except (ValidationError, yaml.YAMLError) as exc:
            report.problems.append(f"{study_file}: {exc}")
            study = None

        if study is not None:
            if not study_folder.name.startswith(f"{study.id}_"):
                report.problems.append(
                    f"{study_folder}: folder name does not start with study id {study.id}"
                )
            if study.id in study_ids:
                report.problems.append(
                    f"duplicate study id {study.id}: {study_ids[study.id]} and {study_folder}"
                )
            else:
                study_ids[study.id] = study_folder

        req_loaded, problems = _load_all(Requirement, study_folder / "requirements")
        report.problems.extend(problems)
        cross_study["requirement"].extend(req_loaded)
        requirements: list[Requirement] = _records(req_loaded)

        mh_loaded, problems = _load_all(ModelHypothesis, study_folder / "model")
        report.problems.extend(problems)
        cross_study["model hypothesis"].extend(mh_loaded)
        hypotheses: list[ModelHypothesis] = _records(mh_loaded)

        exp_loaded, problems = _load_all(Experiment, study_folder / "experiments")
        report.problems.extend(problems)
        cross_study["experiment"].extend(exp_loaded)
        experiments: list[Experiment] = _records(exp_loaded)

        res_loaded, problems = _load_all(Result, study_folder / "results")
        report.problems.extend(problems)
        cross_study["result"].extend(res_loaded)
        results: list[Result] = _records(res_loaded)

        ins_loaded, problems = _load_all(Insight, study_folder / "insights")
        report.problems.extend(problems)
        cross_study["insight"].extend(ins_loaded)
        insights: list[Insight] = _records(ins_loaded)

        evd_loaded, problems = _load_all(Evidence, study_folder / "evidence")
        report.problems.extend(problems)
        cross_study["evidence"].extend(evd_loaded)
        evidence_records: list[Evidence] = _records(evd_loaded)

        if study is None:
            continue

        study_domain = _domain_value(study)

        # Study.<x>_ids convenience index vs the authoritative child files.
        report.problems.extend(
            _reconcile_study_index(
                study_folder, "requirement_ids",
                study.requirement_ids, [r.id for r in requirements], "requirement",
            )
        )
        report.problems.extend(
            _reconcile_study_index(
                study_folder, "model_hypothesis_ids",
                study.model_hypothesis_ids, [h.id for h in hypotheses], "model hypothesis",
            )
        )
        report.problems.extend(
            _reconcile_study_index(
                study_folder, "experiment_ids",
                study.experiment_ids, [e.id for e in experiments], "experiment",
            )
        )
        report.problems.extend(
            _reconcile_study_index(
                study_folder, "insight_ids",
                study.insight_ids, [i.id for i in insights], "insight",
            )
        )
        report.problems.extend(
            _reconcile_study_index(
                study_folder, "evidence_ids",
                study.evidence_ids, [ev.id for ev in evidence_records], "evidence",
            )
        )
        for cap_id in study.capability_ids:
            if cap_id not in capability_ids:
                report.problems.append(
                    f"{study_folder}: study.capability_ids lists unknown "
                    f"capability_id {cap_id}"
                )
            else:
                report.problems.extend(
                    _check_reference_domain(
                        cap_id, capability_domain.get(cap_id), study_domain,
                        f"{study_folder}: study.capability_ids", "capability",
                    )
                )
        for pre_id in study.precedent_ids:
            if pre_id not in precedent_ids:
                report.problems.append(
                    f"{study_folder}: study.precedent_ids lists unknown "
                    f"precedent_id {pre_id}"
                )
            else:
                report.problems.extend(
                    _check_reference_domain(
                        pre_id, precedent_domain.get(pre_id), study_domain,
                        f"{study_folder}: study.precedent_ids", "precedent",
                    )
                )

        for r in requirements:
            if r.study_id != study.id:
                report.problems.append(
                    f"{study_folder}: requirement {r.id} references "
                    f"study_id {r.study_id}, expected {study.id}"
                )
        for h in hypotheses:
            if h.study_id != study.id:
                report.problems.append(
                    f"{study_folder}: hypothesis {h.id} references "
                    f"study_id {h.study_id}, expected {study.id}"
                )
        for i in insights:
            if i.study_id != study.id:
                report.problems.append(
                    f"{study_folder}: insight {i.id} references "
                    f"study_id {i.study_id}, expected {study.id}"
                )
        for ev in evidence_records:
            if ev.study_id != study.id:
                report.problems.append(
                    f"{study_folder}: evidence {ev.id} references "
                    f"study_id {ev.study_id}, expected {study.id}"
                )

        hypotheses_by_id = {h.id: h for h in hypotheses}
        for e in experiments:
            if e.study_id != study.id:
                report.problems.append(
                    f"{study_folder}: experiment {e.id} references "
                    f"study_id {e.study_id}, expected {study.id}"
                )
            hypothesis = hypotheses_by_id.get(e.model_hypothesis_id)
            if hypothesis is None:
                report.problems.append(
                    f"{study_folder}: experiment {e.id} references unknown "
                    f"model_hypothesis_id {e.model_hypothesis_id}"
                )
            elif hypothesis.approval_status != ApprovalStatus.APPROVED:
                # An experiment may legitimately be run against a hypothesis
                # still under review, but that must be a visible validation
                # finding, not silent -- otherwise a draft/unreviewed
                # hypothesis masquerades as the reviewed idealisation that
                # governed the experiment (see ARCHITECTURE.md's five-way
                # validation split).
                report.problems.append(
                    f"{study_folder}: experiment {e.id} references "
                    f"model_hypothesis_id {e.model_hypothesis_id}, which is "
                    f"not approved (approval_status="
                    f"{hypothesis.approval_status.value!r}) -- it cannot "
                    "yet be treated as the reviewed modelling idealisation"
                )
            for cap_id in e.capability_ids:
                if cap_id not in capability_ids:
                    report.problems.append(
                        f"{study_folder}: experiment {e.id} references unknown "
                        f"capability_id {cap_id}"
                    )
                else:
                    report.problems.extend(
                        _check_reference_domain(
                            cap_id, capability_domain.get(cap_id), study_domain,
                            f"{study_folder}: experiment {e.id}", "capability",
                        )
                    )

        experiments_by_id = {e.id: e for e in experiments}
        for res in results:
            parent = experiments_by_id.get(res.experiment_id)
            if parent is None:
                report.problems.append(
                    f"{study_folder}: result {res.id} references unknown "
                    f"experiment_id {res.experiment_id}"
                )
            if res.capability_id not in capability_ids:
                report.problems.append(
                    f"{study_folder}: result {res.id} references unknown "
                    f"capability_id {res.capability_id}"
                )
                continue
            domain_problems = _check_reference_domain(
                res.capability_id, capability_domain.get(res.capability_id),
                study_domain, f"{study_folder}: result {res.id}", "capability",
            )
            report.problems.extend(domain_problems)
            if domain_problems:
                continue
            if (
                parent is not None
                and parent.capability_ids
                and res.capability_id not in parent.capability_ids
            ):
                # The result claims a capability its own experiment never
                # declared it would exercise -- the provenance chain
                # (experiment -> capability -> result) is broken.
                report.problems.append(
                    f"{study_folder}: result {res.id} uses capability_id "
                    f"{res.capability_id}, which is not among experiment "
                    f"{parent.id}'s capability_ids "
                    f"({sorted(parent.capability_ids)})"
                )

    # Cross-study bare-id uniqueness (accumulated above).
    for label, loaded in cross_study.items():
        report.problems.extend(_check_duplicate_ids(loaded, label))

    return report
