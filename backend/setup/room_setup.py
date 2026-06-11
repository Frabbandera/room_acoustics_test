"""
Common room-setup helpers for the Room Acoustics backend.
"""

import shared.result_keys as RK
import shared.scene_keys as SK

from backend.materials import (
    get_band_label,
    get_material_absorption,
    get_material_label,
    get_material_scattering,
)
from backend.postprocessing.multi_area import flatten_receiver_areas
from backend.setup.room_builder import (
    add_microphones_to_room,
    add_sources_to_room,
    build_pra_room,
)

def _resolve_surface_coefficients(materials_cfg, surface_key, material_key, band_key, *, use_material_scattering):
    material_details = materials_cfg.get(SK.MATERIAL_DETAILS, {}) or {}
    surface_detail = material_details.get(surface_key, {}) or {}

    absorption = surface_detail.get(SK.ABSORPTION)
    if absorption is None: absorption = get_material_absorption(material_key, band_key)

    if use_material_scattering:
        scattering = surface_detail.get(SK.SCATTERING)
        if scattering is None: scattering = get_material_scattering(material_key)
    else:
        scattering = 0.0

    return float(absorption), float(scattering)

def _resolve_common_scene_configuration(scene, *, use_material_scattering, override_max_order=None):
    faces = scene[SK.ROOM]["faces"]
    # Separate room faces from furniture faces
    room_faces = [f for f in faces if f.get("surface_type") != "furniture"]
    furniture_faces = [f for f in faces if f.get("surface_type") == "furniture"]
    fs = int(scene[SK.SIMULATION][SK.FS])

    scene_max_order = int(scene[SK.SIMULATION][SK.MAX_ORDER])
    if override_max_order is None: max_order = scene_max_order
    else: max_order = int(override_max_order)

    if max_order < 0: raise ValueError("Invalid max_order: it must be >= 0.")
    air_absorption = bool(scene[SK.SIMULATION][SK.AIR_ABSORPTION])
    selected_band_key = scene[SK.BAND][SK.KEY]

    materials_cfg = scene[SK.MATERIALS]
    walls_key = materials_cfg[SK.WALLS]
    floor_key = materials_cfg[SK.FLOOR]
    ceiling_key = materials_cfg[SK.CEILING]

    sources = scene[SK.SOURCES]
    receiver_areas_in = scene[SK.RECEIVER_AREAS]

    if len(sources) == 0: raise ValueError("The source list is empty.")
    if len(receiver_areas_in) == 0: raise ValueError("The receiver area list is empty.")

    wall_abs, wall_scat = _resolve_surface_coefficients(materials_cfg, SK.WALLS, walls_key, selected_band_key, use_material_scattering=use_material_scattering)
    floor_abs, floor_scat = _resolve_surface_coefficients(materials_cfg, SK.FLOOR, floor_key, selected_band_key, use_material_scattering=use_material_scattering)
    ceiling_abs, ceiling_scat = _resolve_surface_coefficients(materials_cfg, SK.CEILING, ceiling_key, selected_band_key, use_material_scattering=use_material_scattering)

    band_info = {RK.KEY: selected_band_key, RK.LABEL: get_band_label(selected_band_key)}
    materials_info = {
        RK.WALLS: {RK.KEY: walls_key, RK.LABEL: get_material_label(walls_key), RK.ABSORPTION: wall_abs, RK.SCATTERING: wall_scat},
        RK.FLOOR: {RK.KEY: floor_key, RK.LABEL: get_material_label(floor_key), RK.ABSORPTION: floor_abs, RK.SCATTERING: floor_scat},
        RK.CEILING: {RK.KEY: ceiling_key, RK.LABEL: get_material_label(ceiling_key), RK.ABSORPTION: ceiling_abs, RK.SCATTERING: ceiling_scat},
    }

    return {
        "faces": faces,
        "band_key": selected_band_key,
        "fs": fs,
        "scene_max_order": scene_max_order,
        "max_order": max_order,
        "air_absorption": air_absorption,
        "sources": sources,
        "receiver_areas_in": receiver_areas_in,
        "wall_abs": wall_abs,
        "floor_abs": floor_abs,
        "ceiling_abs": ceiling_abs,
        "wall_scat": wall_scat,
        "floor_scat": floor_scat,
        "ceiling_scat": ceiling_scat,
        "band_info": band_info,
        "materials_info": materials_info,
    }

def build_room_setup_from_scene(scene, *, ray_tracing=False, ray_tracing_kwargs=None, use_material_scattering=None, override_max_order=None):
    if use_material_scattering is None: use_material_scattering = bool(ray_tracing)

    cfg = _resolve_common_scene_configuration(scene, use_material_scattering=use_material_scattering, override_max_order=override_max_order)
    room = build_pra_room(cfg, ray_tracing=ray_tracing, ray_tracing_kwargs=ray_tracing_kwargs)
    source_names = add_sources_to_room(room, cfg["sources"])
    flat_receivers, area_spans = flatten_receiver_areas(cfg["receiver_areas_in"], room)
    add_microphones_to_room(room, flat_receivers)

    return {
        "room": room, "fs": cfg["fs"], "scene_max_order": cfg["scene_max_order"], "effective_max_order": cfg["max_order"],
        "source_names": source_names, "flat_receivers": flat_receivers, "area_spans": area_spans,
        "band_info": cfg["band_info"], "materials_info": cfg["materials_info"],
    }
