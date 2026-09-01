"""Experiment -- a bounded run of a Capability against a ModelHypothesis.

``model_hypothesis_id`` is the traceability link this record exists for: it
is what lets a Result be traced back to the reviewed idealisation
(``ModelHypothesis.approval_status``) that governed it, not just to the
Capability that produced it. See ARCHITECTURE.md's five-way validation
split.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from noam.models.common import NoamBaseModel, ValidationStatus


class Experiment(NoamBaseModel):
    id: str = Field(pattern=r"^EXP-\d{3}$")
    study_id: str = Field(pattern=r"^S\d{3}$")
    model_hypothesis_id: str = Field(pattern=r"^MH-\d{3}$")
    capability_ids: list[str] = Field(default_factory=list)
    title: str
    question: str = ""
    experiment_hypothesis: str = Field(
        default="",
        description=(
            "Free-text hypothesis under test by this experiment (e.g. "
            "'increasing overhang depth reduces overheating'). Distinct "
            "from model_hypothesis_id, which is the reviewed idealisation "
            "the experiment was run against."
        ),
    )
    variables: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)
    dataset_reference: str = ""
    result_reference: str = ""
    validation_status: ValidationStatus = ValidationStatus.UNVALIDATED
    findings: str = ""
