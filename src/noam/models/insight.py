"""Insight -- a finding derived from evidence, with an explicit reuse status.

A previous study's Insight is not automatically authoritative for a new one;
``valid_domain`` and ``limitations`` exist so a future study can check
applicability instead of assuming it.
"""

from __future__ import annotations

from pydantic import Field

from noam.models.common import NoamBaseModel, ReuseStatus


class Insight(NoamBaseModel):
    id: str = Field(pattern=r"^INS-\d{3}$")
    study_id: str = Field(pattern=r"^S\d{3}$")
    statement: str
    valid_domain: str = ""
    limitations: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: str = "unstated"
    reuse_status: ReuseStatus = ReuseStatus.CANDIDATE
