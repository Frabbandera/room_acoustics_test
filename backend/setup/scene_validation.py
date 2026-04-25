"""
Scene-payload validation helpers for the Room Acoustics backend.

The module validates the exported scene dictionary before it is passed
to the simulation setup and solver layers.

This file contains backend-side validation of scene payload structure
and generic value ranges.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import shared.scene_keys as SK

from shared.catalogs import (
    get_band_meta,
    get_material_meta,
)
from backend.setup.room_geometry import validate_polygon

# ---------------------------------------------------------------------------
# Supported values
# ---------------------------------------------------------------------------

SUPPORTED_GEOMETRY_MODES = {"room_volume_prism"}

# ---------------------------------------------------------------------------
# Primitive validation helpers
# ---------------------------------------------------------------------------

def _require_dict(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a dictionary.")
    return value


def _require_list(value, label):
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    return value


def _require_number(value, label):
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"{label} must be a numeric value.") from exc


def _require_nonempty_string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    return value


def _require_point3(value, label):
    value = _require_list(value, label)

    if len(value) != 3:
        raise ValueError(f"{label} must contain exactly 3 coordinates.")

    return [
        _require_number(coord, f"{label}[{index}]")
        for index, coord in enumerate(value)
    ]


def _validate_unit_interval(value, label):
    value = _require_number(value, label)

    if value < 0.0 or value > 1.0:
        raise ValueError(f"{label} must be in the range [0, 1].")

    return value

# ---------------------------------------------------------------------------
# Scene-block validators
# ---------------------------------------------------------------------------

def validate_room_block(scene):
    room = _require_dict(scene.get(SK.ROOM), "scene.room")

    geometry_mode = _require_nonempty_string(
        room.get(SK.GEOMETRY_MODE),
        "scene.room.geometry_mode",
    )
    if geometry_mode not in SUPPORTED_GEOMETRY_MODES:
        raise ValueError(
            f"Unsupported geometry_mode: {geometry_mode}. "
            f"Supported values: {sorted(SUPPORTED_GEOMETRY_MODES)}"
        )

    floor_polygon = room.get(SK.FLOOR_POLYGON)
    if not isinstance(floor_polygon, list):
        raise ValueError("scene.room.floor_polygon must be a list of 2D points.")

    validate_polygon(floor_polygon)

    height = _require_number(room.get(SK.HEIGHT), "scene.room.height")
    if height <= 0.0:
        raise ValueError("scene.room.height must be > 0.")

    _require_number(room.get(SK.Z_FLOOR), "scene.room.z_floor")
    _require_nonempty_string(
        room.get(SK.SOURCE_OBJECT_NAME),
        "scene.room.source_object_name",
    )


def validate_simulation_block(scene):
    simulation = _require_dict(scene.get(SK.SIMULATION), "scene.simulation")

    fs = int(_require_number(simulation.get(SK.FS), "scene.simulation.fs"))
    if fs <= 0:
        raise ValueError("scene.simulation.fs must be > 0.")

    max_order = int(
        _require_number(
            simulation.get(SK.MAX_ORDER),
            "scene.simulation.max_order",
        )
    )
    if max_order < 0:
        raise ValueError("scene.simulation.max_order must be >= 0.")

    if SK.AIR_ABSORPTION not in simulation:
        raise ValueError("scene.simulation.air_absorption is missing.")

    if SK.ENGINE not in simulation:
        raise ValueError("scene.simulation.engine is missing.")


def validate_band_block(scene):
    band = _require_dict(scene.get(SK.BAND), "scene.band")
    band_key = _require_nonempty_string(band.get(SK.KEY), "scene.band.key")
    get_band_meta(band_key)


def validate_materials_block(scene):
    materials = _require_dict(scene.get(SK.MATERIALS), "scene.materials")

    walls_key = _require_nonempty_string(
        materials.get(SK.WALLS),
        "scene.materials.walls",
    )
    floor_key = _require_nonempty_string(
        materials.get(SK.FLOOR),
        "scene.materials.floor",
    )
    ceiling_key = _require_nonempty_string(
        materials.get(SK.CEILING),
        "scene.materials.ceiling",
    )

    get_material_meta(walls_key)
    get_material_meta(floor_key)
    get_material_meta(ceiling_key)

    material_details = materials.get(SK.MATERIAL_DETAILS, {}) or {}
    _require_dict(material_details, "scene.materials.material_details")

    for surface_key in (SK.WALLS, SK.FLOOR, SK.CEILING):
        surface_detail = material_details.get(surface_key)
        if surface_detail is None:
            continue

        surface_detail = _require_dict(
            surface_detail,
            f"scene.materials.material_details.{surface_key}",
        )

        if SK.ABSORPTION in surface_detail:
            _validate_unit_interval(
                surface_detail[SK.ABSORPTION],
                f"scene.materials.material_details.{surface_key}.absorption",
            )

        if SK.SCATTERING in surface_detail:
            _validate_unit_interval(
                surface_detail[SK.SCATTERING],
                f"scene.materials.material_details.{surface_key}.scattering",
            )


def validate_sources_block(scene):
    sources = _require_list(scene.get(SK.SOURCES), "scene.sources")

    if len(sources) == 0:
        raise ValueError(
			"scene.sources must contain at least one source."
			"Make sure at least one obkect named SRC_* exists in your Blender scene"
			)

    for index, source in enumerate(sources):
        source = _require_dict(source, f"scene.sources[{index}]")

        _require_nonempty_string(
            source.get(SK.NAME),
            f"scene.sources[{index}].name",
        )
        _require_point3(
            source.get(SK.POSITION),
            f"scene.sources[{index}].position",
        )
        _require_point3(
            source.get(SK.WORLD_POSITION),
            f"scene.sources[{index}].world_position",
        )


def validate_receiver_areas_block(scene):
    receiver_areas = _require_list(
        scene.get(SK.RECEIVER_AREAS),
        "scene.receiver_areas",
    )

    if len(receiver_areas) == 0:
        raise ValueError(
			"scene.receiver_areas must contain at least one receiver area."
			"Make sure at least one object named MAP_* exists in your Blender scene"
			)

    for area_index, area in enumerate(receiver_areas):
        area = _require_dict(area, f"scene.receiver_areas[{area_index}]")

        _require_nonempty_string(
            area.get(SK.NAME),
            f"scene.receiver_areas[{area_index}].name",
        )

        mapping = _require_dict(
            area.get(SK.MAPPING),
            f"scene.receiver_areas[{area_index}].mapping",
        )

        _require_nonempty_string(
            mapping.get(SK.NAME),
            f"scene.receiver_areas[{area_index}].mapping.name",
        )

        spacing = _require_number(
            mapping.get(SK.SPACING),
            f"scene.receiver_areas[{area_index}].mapping.spacing",
        )
        if spacing <= 0.0:
            raise ValueError(
                f"scene.receiver_areas[{area_index}].mapping.spacing must be > 0."
            )

        num_x = int(
            _require_number(
                mapping.get(SK.NUM_X),
                f"scene.receiver_areas[{area_index}].mapping.num_x",
            )
        )
        num_y = int(
            _require_number(
                mapping.get(SK.NUM_Y),
                f"scene.receiver_areas[{area_index}].mapping.num_y",
            )
        )
        num_receivers = int(
            _require_number(
                mapping.get(SK.NUM_RECEIVERS),
                f"scene.receiver_areas[{area_index}].mapping.num_receivers",
            )
        )

        if num_x <= 0 or num_y <= 0:
            raise ValueError(
                f"scene.receiver_areas[{area_index}].mapping.num_x and num_y must be > 0."
            )

        if num_receivers <= 0:
            raise ValueError(
                f"scene.receiver_areas[{area_index}].mapping.num_receivers must be > 0."
            )

        _require_number(
            mapping.get(SK.WORLD_Z),
            f"scene.receiver_areas[{area_index}].mapping.world_z",
        )

        area_width = _require_number(
            mapping.get(SK.AREA_WIDTH),
            f"scene.receiver_areas[{area_index}].mapping.area_width",
        )
        area_depth = _require_number(
            mapping.get(SK.AREA_DEPTH),
            f"scene.receiver_areas[{area_index}].mapping.area_depth",
        )

        if area_width <= 0.0 or area_depth <= 0.0:
            raise ValueError(
                f"scene.receiver_areas[{area_index}].mapping area dimensions must be > 0."
            )

        polygon = mapping.get(SK.POLYGON)
        if not isinstance(polygon, list):
            raise ValueError(
                f"scene.receiver_areas[{area_index}].mapping.polygon must be a list."
            )

        validate_polygon(polygon)

        receivers = _require_list(
            area.get(SK.RECEIVERS),
            f"scene.receiver_areas[{area_index}].receivers",
        )

        if len(receivers) == 0:
            raise ValueError(
                f"scene.receiver_areas[{area_index}] must contain at least one receiver."
            )

        for receiver_index, receiver in enumerate(receivers):
            receiver = _require_dict(
                receiver,
                f"scene.receiver_areas[{area_index}].receivers[{receiver_index}]",
            )

            int(
                _require_number(
                    receiver.get(SK.ID),
                    f"scene.receiver_areas[{area_index}].receivers[{receiver_index}].id",
                )
            )
            _require_point3(
                receiver.get(SK.POSITION),
                f"scene.receiver_areas[{area_index}].receivers[{receiver_index}].position",
            )
            _require_point3(
                receiver.get(SK.WORLD_POSITION),
                f"scene.receiver_areas[{area_index}].receivers[{receiver_index}].world_position",
            )

# ---------------------------------------------------------------------------
# Public validation entry-point
# ---------------------------------------------------------------------------

def validate_scene_payload(scene):
    _require_dict(scene, "scene")

    validate_room_block(scene)
    validate_simulation_block(scene)
    validate_band_block(scene)
    validate_materials_block(scene)
    validate_sources_block(scene)
    validate_receiver_areas_block(scene)
