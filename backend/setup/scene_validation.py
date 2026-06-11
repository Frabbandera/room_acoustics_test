"""
Scene-payload validation helpers for the Room Acoustics backend.
"""

from shared.catalogs import get_band_meta, get_material_meta
import shared.scene_keys as SK

def _require_dict(value, label):
    if not isinstance(value, dict): raise ValueError(f"{label} must be a dictionary.")
    return value

def _require_list(value, label):
    if not isinstance(value, list): raise ValueError(f"{label} must be a list.")
    return value

def _require_number(value, label):
    try: return float(value)
    except Exception as exc: raise ValueError(f"{label} must be a numeric value.") from exc

def _require_nonempty_string(value, label):
    if isinstance(value, (int, float)): value = str(value)
    if not isinstance(value, str) or not value.strip(): raise ValueError(f"{label} must be a non-empty string.")
    return value

def _require_point3(value, label):
    if not isinstance(value, list) or len(value) != 3: raise ValueError(f"{label} must contain exactly 3 coordinates.")
    return [float(coord) for coord in value]

def _validate_unit_interval(value, label):
    num = _require_number(value, label)
    if num < 0.0 or num > 1.0: raise ValueError(f"{label} must be in the range [0, 1].")
    return num

def validate_room_block(scene: dict):
    room = _require_dict(scene.get(SK.ROOM, {}), "scene.room")
    geometry_mode = _require_nonempty_string(room.get(SK.GEOMETRY_MODE), "scene.room.geometry_mode")

    if geometry_mode != "3d_faces":
        raise ValueError(f"Unsupported geometry_mode: {geometry_mode}. Supported values: ['3d_faces'].")

    faces = _require_list(room.get("faces"), "scene.room.faces")
    if len(faces) == 0: raise ValueError("scene.room.faces must be a non-empty list of 3D polygons.")
        
    for i, face in enumerate(faces):
        verts = _require_list(face.get("vertices"), f"face {i} vertices")
        if len(verts) < 3: raise ValueError(f"Each face must have a 'vertices' list with at least 3 points. Face {i} failed.")
        for v in verts: _require_point3(v, "vertex")

        surface_type = _require_nonempty_string(face.get("surface_type"), f"face {i} surface_type")
        if surface_type not in ["floor", "ceiling", "wall", "furniture"]: raise ValueError(f"Invalid surface_type. Must be 'floor', 'ceiling', 'wall', or 'furniture'. Face {i} failed.")

def validate_simulation_block(scene: dict):
    simulation = _require_dict(scene.get(SK.SIMULATION, {}), "scene.simulation")
    fs = _require_number(simulation.get(SK.FS), "scene.simulation.fs")
    if fs <= 0.0: raise ValueError("scene.simulation.fs must be > 0.")
    max_order = int(_require_number(simulation.get(SK.MAX_ORDER), "scene.simulation.max_order"))
    if max_order < 0: raise ValueError("scene.simulation.max_order must be >= 0.")
    if SK.AIR_ABSORPTION not in simulation: raise ValueError("scene.simulation.air_absorption is missing.")
    if SK.ENGINE not in simulation: raise ValueError("scene.simulation.engine is missing.")

def validate_band_block(scene: dict):
    band = _require_dict(scene.get(SK.BAND, {}), "scene.band")
    band_key = _require_nonempty_string(band.get(SK.KEY), "scene.band.key")
    get_band_meta(band_key)

def validate_materials_block(scene: dict):
    materials = _require_dict(scene.get(SK.MATERIALS, {}), "scene.materials")
    _require_nonempty_string(materials.get(SK.WALLS), "scene.materials.walls")
    _require_nonempty_string(materials.get(SK.FLOOR), "scene.materials.floor")
    _require_nonempty_string(materials.get(SK.CEILING), "scene.materials.ceiling")
    material_details = materials.get(SK.MATERIAL_DETAILS, {})
    for surface_key, surface_detail in material_details.items():
        if surface_detail is not None:
            _validate_unit_interval(surface_detail.get(SK.ABSORPTION), f"scene.materials.material_details.{surface_key}.absorption")
            if SK.SCATTERING in surface_detail:
                _validate_unit_interval(surface_detail.get(SK.SCATTERING), f"scene.materials.material_details.{surface_key}.scattering")

