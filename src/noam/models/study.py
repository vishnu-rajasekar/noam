"""Study -- one bounded engineering problem. See ARCHITECTURE.md."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from noam.models.common import (
    Confidentiality,
    Domain,
    NoamBaseModel,
    ProjectStage,
    StudyStatus,
    utcnow,
)


class Study(NoamBaseModel):
    id: str = Field(pattern=r"^S\d{3}$", description="e.g. S001")
    title: str
    domain: Domain
    project_stage: ProjectStage = ProjectStage.UNKNOWN
    status: StudyStatus = StudyStatus.DRAFT
    confidentiality: Confidentiality = Confidentiality.INTERNAL
    engineering_question: str
    decision_required: str
    description: str = ""
    jurisdiction: str = "unknown"
    system_type: str = ""
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    # References -- ids only. The referenced records live under this
    # study's own folder or under domains/<domain>/ once promoted; this
    # list is a convenience index, not ownership.
    requirement_ids: list[str] = Field(default_factory=list)
    model_hypothesis_ids: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    experiment_ids: list[str] = Field(default_factory=list)
    insight_ids: list[str] = Field(default_factory=list)
    precedent_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @property
    def slug(self) -> str:
        return self.title.lower().replace(" ", "-")
