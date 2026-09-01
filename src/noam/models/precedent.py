"""Precedent -- reusable engineering reasoning/model strategy, backed by one
or more studies. Promoted to domains/<domain>/precedents/ once validated."""

from __future__ import annotations

from pydantic import Field

from noam.models.common import Domain, NoamBaseModel, TrustLevel


class Precedent(NoamBaseModel):
    id: str = Field(pattern=r"^PRE-\d{3}$")
    domain: Domain
    title: str
    source_study_ids: list[str] = Field(default_factory=list)
    applicability: str = ""
    modelling_strategy: str = ""
    evidence: list[str] = Field(default_factory=list)
    escalation_conditions: list[str] = Field(default_factory=list)
    validation_state: TrustLevel = TrustLevel.EXPERIMENTAL
