"""
Pyroomacoustics room builders for the Room Acoustics backend.
Hybrid approach: 3D faces for geometry, bounding box for ISM metrics.
"""

import numpy as np
import pyroomacoustics as pra
import shared.result_keys as RK
import shared.scene_keys as SK
from backend.setup.room_geometry import build_prismatic_room_walls


def _triangulate_face(vertices):
    """Split a polygon face into triangles using fan triangulation."""
    triangles = []
    for i in range(1, len(vertices) - 1):
        triangles.append([vertices[0], vertices[i], vertices[i + 1]])
    return triangles

def _compute_room_center(faces):
    """Compute the centroid of all vertices in the room."""
    all_verts = [v for face in faces for v in face["vertices"]]
    return np.mean(all_verts, axis=0)

def _ensure_inward_normal(corners, room_center):
    """Flip triangle corners if normal points away from room center."""
    v0 = corners[:, 0]
    v1 = corners[:, 1]
    v2 = corners[:, 2]
    edge1 = v1 - v0
    edge2 = v2 - v0
    normal = np.cross(edge1, edge2)
    tri_center = (v0 + v1 + v2) / 3.0
    to_room_center = room_center - tri_center
    if np.dot(normal, to_room_center) < 0:
        corners = corners[:, [0, 2, 1]]
    return corners

def _is_ceiling_sloped(faces, tol=0.05):
    """
    Check if the ceiling is sloped.
    Returns True if ceiling vertices have more than tol meters of Z variation.
    """
    ceiling_faces = [f for f in faces if f["surface_type"] == "ceiling"]
    if not ceiling_faces:
        return False

    ceiling_z_values = [v[2] for f in ceiling_faces for v in f["vertices"]]
    z_range = max(ceiling_z_values) - min(ceiling_z_values)

    if z_range > tol:
        print(f"[RA] Sloped ceiling detected (Z range: {z_range:.3f}m) — using area-weighted average height")
        return True

    print(f"[RA] Flat ceiling detected — using exact height")
    return False


def _extract_bounding_box(faces):
    """
    Extract a bounding box from 3D faces.
    Uses exact height for flat ceilings, area-weighted average for sloped ones.
    """
    all_verts = np.array([v for face in faces for v in face["vertices"]])

    min_x = float(np.min(all_verts[:, 0]))
    max_x = float(np.max(all_verts[:, 0]))
    min_y = float(np.min(all_verts[:, 1]))
    max_y = float(np.max(all_verts[:, 1]))
    min_z = float(np.min(all_verts[:, 2]))
    max_z = float(np.max(all_verts[:, 2]))

    floor_polygon = [
        [min_x, min_y],
        [max_x, min_y],
        [max_x, max_y],
        [min_x, max_y],
    ]

    if _is_ceiling_sloped(faces):
        # Use area-weighted average height for sloped ceilings
        height = _compute_average_height(faces)
        print(f"[RA] Using area-weighted height: {height:.3f}m")
    else:
        # Use exact height for flat ceilings
        height = max_z - min_z
        print(f"[RA] Using exact height: {height:.3f}m")

    return floor_polygon, height, min_z

def build_pra_room(cfg, *, ray_tracing=False, ray_tracing_kwargs=None):
    """
    Build a Pyroomacoustics room using a bounding box extracted from 3D faces.
    This ensures correct ISM reflections for acoustic metric computation.
    """
    faces = cfg["faces"]

    # Separate room faces from furniture faces
    room_faces = [f for f in faces if f.get("surface_type") != "furniture"]
    furniture_faces = [f for f in faces if f.get("surface_type") == "furniture"]

    # Extract bounding box from room faces only
    floor_polygon, height, z_floor = _extract_bounding_box(room_faces)

    # Build walls using the original prismatic room approach
    walls = build_prismatic_room_walls(
        floor_polygon=floor_polygon,
        height=height,
        wall_abs=cfg["wall_abs"],
        floor_abs=cfg["floor_abs"],
        ceiling_abs=cfg["ceiling_abs"],
        wall_scat=cfg["wall_scat"],
        floor_scat=cfg["floor_scat"],
        ceiling_scat=cfg["ceiling_scat"],
    )
    # Add furniture faces with their own materials
    from backend.materials import get_material_absorption, get_material_scattering
    selected_band_key = cfg.get("band_key", "500")
    room_center = _compute_room_center(room_faces)

    for i, face in enumerate(furniture_faces):
        mat_key = face.get("material_key", "reflective_plaster")
        abs_val = get_material_absorption(mat_key, selected_band_key)
        scat_val = get_material_scattering(mat_key)

        abs_coeff = np.array([abs_val], dtype=np.float32)
        scat_coeff = np.array([scat_val], dtype=np.float32)

        triangles = _triangulate_face(face["vertices"])
        for tri in triangles:
            corners = np.array(tri, dtype=np.float32).T
            corners = _ensure_inward_normal(corners, room_center)
            try:
                wall = pra.wall_factory(
                    corners,
                    absorption=abs_coeff,
                    scattering=scat_coeff,
                    name=f"furniture_{i}"
                )
                walls.append(wall)
            except Exception:
                pass

    room_kwargs = {
        "walls": walls,
        "fs": cfg["fs"],
        "max_order": cfg["max_order"],
        "air_absorption": cfg["air_absorption"],
    }

    if ray_tracing:
        room_kwargs["ray_tracing"] = True

    room = pra.Room(**room_kwargs)

    if ray_tracing:
        rt_kwargs = dict(ray_tracing_kwargs or {})
        room.set_ray_tracing(**rt_kwargs)

    # Store z_floor offset so source positions can be adjusted
    room._z_floor_offset = z_floor

    return room


def add_sources_to_room(room, sources):
    source_names = []
    z_offset = getattr(room, '_z_floor_offset', 0.0)

    for source in sources:
        source_name = source[SK.NAME]
        source_position = np.array(source[SK.POSITION], dtype=float)

        # Adjust Z position relative to bounding box floor
        adjusted_position = source_position.copy()
        adjusted_position[2] = source_position[2] - z_offset

        if not room.is_inside(adjusted_position, include_borders=True):
            raise ValueError(
                f"Source '{source_name}' is outside the room at position "
                f"{adjusted_position.tolist()}. Move it inside RoomVolume in Blender."
            )

        room.add_source(adjusted_position)
        source_names.append(source_name)
    return source_names


def add_microphones_to_room(room, flat_receivers):
    if not flat_receivers:
        return

    z_offset = 0.0

    mic_positions = np.array(
        [receiver[RK.POSITION] for receiver in flat_receivers],
        dtype=float,
    ).T

    room.add_microphone_array(mic_positions)
