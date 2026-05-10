"""
Geometry helpers for the Room Acoustics frontend.

The module validates the RoomVolume mesh and extracts the simplified
room definition used by the Blender UI and scene export layer.

This file contains geometry validation and boundary extraction helpers
that support arbitrary non-convex and triangulated prismatic shapes.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import math

import bmesh
import bpy

# ---------------------------------------------------------------------------
# Room-definition keys
# ---------------------------------------------------------------------------

ROOM_DEF_MODE = "mode"
ROOM_DEF_SOURCE_OBJECT_NAME = "source_object_name"
ROOM_DEF_DISPLAY_LABEL = "display_label"
ROOM_DEF_FLOOR_POLYGON_WORLD_2D = "floor_polygon_world_2d"
ROOM_DEF_Z_FLOOR = "z_floor"
ROOM_DEF_HEIGHT = "height"

# ---------------------------------------------------------------------------
# Geometry constants
# ---------------------------------------------------------------------------

_GEOM_TOL = 1e-5

# ---------------------------------------------------------------------------
# Public object-access helpers
# ---------------------------------------------------------------------------

def get_obj(name, expected_type=None):
    obj = bpy.data.objects.get(name)

    if obj is None:
        raise RuntimeError(f"Object '{name}' not found.")

    if expected_type is not None and obj.type != expected_type:
        raise RuntimeError(
            f"Object '{name}' was found, but it has type '{obj.type}' "
            f"instead of '{expected_type}'."
        )

    return obj


def get_mapping_objs():
    map_objs = sorted(
        [
            obj
            for obj in bpy.data.objects
            if obj.name.startswith("MAP_") and obj.type == "MESH"
        ],
        key=lambda obj: obj.name,
    )

    if map_objs:
        return map_objs

    raise RuntimeError(
        "No receiver areas found. Create at least one mesh object named 'MAP_*'."
    )

# ---------------------------------------------------------------------------
# 2D polygon helpers
# ---------------------------------------------------------------------------

def validate_not_rotated(obj, label):
    rx, ry, rz = obj.rotation_euler

    if abs(rx) > 1e-6 or abs(ry) > 1e-6 or abs(rz) > 1e-6:
        raise RuntimeError(f"For this test, '{label}' must not be rotated.")


def polygon_signed_area_2d(points):
    area = 0.0
    num_points = len(points)

    for i in range(num_points):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % num_points]
        area += x1 * y2 - x2 * y1

    return 0.5 * area


def ensure_anticlockwise(points):
    if polygon_signed_area_2d(points) < 0.0:
        return list(reversed(points))

    return points


def point_on_segment_2d(point, a, b, eps=1e-9):
    px, py = point
    ax, ay = a
    bx, by = b

    cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
    if abs(cross) > eps:
        return False

    dot = (px - ax) * (bx - ax) + (py - ay) * (by - ay)
    if dot < -eps:
        return False

    sq_len = (bx - ax) ** 2 + (by - ay) ** 2
    if dot - sq_len > eps:
        return False

    return True


def point_in_polygon_2d(point, polygon, include_borders=True):
    x, y = point
    inside = False
    num_points = len(polygon)

    if include_borders:
        for i in range(num_points):
            a = polygon[i]
            b = polygon[(i + 1) % num_points]
            if point_on_segment_2d(point, a, b):
                return True

    j = num_points - 1
    for i in range(num_points):
        xi, yi = polygon[i]
        xj, yj = polygon[j]

        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-12) + xi
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def _group_sorted_levels(values, tol=_GEOM_TOL):
    levels = []

    for value in sorted(float(x) for x in values):
        if not levels or abs(value - levels[-1]) > tol:
            levels.append(value)

    return levels

# ---------------------------------------------------------------------------
# Mesh boundary extraction helpers
# ---------------------------------------------------------------------------

def extract_horizontal_boundary_2d(mesh_obj, label, z_target=None, tol=_GEOM_TOL):
    """
    Extracts the continuous outer 2D boundary of horizontal faces on a given Z level.
    Supports non-convex and multi-face (e.g. triangulated) flat surfaces.
    """
    bm = bmesh.new()
    bm.from_mesh(mesh_obj.data)
    matrix_world = mesh_obj.matrix_world

    target_faces = []
    actual_z = z_target

    # 1. Gather faces that lie flat on the target Z level
    for f in bm.faces:
        z_vals = [(matrix_world @ v.co).z for v in f.verts]
        if max(z_vals) - min(z_vals) <= tol:
            z_mean = sum(z_vals) / len(z_vals)
            if actual_z is None:
                actual_z = z_mean
            if abs(z_mean - actual_z) <= tol:
                target_faces.append(f)

    if not target_faces:
        bm.free()
        raise RuntimeError(f"'{label}': No horizontal faces found.")

    # 2. Find perimeter edges (edges connected to exactly 1 face in the target set)
    boundary_edges = [
        e for e in bm.edges 
        if sum(1 for f in e.link_faces if f in target_faces) == 1
    ]

    if not boundary_edges:
        bm.free()
        raise RuntimeError(f"'{label}': Could not determine boundary.")

    # 3. Build vertex adjacency map from boundary edges
    adj = {}
    for e in boundary_edges:
        v1, v2 = e.verts
        adj.setdefault(v1, []).append(v2)
        adj.setdefault(v2, []).append(v1)

    for v, neighbors in adj.items():
        if len(neighbors) != 2:
            bm.free()
            raise RuntimeError(
                f"'{label}': The boundary is not a clean, simple loop. "
                "Ensure there are no holes, interior pillars, or self-intersecting geometry."
            )

    # 4. Walk the perimeter to extract the ordered vertices
    start_v = boundary_edges[0].verts[0]
    current_v = start_v
    prev_v = None
    ordered_verts = []

    while True:
        ordered_verts.append(current_v)
        neighbors = adj[current_v]
        next_v = neighbors[0] if neighbors[0] != prev_v else neighbors[1]

        if next_v == start_v:
            break
        prev_v = current_v
        current_v = next_v

    points_2d = [
        [float((matrix_world @ v.co).x), float((matrix_world @ v.co).y)] 
        for v in ordered_verts
    ]
    bm.free()

    # 5. Clean up duplicate or near-duplicate coordinates
    cleaned_points = []
    for p in points_2d:
        if not cleaned_points or math.hypot(p[0] - cleaned_points[-1][0], p[1] - cleaned_points[-1][1]) > tol:
            cleaned_points.append(p)
    if len(cleaned_points) > 1 and math.hypot(cleaned_points[-1][0] - cleaned_points[0][0], cleaned_points[-1][1] - cleaned_points[0][1]) <= tol:
        cleaned_points.pop()

    # 6. Remove consecutive collinear points to simplify the array for Pyroomacoustics
    final_points = []
    num = len(cleaned_points)
    if num >= 3:
        for i in range(num):
            p_prev = cleaned_points[i - 1]
            p_curr = cleaned_points[i]
            p_next = cleaned_points[(i + 1) % num]
            
            # Cross product check for collinearity
            cross = (p_curr[0] - p_prev[0]) * (p_next[1] - p_curr[1]) - (p_curr[1] - p_prev[1]) * (p_next[0] - p_curr[0])
            if abs(cross) > 1e-7:
                final_points.append(p_curr)
    else:
        final_points = cleaned_points

    if len(final_points) < 3:
        raise RuntimeError(f"'{label}': Boundary does not define a valid 2D polygon.")

    # 7. Ensure valid orientation
    final_points = ensure_anticlockwise(final_points)

    return final_points, float(actual_z)


def get_single_face_polygon_world_2d(mesh_obj, label):
    """
    Kept for backwards compatibility with the export scripts, 
    but it now extracts the boundary even if the mesh has multiple faces.
    """
    points_2d, z_mean = extract_horizontal_boundary_2d(mesh_obj, label)
    return points_2d, z_mean

# ---------------------------------------------------------------------------
# Room validation and extraction
# ---------------------------------------------------------------------------

def validate_room_volume_vertical_prism(room_obj):
    if room_obj.type != "MESH":
        raise RuntimeError("The object 'RoomVolume' must be a mesh.")

    validate_not_rotated(room_obj, "RoomVolume")

    mesh = room_obj.data
    if len(mesh.vertices) < 6:
        raise RuntimeError(
            "'RoomVolume' does not look like a valid prism: "
            "at least 6 vertices are required."
        )

    bm = bmesh.new()
    bm.from_mesh(mesh)

    try:
        if len(bm.verts) == 0 or len(bm.edges) == 0 or len(bm.faces) == 0:
            raise RuntimeError("'RoomVolume' must be a valid non-empty 3D mesh.")

        if any(not edge.is_manifold for edge in bm.edges):
            raise RuntimeError(
                "'RoomVolume' must be a closed manifold mesh. "
                "Check for missing faces or open edges."
            )

        if any(len(vert.link_edges) == 0 for vert in bm.verts):
            raise RuntimeError(
                "'RoomVolume' contains isolated vertices. "
                "Remove any unused or dirty geometry."
            )
    finally:
        bm.free()

    verts_world = [room_obj.matrix_world @ vert.co for vert in mesh.vertices]
    z_levels = _group_sorted_levels([float(v.z) for v in verts_world])

    if len(z_levels) != 2:
        raise RuntimeError(
            "'RoomVolume' must have exactly 2 distinct Z levels "
            "(horizontal floor and ceiling)."
        )

    z_floor, z_ceil = z_levels
    height = float(z_ceil - z_floor)

    if height <= _GEOM_TOL:
        raise RuntimeError(
            "'RoomVolume' has invalid height: the distance between floor and "
            "ceiling must be > 0."
        )

    # Automatically handle non-convexity, multiple floor faces, and triangulated surfaces
    floor_polygon_world_2d, _ = extract_horizontal_boundary_2d(
        room_obj, 
        "The floor footprint of 'RoomVolume'", 
        z_target=z_floor
    )

    return {
        "floor_polygon_world_2d": floor_polygon_world_2d,
        "z_floor": float(z_floor),
        "height": float(height),
    }


def extract_room_definition_from_room_volume(room_obj):
    prism = validate_room_volume_vertical_prism(room_obj)

    return {
        ROOM_DEF_MODE: "room_volume_prism",
        ROOM_DEF_SOURCE_OBJECT_NAME: room_obj.name,
        ROOM_DEF_DISPLAY_LABEL: "RoomVolume",
        ROOM_DEF_FLOOR_POLYGON_WORLD_2D: prism["floor_polygon_world_2d"],
        ROOM_DEF_Z_FLOOR: prism["z_floor"],
        ROOM_DEF_HEIGHT: prism["height"],
    }


def extract_room_definition():
    room_volume = bpy.data.objects.get("RoomVolume")

    if room_volume is None:
        raise RuntimeError(
            "No valid room source found. Create a mesh object named 'RoomVolume'."
        )

    return extract_room_definition_from_room_volume(room_volume)

# ---------------------------------------------------------------------------
# Grid helper
# ---------------------------------------------------------------------------

def centered_axis_points(center, size, spacing):
    if spacing <= 0:
        raise RuntimeError("Grid spacing must be > 0.")

    num_points = max(1, int(math.floor(size / spacing)))
    coords = []

    for i in range(num_points):
        coord = center + (i - (num_points - 1) / 2.0) * spacing
        coords.append(float(coord))

    return coords
