"""Repository-relative paths. All registry/CLI code goes through here so the
repo can be relocated (e.g. copied onto a work PC) without code changes."""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError(
        "could not locate the noam repository root (no pyproject.toml found "
        "in any parent directory)"
    )


def studies_dir() -> Path:
    return repo_root() / "studies"


def study_dir(study_id_and_slug: str) -> Path:
    """``study_id_and_slug`` is the folder name, e.g. ``S001_airport_cw``."""
    return studies_dir() / study_id_and_slug


def find_study_dir(study_id: str) -> Path | None:
    if not studies_dir().is_dir():
        return None
    for candidate in studies_dir().iterdir():
        if candidate.is_dir() and candidate.name.startswith(f"{study_id}_"):
            return candidate
    return None


def domains_dir() -> Path:
    return repo_root() / "domains"


def domain_capabilities_dir(domain: str) -> Path:
    return domains_dir() / domain / "capabilities"


def domain_precedents_dir(domain: str) -> Path:
    return domains_dir() / domain / "precedents"


def knowledge_dir() -> Path:
    return repo_root() / "knowledge"


def registry_dir() -> Path:
    return repo_root() / "registry"


def index_db_path() -> Path:
    return registry_dir() / "noam.db"
