"""Fast, EnergyPlus-free unit tests for the rectangular office model builder."""
import pytest
from honeybee.boundarycondition import boundary_conditions

from spike.task0_energy.building import OfficeBuildingParameters, build_office_model


def test_default_parameters_are_valid():
    params = OfficeBuildingParameters()
    assert params.floor_count >= 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"floor_count": 0},
        {"floor_width_m": 0},
        {"floor_depth_m": -1},
        {"floor_to_floor_height_m": 0},
        {"orientation_angle_deg": 360},
        {"orientation_angle_deg": -1},
        {"window_to_wall_ratio": 0},
        {"window_to_wall_ratio": 1},
    ],
)
def test_invalid_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        OfficeBuildingParameters(**kwargs)


def test_model_has_one_zone_per_floor():
    params = OfficeBuildingParameters(floor_count=4)
    model = build_office_model(params)
    assert len(model.rooms) == 4


def test_interior_floor_ceiling_adjacencies_are_solved():
    params = OfficeBuildingParameters(floor_count=3)
    model = build_office_model(params)
    rooms_by_story = {room.story: room for room in model.rooms}

    bottom_room = rooms_by_story["Floor1"]
    top_room = rooms_by_story["Floor3"]
    middle_room = rooms_by_story["Floor2"]

    bottom_floor_face = next(f for f in bottom_room.faces if f.type.name == "Floor")
    assert bottom_floor_face.boundary_condition == boundary_conditions.ground

    top_roof_face = next(f for f in top_room.faces if f.type.name == "RoofCeiling")
    assert top_roof_face.boundary_condition == boundary_conditions.outdoors

    middle_floor_face = next(f for f in middle_room.faces if f.type.name == "Floor")
    assert middle_floor_face.boundary_condition.name == "Surface"


def test_orientation_angle_rotates_the_facade():
    north_facing = build_office_model(OfficeBuildingParameters(orientation_angle_deg=0))
    east_facing = build_office_model(OfficeBuildingParameters(orientation_angle_deg=90))

    north_front = next(f for f in north_facing.rooms[0].faces if "Front" in f.identifier)
    east_front = next(f for f in east_facing.rooms[0].faces if "Front" in f.identifier)

    assert north_front.normal != east_front.normal


def test_every_room_has_program_hvac_and_apertures():
    params = OfficeBuildingParameters()
    model = build_office_model(params)
    for room in model.rooms:
        assert room.properties.energy.program_type.identifier == params.program_type_identifier
        assert room.properties.energy.hvac is not None
        assert room.exterior_aperture_area > 0
