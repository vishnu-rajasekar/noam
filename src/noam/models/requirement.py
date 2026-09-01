"""Requirement -- what must be satisfied, and why. See ARCHITECTURE.md."""

from __future__ import annotations

from pydantic import Field

from noam.models.common import NoamBaseModel, RequirementStatus


class Requirement(NoamBaseModel):
    id: str = Field(pattern=r"^REQ-\d{3}$")
    study_id: str = Field(pattern=r"^S\d{3}$")
    title: str
    description: str = ""
    category: str = ""
    source_reference: str = ""
    source_type: str = ""
    applicability: str = ""
    status: RequirementStatus = RequirementStatus.PROPOSED
    notes: str = ""
