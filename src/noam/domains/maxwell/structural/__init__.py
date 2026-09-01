"""Maxwell.Structural -- solver-neutral structural model and closed-form analysis.

Scope, for now, is exactly two benchmarks: a simply-supported single-span
member under either one central point load or one full-span uniformly
distributed load. See ``model.py``/``analysis.py``/``results.py``
docstrings and ``knowledge/restricted/framesizer_audit/`` for the reasoning
behind that boundary.
"""

from noam.domains.maxwell.structural.analysis import (
    ANALYSIS_METHOD_CENTRAL_POINT_LOAD,
    ANALYSIS_METHOD_FULL_SPAN_UDL,
    ClosedFormFormulaAnalysisAdapter,
    UnsupportedStructuralModelError,
)
from noam.domains.maxwell.structural.model import (
    DistributedLoad,
    LoadCase,
    Material,
    Member,
    Node,
    PointLoad,
    SectionProperties,
    StructuralModel,
    Support,
    SupportKind,
)
from noam.domains.maxwell.structural.results import AnalysisResult, Reaction

__all__ = [
    "ANALYSIS_METHOD_CENTRAL_POINT_LOAD",
    "ANALYSIS_METHOD_FULL_SPAN_UDL",
    "AnalysisResult",
    "ClosedFormFormulaAnalysisAdapter",
    "DistributedLoad",
    "LoadCase",
    "Material",
    "Member",
    "Node",
    "PointLoad",
    "Reaction",
    "SectionProperties",
    "StructuralModel",
    "Support",
    "SupportKind",
    "UnsupportedStructuralModelError",
]
