"""Authoring-file read/write for the Study hierarchy.

These files ARE the registry (see ARCHITECTURE.md). ``registry/index.py``
only ever reads them to build a disposable query cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from noam.models import Capability, Insight, Precedent, Study
from noam.registry import paths
from noam.utils.yaml_io import dump_yaml, load_yaml

ModelT = TypeVar("ModelT", bound=BaseModel)


def save_record(record: BaseModel, path: Path) -> None:
    dump_yaml(record.model_dump(mode="json"), path)


def load_record(model_cls: type[ModelT], path: Path) -> ModelT:
    return model_cls.model_validate(load_yaml(path))


def load_records(model_cls: type[ModelT], directory: Path) -> list[ModelT]:
    if not directory.is_dir():
        return []
    return [
        load_record(model_cls, p) for p in sorted(directory.glob("*.yaml"))
    ]


# -- Study -------------------------------------------------------------


def study_folder_name(study: Study, slug: str | None = None) -> str:
    return f"{study.id}_{(slug or study.slug).replace('-', '_')}"


def save_study(study: Study, slug: str | None = None) -> Path:
    existing = paths.find_study_dir(study.id)
    directory = existing or paths.study_dir(study_folder_name(study, slug))
    directory.mkdir(parents=True, exist_ok=True)
    save_record(study, directory / "study.yaml")
    return directory


def load_study(study_id: str) -> Study:
    directory = paths.find_study_dir(study_id)
    if directory is None:
        raise FileNotFoundError(f"no study directory found for {study_id}")
    return load_record(Study, directory / "study.yaml")


# Study fields this tracks -- keeps Study.<x>_ids in sync with what the CLI
# actually creates under the study folder. This is a convenience index (the
# folder scan in registry/validate.py remains authoritative), but letting it
# silently drift was one of the Phase A closure findings.
_STUDY_REF_FIELDS = {
    "requirement": "requirement_ids",
    "model_hypothesis": "model_hypothesis_ids",
    "experiment": "experiment_ids",
    "insight": "insight_ids",
    "evidence": "evidence_ids",
}


def append_study_ref(study_id: str, kind: str, record_id: str) -> None:
    """Append ``record_id`` to the matching ``Study.<kind>_ids`` list, if not
    already present. ``kind`` is one of _STUDY_REF_FIELDS's keys."""
    field_name = _STUDY_REF_FIELDS[kind]
    study = load_study(study_id)
    ids: list[str] = getattr(study, field_name)
    if record_id not in ids:
        ids.append(record_id)
        save_study(study)


def list_studies() -> list[Study]:
    studies_dir = paths.studies_dir()
    if not studies_dir.is_dir():
        return []
    out = []
    for candidate in sorted(studies_dir.iterdir()):
        study_file = candidate / "study.yaml"
        if study_file.is_file():
            out.append(load_record(Study, study_file))
    return out


# -- Domain-level promoted records --------------------------------------


def _list_domain_names() -> list[str]:
    if not paths.domains_dir().is_dir():
        return []
    return [d.name for d in sorted(paths.domains_dir().iterdir()) if d.is_dir()]


def list_capabilities(domain: str | None = None) -> list[Capability]:
    domains = [domain] if domain else _list_domain_names()
    out: list[Capability] = []
    for d in domains:
        out.extend(load_records(Capability, paths.domain_capabilities_dir(d)))
    return out


def list_precedents(domain: str | None = None) -> list[Precedent]:
    domains = [domain] if domain else _list_domain_names()
    out: list[Precedent] = []
    for d in domains:
        out.extend(load_records(Precedent, paths.domain_precedents_dir(d)))
    return out


def list_insights(study_id: str | None = None) -> list[Insight]:
    if study_id:
        studies = [paths.find_study_dir(study_id)]
    elif paths.studies_dir().is_dir():
        studies = [d for d in sorted(paths.studies_dir().iterdir()) if d.is_dir()]
    else:
        studies = []
    out: list[Insight] = []
    for study_folder in studies:
        if study_folder is None:
            continue
        out.extend(load_records(Insight, study_folder / "insights"))
    return out
