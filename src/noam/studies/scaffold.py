"""Create a study folder on disk (see ARCHITECTURE.md's study-folder layout).

Authoring files this writes are starting templates, not claimed engineering
content -- brief.md and model-hypothesis.md are seeded with unknowns
explicitly marked as unknown, never invented values (see AGENTS.md).
"""

from __future__ import annotations

from pathlib import Path

from noam.models import Study
from noam.registry import paths, store

SUBFOLDERS = (
    "requirements",
    "model",
    "calculations",
    "experiments",
    "datasets",
    "validation",
    "results",
    "insights",
    "decisions",
    "evidence",
)

BRIEF_TEMPLATE = """# Engineering question

# Decision required

# Project stage

# System description

# Jurisdiction

# Design intent

# Known geometry

# Primary load paths

# Known requirements

# Available information

# Missing information

# Initial modelling hypothesis

# Critical modelling uncertainties

# Existing engineering tools/assets

# Required outputs

# Validation strategy

# Potential reusable capability

# Potential reusable precedent

# Confidentiality notes
"""

MODEL_HYPOTHESIS_TEMPLATE = """# Model hypothesis (starting template -- requires project review)

All values below require project review before use. Leave anything unknown
explicitly marked `Unknown` -- do not invent support conditions, releases,
loads, or material properties (see AGENTS.md).

# Analysis question

# Intended decision

# Proposed model fidelity

# Geometry idealisation

# Members

# Supports

Unknown

# Joint/release assumptions

Unknown

# Loads

Unknown

# Materials

Unknown

# Behaviour included

# Behaviour excluded

# Known simplifications

# Unknowns

# Sensitivity questions

# Escalation conditions

# Validation required

# Approval status

draft
"""


def create_study(study: Study, slug: str | None = None) -> Path:
    """Create the study folder, study.yaml, brief.md, and the
    model-hypothesis.md skeleton. Raises FileExistsError if a directory for
    this study id already exists. ``slug`` overrides the folder's short name
    (default: derived from the title); pass it for a short, stable folder
    name such as ``S001_airport_cw`` rather than a full-title slug."""
    if paths.find_study_dir(study.id) is not None:
        raise FileExistsError(f"a study directory already exists for {study.id}")

    directory = store.save_study(study, slug=slug)
    for sub in SUBFOLDERS:
        (directory / sub).mkdir(parents=True, exist_ok=True)
        gitkeep = directory / sub / ".gitkeep"
        if not any((directory / sub).iterdir()):
            gitkeep.write_text("", encoding="utf-8")

    brief = directory / "brief.md"
    if not brief.exists():
        brief.write_text(BRIEF_TEMPLATE, encoding="utf-8")

    hypothesis_md = directory / "model" / "model-hypothesis.md"
    if not hypothesis_md.exists():
        hypothesis_md.write_text(MODEL_HYPOTHESIS_TEMPLATE, encoding="utf-8")
        gitkeep = directory / "model" / ".gitkeep"
        if gitkeep.exists():
            gitkeep.unlink()

    return directory
