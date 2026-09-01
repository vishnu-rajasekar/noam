"""Evidence -- engineering validation, professional (CEng/CPD), and decision
evidence tying requirements/hypotheses/results/insights to a human decision."""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from noam.models.common import NoamBaseModel


class EvidenceKind(str, Enum):
    ENGINEERING_VALIDATION = "engineering_validation"
    PROFESSIONAL = "professional"
    DECISION = "decision"


class Evidence(NoamBaseModel):
    id: str = Field(pattern=r"^EVD-\d{3}$")
    study_id: str = Field(pattern=r"^S\d{3}$")
    kind: EvidenceKind
    statement: str
    references: list[str] = Field(default_factory=list)
    owner: str = ""
    approved: bool = False
