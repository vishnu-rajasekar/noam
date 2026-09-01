"""RuleCard -- future bridge from a standard/guidance clause into a
deterministic design check. Metadata only tonight; no rule executes.

See ARCHITECTURE.md's Phase C: licensed/project documents -> local intake ->
clause extraction -> structured retrieval -> RuleCard -> human review ->
approved rule pack -> deterministic check. A RuleCard never lets a
calculation re-read a standard through an LLM at run time.
"""

from __future__ import annotations

from pydantic import Field

from noam.models.common import ApprovalStatus, NoamBaseModel


class RuleCard(NoamBaseModel):
    id: str = Field(pattern=r"^RC-\d{3}$")
    standard: str
    edition: str = ""
    clause: str = ""
    jurisdiction: str = "unknown"
    statement: str = ""
    source_reference: str = ""
    approval_status: ApprovalStatus = ApprovalStatus.DRAFT
