"""Physical facade actions -- pressure only, for this slice.

A ``FacadePressureLoad`` is a physical action on the facade, not a
structural load on a member. It has no tributary width baked in and no
member it is "for" -- turning it into a line load on one specific
analytical member is the job of ``idealisation.py``'s
``derive_mullion_line_load``, done explicitly and kept traceable, not
folded into this type.

Units: ``pressure_n_per_mm2`` is N/mm^2. For reference, 1 kPa = 1 kN/m^2 =
0.001 N/mm^2.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from noam.domains.maxwell.facade.geometry import FacadeModelBase


class PressureDirection(str, Enum):
    """Which way the pressure acts, relative to the facade plane.

    Recorded for explicitness only -- this slice's tributary-load
    conversion (``idealisation.derive_mullion_line_load``) does not yet
    branch on it (both directions currently produce the same positive
    line-load magnitude). Wiring an inward/outward sign convention into
    that conversion is left for a future task, once a suction/uplift case
    is actually needed -- see the completion report.
    """

    INWARD = "inward"
    OUTWARD = "outward"


class FacadePressureLoad(FacadeModelBase):
    """A uniform wind pressure applied over one loaded width of facade."""

    id: str = Field(min_length=1)
    pressure_n_per_mm2: float
    loaded_width_mm: float = Field(gt=0)
    direction: PressureDirection = PressureDirection.INWARD
