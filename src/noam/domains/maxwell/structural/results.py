"""Normalized analysis result -- explicit fields, no untyped dict.

Every field a result carries is typed and named, and every result carries
enough identity to answer "which model, which member, which load case,
which analysis method produced this?" without positional guessing -- see
the FrameSizer audit's finding that FrameSizer reconstructs load-case
identity after the fact by floating-point-matching a value back against a
list. That is exactly what this shape exists to avoid.

This module contains no design-check concept (no utilisation, no
resistance, no pass/fail, no deflection limit) -- see ARCHITECTURE.md's
analysis/design-check boundary. A result here answers "what did the member
do under this load", never "is that adequate".
"""

from __future__ import annotations

from noam.domains.maxwell.structural.model import StructuralModelBase
from pydantic import Field


class Reaction(StructuralModelBase):
    """A support reaction.

    ``force_n`` is a magnitude acting to support the member (i.e. upward,
    for the downward point load this benchmark applies) -- a full signed
    force/moment vector is not tracked, since this spike has no case that
    needs one.
    """

    node_id: str = Field(min_length=1)
    support_id: str = Field(min_length=1)
    force_n: float


class AnalysisResult(StructuralModelBase):
    """The outcome of analysing one load case against one structural model."""

    model_id: str = Field(min_length=1)
    member_id: str = Field(min_length=1)
    load_case_id: str = Field(min_length=1)
    analysis_method: str = Field(min_length=1)

    reactions: list[Reaction]

    max_bending_moment_n_mm: float
    max_bending_moment_location_mm: float

    max_deflection_mm: float
    max_deflection_location_mm: float
