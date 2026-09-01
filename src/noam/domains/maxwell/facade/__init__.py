"""Physical S001 curtain-wall facade geometry -- one rectangular unit.

Deliberately independent of ``noam.domains.maxwell.structural``: nothing
here imports the structural package, so "physical facade model" and
"structural idealisation" stay two separately defined layers. See
``noam.domains.maxwell.idealisation`` for the mapper that connects them.
"""

from noam.domains.maxwell.facade.geometry import Point
from noam.domains.maxwell.facade.loads import FacadePressureLoad, PressureDirection
from noam.domains.maxwell.facade.unit import (
    CurtainWallUnit,
    FacadeMember,
    MemberRole,
    build_rectangular_unit,
)

__all__ = [
    "CurtainWallUnit",
    "FacadeMember",
    "FacadePressureLoad",
    "MemberRole",
    "Point",
    "PressureDirection",
    "build_rectangular_unit",
]
