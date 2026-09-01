"""ModelHypothesis -- a first-class, reviewable idealisation choice.

This is deliberately not a black box: every field it forces the engineer to
fill (or explicitly leave unknown) is a question that a review conversation
would otherwise have to reconstruct from memory. See ARCHITECTURE.md's
governing rule (lowest fidelity capable of answering the current decision)
and the five-way validation split it also describes.
"""

from __future__ import annotations

from pydantic import Field

from noam.models.common import ApprovalStatus, NoamBaseModel


class ModelHypothesis(NoamBaseModel):
    id: str = Field(pattern=r"^MH-\d{3}$")
    study_id: str = Field(pattern=r"^S\d{3}$")
    purpose: str
    analysis_question: str
    model_type: str = ""
    fidelity: str = ""
    geometry_idealisation: str = ""
    included_behaviour: list[str] = Field(default_factory=list)
    excluded_behaviour: list[str] = Field(default_factory=list)
    supports: str = "unknown"
    joints_releases: str = "unknown"
    loads: str = "unknown"
    materials: str = "unknown"
    known_simplifications: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    escalation_conditions: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
    supersedes: str | None = None
    superseded_by: str | None = None
