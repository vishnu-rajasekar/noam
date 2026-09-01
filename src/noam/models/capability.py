"""Capability -- reusable deterministic engineering functionality.

Promoted out of a study into domains/<domain>/capabilities/ once validated.
A Capability never performs a design check under a generic "utilisation"
result -- see ARCHITECTURE.md's analysis/design-check boundary.
"""

from __future__ import annotations

from pydantic import Field

from noam.models.common import CapabilityStatus, Domain, NoamBaseModel


class Capability(NoamBaseModel):
    id: str = Field(pattern=r"^CAP-\d{3}$")
    domain: Domain
    name: str
    purpose: str
    version: str = "0.1.0"
    status: CapabilityStatus = CapabilityStatus.PROPOSED
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    valid_domain: str = ""
    validation_evidence: list[str] = Field(default_factory=list)
    implementation_reference: str = ""
