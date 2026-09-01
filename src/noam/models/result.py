"""Result -- explicit, not hidden inside Experiment. See ARCHITECTURE.md.

``software_validation_status`` and ``numerical_validation_status`` are kept
as two separate fields, not one collapsed ``validation_status``, because
ARCHITECTURE.md requires software correctness ("does the code do what it
claims?") and numerical/physics correctness ("does it converge, balance,
and agree with a benchmark?") to remain distinct and independently
recordable -- code can pass its tests while a solver's numerics are wrong,
or vice versa, and a single flag cannot represent that.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from noam.models.common import NoamBaseModel, ValidationStatus


class Result(NoamBaseModel):
    id: str = Field(pattern=r"^RES-\d{3}$")
    experiment_id: str = Field(pattern=r"^EXP-\d{3}$")
    capability_id: str = Field(pattern=r"^CAP-\d{3}$")
    result_type: str
    units: str = ""
    value: Any = None
    reference: str = ""
    provenance: str = ""
    software_validation_status: ValidationStatus = ValidationStatus.UNVALIDATED
    numerical_validation_status: ValidationStatus = ValidationStatus.UNVALIDATED
    warnings: list[str] = Field(default_factory=list)
