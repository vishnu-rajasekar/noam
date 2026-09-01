"""Deterministic rectangular multi-storey office model builder.

Produces a Honeybee Model of a rectangular office building with one thermal
zone per floor and a single parameterised facade orientation, using only
honeybee-core geometry plus honeybee-energy program/HVAC/construction
assignment. No OpenStudio dependency is used anywhere in this module.
"""
from __future__ import annotations

from dataclasses import dataclass

from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.lib.constructionsets import construction_set_by_identifier
from honeybee_energy.lib.programtypes import program_type_by_identifier
from ladybug_geometry.geometry3d.pointvector import Point3D

#: honeybee-energy standards-library identifiers used as the reference
#: assumptions for this feasibility case. Both ship with
#: honeybee-energy[standards] and require no network access.
DEFAULT_PROGRAM_TYPE = "Generic Office Program"
DEFAULT_CONSTRUCTION_SET = "Default Generic Construction Set"


@dataclass(frozen=True)
class OfficeBuildingParameters:
    """Parameters for a rectangular, single-zone-per-floor office building."""

    identifier: str = "task0_office"
    floor_count: int = 3
    floor_width_m: float = 20.0
    floor_depth_m: float = 12.0
    floor_to_floor_height_m: float = 3.5
    orientation_angle_deg: float = 0.0
    window_to_wall_ratio: float = 0.35
    program_type_identifier: str = DEFAULT_PROGRAM_TYPE
    construction_set_identifier: str = DEFAULT_CONSTRUCTION_SET

    def __post_init__(self) -> None:
        if self.floor_count < 1:
            raise ValueError("floor_count must be >= 1")
        if self.floor_width_m <= 0 or self.floor_depth_m <= 0:
            raise ValueError("floor_width_m and floor_depth_m must be > 0")
        if self.floor_to_floor_height_m <= 0:
            raise ValueError("floor_to_floor_height_m must be > 0")
        if not (0.0 <= self.orientation_angle_deg < 360.0):
            raise ValueError("orientation_angle_deg must be in [0, 360)")
        if not (0.0 < self.window_to_wall_ratio < 0.95):
            raise ValueError("window_to_wall_ratio must be in (0, 0.95)")


def build_office_model(params: OfficeBuildingParameters) -> Model:
    """Build a rectangular office Honeybee Model with one zone per floor.

    Each floor is an independent box room stacked on the one below. Interior
    floor/ceiling adjacencies are solved automatically (Surface boundary
    condition); the ground floor's floor face and the top floor's roof face
    keep Honeybee's box defaults (Ground and Outdoors respectively). Every
    room gets the same program type, construction set, and an ideal-air
    HVAC equivalent (no plant/system sizing beyond the ideal loads system),
    so the only architectural variable exercised is facade orientation.
    """
    program = program_type_by_identifier(params.program_type_identifier)
    construction_set = construction_set_by_identifier(params.construction_set_identifier)

    rooms = []
    for floor_index in range(params.floor_count):
        origin_z = floor_index * params.floor_to_floor_height_m
        room = Room.from_box(
            identifier=f"{params.identifier}_floor{floor_index + 1}",
            width=params.floor_width_m,
            depth=params.floor_depth_m,
            height=params.floor_to_floor_height_m,
            orientation_angle=params.orientation_angle_deg,
            origin=Point3D(0, 0, origin_z),
        )
        room.story = f"Floor{floor_index + 1}"
        room.multiplier = 1
        room.wall_apertures_by_ratio(params.window_to_wall_ratio)
        room.properties.energy.program_type = program
        room.properties.energy.construction_set = construction_set
        room.properties.energy.add_default_ideal_air()
        rooms.append(room)

    Room.solve_adjacency(rooms)

    return Model(params.identifier, rooms)
