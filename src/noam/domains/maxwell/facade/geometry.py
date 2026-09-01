"""S001 facade local coordinate convention, and the base geometry types.

Convention (this package's own, not a project-wide standard):

    X: horizontal, across the curtain-wall unit's width, left -> right
    Y: vertical, up the facade, bottom -> top
    Z: outward, normal to the facade plane, positive = away from the
       building interior

    Origin: the bottom-left corner of the unit being modelled -- the
    sill/left-mullion intersection. X=0 at the left mullion, Y=0 at the
    sill.

All coordinates in this package are in millimetres.

This is a Maxwell/S001-local convention, owned entirely here. It has no
relationship to Rhino's world coordinate system, a document CPlane, or any
other tool's origin -- that mapping, if and when a Rhino-facing layer is
built, belongs there, not here. Nothing in this package imports or assumes
RhinoCommon (see the task boundary: Rhino is deliberately the next layer,
not this one).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FacadeModelBase(BaseModel):
    """Local strict base for physical facade entities.

    A separate class from ``noam.domains.maxwell.structural.model.StructuralModelBase``
    on purpose -- the facade package does not import the structural package,
    so that "physical facade model" and "structural idealisation" stay two
    independently defined layers, not one importing infrastructure from the
    other (see ``idealisation.py`` for the one layer that is allowed to
    depend on both).
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Point(FacadeModelBase):
    """A point in the local facade coordinate system, in millimetres."""

    x_mm: float
    y_mm: float
    z_mm: float = 0.0
