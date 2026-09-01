"""Shared enums and base model for the Study hierarchy."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NoamBaseModel(BaseModel):
    """Base for all Study-hierarchy records.

    ``extra="forbid"`` is deliberate: an unrecognised field in an authoring
    file is far more likely to be a typo or a stale field than an intentional
    extension, and this is a local registry an engineer hand-edits.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ProjectStage(str, Enum):
    """RIBA-style numeric stage, or ``unknown``.

    Stage-specific analysis rules are deliberately not encoded here (see
    ARCHITECTURE.md's governing rule: use the lowest-fidelity model capable
    of answering the current decision). The stage is metadata an engineer
    and a ModelHypothesis's fidelity choice can be checked against, not a
    switch that changes behaviour.
    """

    STAGE_1 = "1"
    STAGE_2 = "2"
    STAGE_3 = "3"
    STAGE_4 = "4"
    STAGE_5 = "5"
    UNKNOWN = "unknown"


class Confidentiality(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"


class StudyStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class RequirementStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    """Human review state -- never set by an agent on its own authority."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class CapabilityStatus(str, Enum):
    PROPOSED = "proposed"
    EXPERIMENTAL = "experimental"
    VALIDATED = "validated"
    DEPRECATED = "deprecated"


class ValidationStatus(str, Enum):
    """Result/Experiment-level: has the *numerical/physics* output been
    checked, independent of whether the modelling hypothesis or the design
    code applied to it are correct (see ARCHITECTURE.md)."""

    UNVALIDATED = "unvalidated"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class TrustLevel(str, Enum):
    """From PROTOCOLS.md -- scoped to one capability/version, never
    inherited by a whole neighbouring environment."""

    EXPERIMENTAL = "experimental"
    VERIFIED = "verified"
    PROJECT_APPROVED = "project_approved"
    SUPERSEDED = "superseded"


class ReuseStatus(str, Enum):
    CANDIDATE = "candidate"
    REUSABLE = "reusable"
    NOT_REUSABLE = "not_reusable"
    SUPERSEDED = "superseded"


class Domain(str, Enum):
    """Confirmed environments only -- see ENVIRONMENTS.md. Provisional names
    (Fick, Prandtl, ...) are intentionally not enumerated here so a study
    cannot be filed against a domain with no implemented contract."""

    MAXWELL = "maxwell"
    JOULE = "joule"