def validate_sources_block(scene: dict):
    sources = _require_list(scene.get(SK.SOURCES, []), "scene.sources")
    if len(sources) == 0: raise ValueError("scene.sources must contain at least one source.")
    for i, source in enumerate(sources):
        _require_nonempty_string(source.get(SK.NAME), f"scene.sources[{i}].name")
        _require_point3(source.get(SK.POSITION), f"scene.sources[{i}].position")
        _require_point3(source.get(SK.WORLD_POSITION), f"scene.sources[{i}].world_position")

def validate_receiver_areas_block(scene: dict):
    receiver_areas = _require_list(scene.get(SK.RECEIVER_AREAS, []), "scene.receiver_areas")
    if len(receiver_areas) == 0: raise ValueError("scene.receiver_areas must contain at least one receiver area.")
    for i, area in enumerate(receiver_areas):
        mapping = _require_dict(area.get(SK.MAPPING), f"scene.receiver_areas[{i}].mapping")
        _require_nonempty_string(mapping.get(SK.NAME), f"scene.receiver_areas[{i}].mapping.name")
        spacing = _require_number(mapping.get(SK.SPACING), f"scene.receiver_areas[{i}].mapping.spacing")
        if spacing <= 0.0: raise ValueError(f"scene.receiver_areas[{i}].mapping.spacing must be > 0.")
        num_x = int(_require_number(mapping.get(SK.NUM_X), f"scene.receiver_areas[{i}].mapping.num_x"))
        num_y = int(_require_number(mapping.get(SK.NUM_Y), f"scene.receiver_areas[{i}].mapping.num_y"))
        num_receivers = int(_require_number(mapping.get(SK.NUM_RECEIVERS), f"scene.receiver_areas[{i}].mapping.num_receivers"))
        if num_x <= 0 or num_y <= 0: raise ValueError(f"scene.receiver_areas[{i}].mapping.num_x and num_y must be > 0.")
        if num_receivers <= 0: raise ValueError(f"scene.receiver_areas[{i}].mapping.num_receivers must be > 0.")
        _require_number(mapping.get(SK.WORLD_Z), f"scene.receiver_areas[{i}].mapping.world_z")
        area_width = _require_number(mapping.get(SK.AREA_WIDTH), f"scene.receiver_areas[{i}].mapping.area_width")
        area_depth = _require_number(mapping.get(SK.AREA_DEPTH), f"scene.receiver_areas[{i}].mapping.area_depth")
        if area_width <= 0.0 or area_depth <= 0.0: raise ValueError(f"scene.receiver_areas[{i}].mapping area dimensions must be > 0.")
        polygon = mapping.get(SK.POLYGON)
        if not isinstance(polygon, list): raise ValueError(f"scene.receiver_areas[{i}].mapping.polygon must be a list.")
        receivers = _require_list(area.get(SK.RECEIVERS), f"scene.receiver_areas[{i}].receivers")
        if len(receivers) == 0: raise ValueError(f"scene.receiver_areas[{i}] must contain at least one receiver.")
        for j, receiver in enumerate(receivers):
            _require_nonempty_string(receiver.get(SK.ID), f"scene.receiver_areas[{i}].receivers[{j}].id")
            _require_point3(receiver.get(SK.POSITION), f"scene.receiver_areas[{i}].receivers[{j}].position")
            _require_point3(receiver.get(SK.WORLD_POSITION), f"scene.receiver_areas[{i}].receivers[{j}].world_position")

def validate_scene_payload(scene: dict):
    validate_room_block(scene)
    validate_simulation_block(scene)
    validate_band_block(scene)
    validate_materials_block(scene)
    validate_sources_block(scene)
    validate_receiver_areas_block(scene)
