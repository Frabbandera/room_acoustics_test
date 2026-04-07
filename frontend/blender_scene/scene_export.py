"""
Scene-export helpers for the Room Acoustics frontend.

The module builds the scene dictionary exported from Blender to the
simulation backend.

This file contains scene serialization logic for room geometry, sources,
receiver areas, materials, and simulation settings.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import bpy

import shared.scene_keys as SK

from backend.materials import (
    get_material_absorption,
    get_material_scattering,
)

from .geometry import (
    ROOM_DEF_DISPLAY_LABEL,
    ROOM_DEF_FLOOR_POLYGON_WORLD_2D,
    ROOM_DEF_HEIGHT,
    ROOM_DEF_MODE,
    ROOM_DEF_SOURCE_OBJECT_NAME,
    ROOM_DEF_Z_FLOOR,
    centered_axis_points,
    extract_room_definition,
    get_mapping_objs,
    get_single_face_polygon_world_2d,
    point_in_polygon_2d,
    validate_not_rotated,
)

# ---------------------------------------------------------------------------
# Source export helpers
# ---------------------------------------------------------------------------

def _get_sorted_source_objects():
    source_objects = sorted(
        [obj for obj in bpy.data.objects if obj.name.startswith("SRC_")],
        key=lambda obj: obj.name,
    )

    if not source_objects:
        raise RuntimeError(
            "No valid sources found. Create at least one object named 'SRC_*'."
        )

    return source_objects


def _validate_sources_inside_room(
    source_objects,
    floor_polygon_world_2d,
    z_floor,
    room_height,
    room_label,
):
    z_ceil = z_floor + room_height

    for source_obj in source_objects:
        source_pos_world = source_obj.matrix_world.translation

        if source_pos_world.z < z_floor or source_pos_world.z > z_ceil:
            raise RuntimeError(f"Source {source_obj.name} is outside the room along Z.")

        if not point_in_polygon_2d(
            (float(source_pos_world.x), float(source_pos_world.y)),
            floor_polygon_world_2d,
            include_borders=True,
        ):
            raise RuntimeError(
                f"Source {source_obj.name} is outside the footprint defined by "
                f"{room_label}."
            )


def _build_sources_data(source_objects, z_floor):
    sources_data = []

    for source_obj in source_objects:
        source_pos_world = source_obj.matrix_world.translation

        source_room_position = [
            float(source_pos_world.x),
            float(source_pos_world.y),
            float(source_pos_world.z - z_floor),
        ]

        sources_data.append({
            SK.NAME: source_obj.name,
            SK.POSITION: source_room_position,
            SK.WORLD_POSITION: [
                float(source_pos_world.x),
                float(source_pos_world.y),
                float(source_pos_world.z),
            ],
        })

    return sources_data

# ---------------------------------------------------------------------------
# Receiver-area export helpers
# ---------------------------------------------------------------------------

def _build_receivers_for_mapping(
    mapping_obj,
    props,
    floor_polygon_world_2d,
    z_floor,
    room_height,
    room_label,
):
    validate_not_rotated(mapping_obj, mapping_obj.name)

    mapping_polygon_world_2d, map_z = get_single_face_polygon_world_2d(
        mapping_obj,
        mapping_obj.name,
    )

    if map_z < z_floor or map_z > z_floor + room_height:
        raise RuntimeError(
            f"The Z elevation of '{mapping_obj.name}' is outside the room."
        )

    for point in mapping_polygon_world_2d:
        if not point_in_polygon_2d(
            tuple(point),
            floor_polygon_world_2d,
            include_borders=True,
        ):
            raise RuntimeError(
                f"All vertices of '{mapping_obj.name}' must lie inside {room_label}."
            )

    xs = [point[0] for point in mapping_polygon_world_2d]
    ys = [point[1] for point in mapping_polygon_world_2d]

    map_min_x = min(xs)
    map_max_x = max(xs)
    map_min_y = min(ys)
    map_max_y = max(ys)

    map_center_x = 0.5 * (map_min_x + map_max_x)
    map_center_y = 0.5 * (map_min_y + map_max_y)

    map_width = map_max_x - map_min_x
    map_depth = map_max_y - map_min_y

    if map_width <= 0.0 or map_depth <= 0.0:
        raise RuntimeError(f"'{mapping_obj.name}' has an invalid bounding box.")

    x_points_world = centered_axis_points(
        map_center_x,
        map_width,
        props.grid_spacing,
    )
    y_points_world = centered_axis_points(
        map_center_y,
        map_depth,
        props.grid_spacing,
    )

    receivers = []
    receiver_id = 0

    for y_world in y_points_world:
        for x_world in x_points_world:
            point = (float(x_world), float(y_world))

            if not point_in_polygon_2d(
                point,
                mapping_polygon_world_2d,
                include_borders=True,
            ):
                continue

            if not point_in_polygon_2d(
                point,
                floor_polygon_world_2d,
                include_borders=True,
            ):
                raise RuntimeError(
                    "Generated receiver outside the room footprint: "
                    f"({x_world:.3f}, {y_world:.3f})"
                )

            room_position = [
                float(x_world),
                float(y_world),
                float(map_z - z_floor),
            ]

            receivers.append({
                SK.ID: receiver_id,
                SK.POSITION: room_position,
                SK.WORLD_POSITION: [float(x_world), float(y_world), float(map_z)],
            })
            receiver_id += 1

    if not receivers:
        raise RuntimeError(f"No receivers were generated on '{mapping_obj.name}'.")

    if len(receivers) > props.max_receivers:
        raise RuntimeError(
            f"Too many receivers were generated on '{mapping_obj.name}' "
            f"({len(receivers)}). Increase grid spacing or raise max receivers."
        )

    return {
        SK.NAME: mapping_obj.name,
        SK.MAPPING: {
            SK.NAME: mapping_obj.name,
            SK.SPACING: float(props.grid_spacing),
            SK.NUM_X: len(x_points_world),
            SK.NUM_Y: len(y_points_world),
            SK.NUM_RECEIVERS: len(receivers),
            SK.WORLD_Z: float(map_z),
            SK.AREA_WIDTH: map_width,
            SK.AREA_DEPTH: map_depth,
            SK.POLYGON: mapping_polygon_world_2d,
        },
        SK.RECEIVERS: receivers,
    }


def _build_receiver_areas_data(
    props,
    floor_polygon_world_2d,
    z_floor,
    room_height,
    room_label,
):
    receiver_areas_data = []

    for mapping_obj in get_mapping_objs():
        receiver_areas_data.append(
            _build_receivers_for_mapping(
                mapping_obj,
                props,
                floor_polygon_world_2d,
                z_floor,
                room_height,
                room_label,
            )
        )

    if not receiver_areas_data:
        raise RuntimeError("No valid receiver areas were found.")

    return receiver_areas_data

# ---------------------------------------------------------------------------
# Material export helper
# ---------------------------------------------------------------------------

def _build_material_details(props, selected_band_key):
    return {
        SK.WALLS: {
            SK.KEY: props.wall_material,
            SK.ABSORPTION: get_material_absorption(
                props.wall_material,
                selected_band_key,
            ),
            SK.SCATTERING: get_material_scattering(props.wall_material),
        },
        SK.FLOOR: {
            SK.KEY: props.floor_material,
            SK.ABSORPTION: get_material_absorption(
                props.floor_material,
                selected_band_key,
            ),
            SK.SCATTERING: get_material_scattering(props.floor_material),
        },
        SK.CEILING: {
            SK.KEY: props.ceiling_material,
            SK.ABSORPTION: get_material_absorption(
                props.ceiling_material,
                selected_band_key,
            ),
            SK.SCATTERING: get_material_scattering(props.ceiling_material),
        },
    }

# ---------------------------------------------------------------------------
# Main scene export function
# ---------------------------------------------------------------------------

def build_scene_dict(context):
    props = context.scene.ra_test_props

    room_def = extract_room_definition()
    room_label = room_def[ROOM_DEF_DISPLAY_LABEL]
    room_mode = room_def[ROOM_DEF_MODE]
    room_source_object_name = room_def[ROOM_DEF_SOURCE_OBJECT_NAME]
    floor_polygon_world_2d = room_def[ROOM_DEF_FLOOR_POLYGON_WORLD_2D]
    z_floor = room_def[ROOM_DEF_Z_FLOOR]
    room_height = room_def[ROOM_DEF_HEIGHT]

    source_objects = _get_sorted_source_objects()
    _validate_sources_inside_room(
        source_objects,
        floor_polygon_world_2d,
        z_floor,
        room_height,
        room_label,
    )

    sources_data = _build_sources_data(source_objects, z_floor)
    receiver_areas_data = _build_receiver_areas_data(
        props,
        floor_polygon_world_2d,
        z_floor,
        room_height,
        room_label,
    )

    selected_band_key = props.selected_band
    material_details = _build_material_details(props, selected_band_key)

    return {
        SK.ROOM: {
            SK.FLOOR_POLYGON: floor_polygon_world_2d,
            SK.HEIGHT: room_height,
            SK.Z_FLOOR: z_floor,
            SK.GEOMETRY_MODE: room_mode,
            SK.SOURCE_OBJECT_NAME: room_source_object_name,
        },
        SK.SIMULATION: {
            SK.ENGINE: props.simulation_engine,
            SK.USE_FIXED_RANDOM_SEED: bool(props.use_fixed_random_seed),
            SK.RANDOM_SEED: int(props.random_seed),
            SK.RAY_TRACING: {
                SK.N_RAYS: int(props.rt_n_rays),
                SK.RECEIVER_RADIUS: float(props.rt_receiver_radius),
                SK.HIST_BIN_SIZE: float(props.rt_hist_bin_size),
                SK.ENERGY_THRES: float(props.rt_energy_thres),
                SK.TIME_THRES: float(props.rt_time_thres),
            },
            SK.FS: int(props.fs),
            SK.MAX_ORDER: int(props.max_order),
            SK.AIR_ABSORPTION: bool(props.air_absorption),
        },
        SK.BAND: {
            SK.KEY: props.selected_band,
        },
        SK.MATERIALS: {
            SK.WALLS: props.wall_material,
            SK.FLOOR: props.floor_material,
            SK.CEILING: props.ceiling_material,
            SK.MATERIAL_DETAILS: material_details,
        },
        SK.SOURCES: sources_data,
        SK.RECEIVER_AREAS: receiver_areas_data,
    }