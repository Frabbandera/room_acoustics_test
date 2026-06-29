"""
Scene-export helpers for the Room Acoustics frontend.
"""

import bpy
import shared.scene_keys as SK

from backend.materials import (
    get_material_absorption,
    get_material_scattering,
)
from .geometry import (
    ROOM_DEF_DISPLAY_LABEL,
    ROOM_DEF_MODE,
    ROOM_DEF_SOURCE_OBJECT_NAME,
    ROOM_DEF_FACES,
    centered_axis_points,
    extract_room_definition,
    get_mapping_objs,
    get_single_face_polygon_world_2d,
    point_in_polygon_2d,
    validate_not_rotated,
)

def _get_sorted_source_objects():
    source_objects = sorted(
        [obj for obj in bpy.data.objects if obj.name.startswith("SRC_")],
        key=lambda obj: obj.name,
    )
    if not source_objects:
        raise RuntimeError("No valid sources found. Create at least one object named 'SRC_*'.")
    return source_objects

def _validate_sources(source_objects):
    pass

def _build_sources_data(source_objects):
    sources_data = []
    for source_obj in source_objects:
        source_pos_world = source_obj.matrix_world.translation
        position_3d = [float(source_pos_world.x), float(source_pos_world.y), float(source_pos_world.z)]
        sources_data.append({
            SK.NAME: source_obj.name,
            SK.POSITION: position_3d,
            SK.WORLD_POSITION: position_3d,
        })
    return sources_data

def _build_receivers_for_mapping(mapping_obj, props):
    validate_not_rotated(mapping_obj, mapping_obj.name)
    mapping_polygon_world_2d, map_z = get_single_face_polygon_world_2d(mapping_obj, mapping_obj.name)

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

    x_points_world = centered_axis_points(map_center_x, map_width, props.grid_spacing)
    y_points_world = centered_axis_points(map_center_y, map_depth, props.grid_spacing)

    receivers = []
    receiver_id = 0

    for y_world in y_points_world:
        for x_world in x_points_world:
            point = (float(x_world), float(y_world))

            if not point_in_polygon_2d(point, mapping_polygon_world_2d, include_borders=True):
                continue

            position_3d = [float(x_world), float(y_world), float(map_z)]

            receivers.append({
                SK.ID: receiver_id,
                SK.POSITION: position_3d,
                SK.WORLD_POSITION: position_3d,
            })
            receiver_id += 1

    if not receivers:
        raise RuntimeError(f"No receivers were generated on '{mapping_obj.name}'.")

    if len(receivers) > props.max_receivers:
        raise RuntimeError(f"Too many receivers were generated on '{mapping_obj.name}'. Increase grid spacing.")

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

def _build_receiver_areas_data(props):
    receiver_areas_data = []
    for mapping_obj in get_mapping_objs():
        receiver_areas_data.append(_build_receivers_for_mapping(mapping_obj, props))
    if not receiver_areas_data:
        raise RuntimeError("No valid receiver areas were found.")
    return receiver_areas_data

def _build_material_details(props, selected_band_key):
    return {
        SK.WALLS: {
            SK.KEY: props.wall_material,
            SK.ABSORPTION: get_material_absorption(props.wall_material, selected_band_key),
            SK.SCATTERING: get_material_scattering(props.wall_material),
        },
        SK.FLOOR: {
            SK.KEY: props.floor_material,
            SK.ABSORPTION: get_material_absorption(props.floor_material, selected_band_key),
            SK.SCATTERING: get_material_scattering(props.floor_material),
        },
        SK.CEILING: {
            SK.KEY: props.ceiling_material,
            SK.ABSORPTION: get_material_absorption(props.ceiling_material, selected_band_key),
            SK.SCATTERING: get_material_scattering(props.ceiling_material),
        },
    }

def build_scene_dict(context):
    props = context.scene.ra_test_props
    room_def = extract_room_definition()
    room_mode = room_def[ROOM_DEF_MODE]
    room_source_object_name = room_def[ROOM_DEF_SOURCE_OBJECT_NAME]
    faces_3d = room_def[ROOM_DEF_FACES]

    # Compute zone-based furniture absorption map
    # Divide room into 3x3 grid of zones
    all_verts = [v for face in faces_3d for v in face["vertices"]]
    if all_verts:
        import numpy as np
        verts_array = np.array(all_verts)
        room_min_x = float(np.min(verts_array[:, 0]))
        room_max_x = float(np.max(verts_array[:, 0]))
        room_min_y = float(np.min(verts_array[:, 1]))
        room_max_y = float(np.max(verts_array[:, 1]))
    else:
        room_min_x, room_max_x = -3.0, 3.0
        room_min_y, room_max_y = -2.0, 2.0

    zone_grid = 3
    zone_absorption = {}
    for zi in range(zone_grid):
        for zj in range(zone_grid):
            zone_absorption[f"{zi}_{zj}"] = 0.0

    for obj in bpy.data.objects:
        if not obj.get("acoustic_object"):
            continue
        mat_key = obj.get("acoustic_material", "reflective_plaster")
        fx = float(obj.location.x)
        fy = float(obj.location.y)

        # Find which zone this furniture is in
        zone_i = min(int((fx - room_min_x) / (room_max_x - room_min_x) * zone_grid), zone_grid - 1)
        zone_j = min(int((fy - room_min_y) / (room_max_y - room_min_y) * zone_grid), zone_grid - 1)
        zone_i = max(0, zone_i)
        zone_j = max(0, zone_j)
        zone_key = f"{zone_i}_{zone_j}"

        # Get absorption coefficient for this material at 500Hz as reference
        from backend.materials import get_material_absorption
        abs_coeff = get_material_absorption(mat_key, props.selected_band)
        zone_absorption[zone_key] = min(1.0, zone_absorption[zone_key] + abs_coeff * 0.3)

        print(f"[RA] {obj.name} placed in zone {zone_key} with absorption {abs_coeff:.2f}")


    source_objects = _get_sorted_source_objects()
    _validate_sources(source_objects)
    sources_data = _build_sources_data(source_objects)
    receiver_areas_data = _build_receiver_areas_data(props)

    selected_band_key = props.selected_band
    material_details = _build_material_details(props, selected_band_key)

    return {
        SK.ROOM: {
            SK.GEOMETRY_MODE: room_mode,
            SK.SOURCE_OBJECT_NAME: room_source_object_name,
            "faces": faces_3d,
            "zone_absorption": zone_absorption,
            "room_bounds": {
                "min_x": room_min_x,
                "max_x": room_max_x,
                "min_y": room_min_y,
                "max_y": room_max_y,
            },
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
	    "source_swl": float(props.source_swl),
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
