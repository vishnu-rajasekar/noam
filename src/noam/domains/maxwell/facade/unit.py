"""Physical facade geometry for one rectangular unitised curtain-wall unit.

These are physical objects -- what is actually there on the building -- not
structural idealisations. A ``FacadeMember`` is not, and must not become, a
subclass of ``noam.domains.maxwell.structural.model.Member``: a physical
mullion is not necessarily equal to one analytical beam element (it might
be idealised as one beam, several, or none, depending on the modelling
hypothesis chosen -- see ``idealisation.py``). This module has no import of
anything under ``structural/``.

Scope is deliberately one unit: this package does not represent a facade
grid, multiple units, panelisation, or unit-to-unit interaction (stack
joints). See the task boundary this was built against.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from noam.domains.maxwell.facade.geometry import FacadeModelBase, Point


class MemberRole(str, Enum):
    """Which perimeter position a physical facade member occupies."""

    LEFT_MULLION = "left_mullion"
    RIGHT_MULLION = "right_mullion"
    HEAD_TRANSOM = "head_transom"
    SILL_TRANSOM = "sill_transom"


class FacadeMember(FacadeModelBase):
    """One physical facade member (a mullion or a transom).

    ``start_point``/``end_point`` are in the unit's local coordinate system
    (see ``geometry.py``). By convention in this package, a mullion's
    ``start_point`` is its bottom end and a transom's ``start_point`` is
    its left end -- ``build_rectangular_unit`` below follows this, and
    tests may rely on it.
    """

    id: str = Field(min_length=1)
    role: MemberRole
    start_point: Point
    end_point: Point


class CurtainWallUnit(FacadeModelBase):
    """One rectangular unitised curtain-wall unit: four perimeter members.

    Explicit named fields (not a bare list) so a role can never be
    ambiguous by position -- ``unit.left_mullion`` is always the left
    mullion. The ``_check_roles_match_fields`` validator additionally
    guards against constructing a unit where e.g. ``left_mullion`` was
    accidentally given ``role=RIGHT_MULLION``.
    """

    id: str = Field(min_length=1)
    width_mm: float = Field(gt=0)
    height_mm: float = Field(gt=0)
    left_mullion: FacadeMember
    right_mullion: FacadeMember
    head_transom: FacadeMember
    sill_transom: FacadeMember

    @model_validator(mode="after")
    def _check_roles_match_fields(self) -> "CurtainWallUnit":
        expected = {
            "left_mullion": MemberRole.LEFT_MULLION,
            "right_mullion": MemberRole.RIGHT_MULLION,
            "head_transom": MemberRole.HEAD_TRANSOM,
            "sill_transom": MemberRole.SILL_TRANSOM,
        }
        for field_name, expected_role in expected.items():
            member: FacadeMember = getattr(self, field_name)
            if member.role is not expected_role:
                raise ValueError(
                    f"CurtainWallUnit.{field_name} must have role "
                    f"{expected_role!r}; got {member.role!r} "
                    f"(member id {member.id!r})."
                )
        return self


def build_rectangular_unit(
    *,
    id: str,
    width_mm: float,
    height_mm: float,
    left_mullion_id: str,
    right_mullion_id: str,
    head_transom_id: str,
    sill_transom_id: str,
) -> CurtainWallUnit:
    """Builds a rectangular unit's four perimeter members from width/height.

    Ids are always supplied explicitly by the caller, never generated --
    identity is not this function's decision to make (see the task's
    identity-mapping requirement).

        (0, H) head_transom (W, H)
            +-------------------+
            |                   |
    left_   |                   | right_
    mullion |                   | mullion
            |                   |
            +-------------------+
        (0, 0) sill_transom  (W, 0)
    """
    return CurtainWallUnit(
        id=id,
        width_mm=width_mm,
        height_mm=height_mm,
        left_mullion=FacadeMember(
            id=left_mullion_id,
            role=MemberRole.LEFT_MULLION,
            start_point=Point(x_mm=0.0, y_mm=0.0),
            end_point=Point(x_mm=0.0, y_mm=height_mm),
        ),
        right_mullion=FacadeMember(
            id=right_mullion_id,
            role=MemberRole.RIGHT_MULLION,
            start_point=Point(x_mm=width_mm, y_mm=0.0),
            end_point=Point(x_mm=width_mm, y_mm=height_mm),
        ),
        head_transom=FacadeMember(
            id=head_transom_id,
            role=MemberRole.HEAD_TRANSOM,
            start_point=Point(x_mm=0.0, y_mm=height_mm),
            end_point=Point(x_mm=width_mm, y_mm=height_mm),
        ),
        sill_transom=FacadeMember(
            id=sill_transom_id,
            role=MemberRole.SILL_TRANSOM,
            start_point=Point(x_mm=0.0, y_mm=0.0),
            end_point=Point(x_mm=width_mm, y_mm=0.0),
        ),
    )
