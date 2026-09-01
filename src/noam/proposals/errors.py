"""Structured backend errors for A5.1.

A single exception type carrying a :class:`ReasonCode` and a non-content
``affected`` reference. The intake layer converts these into an
:class:`~noam.proposals.unresolved.UnresolvedState`; they are never allowed
to propagate as an uncaught traceback, and their string form contains only
the reason code and the affected identifier -- no prompt or source text.
"""

from __future__ import annotations

from noam.proposals.unresolved import ReasonCode


class ProposalError(Exception):
    """Recoverable backend/contract failure with a stable reason code."""

    def __init__(self, reason_code: ReasonCode, affected: str) -> None:
        super().__init__(f"{reason_code.value}:{affected}")
        self.reason_code = reason_code
        self.affected = affected
