"""
Geometry helpers for the Room Acoustics frontend.

The module validates the RoomVolume mesh and extracts the simplified
room definition used by the Blender UI and scene export layer.

This file contains geometry validation and small geometric helper functions.
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


def get_single_face_polygon_world_2d(mesh_obj, label):
    mesh = mesh_obj.data

    if len(mesh.polygons) != 1:
        raise RuntimeError(
            f"For this stage, '{label}' must be a mesh with exactly one face."
        )

    poly = mesh.polygons[0]
    matrix_world = mesh_obj.matrix_world

    verts_world = [matrix_world @ mesh.vertices[idx].co for idx in poly.vertices]
    z_values = [float(v.z) for v in verts_world]

    if (max(z_values) - min(z_values)) > _GEOM_TOL:
        raise RuntimeError(
            f"'{label}' must be planar and horizontal "
            "(all vertices must share the same Z value)."
        )

    points_2d = [[float(v.x), float(v.y)] for v in verts_world]

    unique_points = {tuple(p) for p in points_2d}
    if len(unique_points) < 3:
        raise RuntimeError(f"'{label}' does not define a valid polygon.")

    points_2d = ensure_anticlockwise(points_2d)

    if abs(polygon_signed_area_2d(points_2d)) < 1e-9:
        raise RuntimeError(f"'{label}' has zero or near-zero area.")

    z_mean = float(sum(z_values) / len(z_values))
    return points_2d, z_mean

# ---------------------------------------------------------------------------
# Internal quantization and cleanup helpers
# ---------------------------------------------------------------------------

def _group_sorted_levels(values, tol=_GEOM_TOL):
    levels = []

    for value in sorted(float(x) for x in values):
        if not levels or abs(value - levels[-1]) > tol:
            levels.append(value)

    return levels


def _quantize_value(value, tol=_GEOM_TOL):
    return int(round(float(value) / tol))


def _quantize_xy_point(point, tol=_GEOM_TOL):
    return (
        _quantize_value(point[0], tol),
        _quantize_value(point[1], tol),
    )


def _unordered_edge_key_2d(a, b, tol=_GEOM_TOL):
    qa = _quantize_xy_point(a, tol)
    qb = _quantize_xy_point(b, tol)
    return tuple(sorted((qa, qb)))


def _collect_unique_xy_points(points_xy, tol=_GEOM_TOL):
    unique = {}

    for x, y in points_xy:
        key = _quantize_xy_point((x, y), tol)
        if key not in unique:
            unique[key] = [float(x), float(y)]

    return list(unique.values())


def _is_convex_polygon_2d(points_xy, tol=1e-9):
    num_points = len(points_xy)

    if num_points < 3:
        return False

    sign = 0

    for i in range(num_points):
        x1, y1 = points_xy[i]
        x2, y2 = points_xy[(i + 1) % num_points]
        x3, y3 = points_xy[(i + 2) % num_points]

        cross = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)

        if abs(cross) <= tol:
            continue

        current_sign = 1 if cross > 0.0 else -1

        if sign == 0:
            sign = current_sign
        elif current_sign != sign:
            return False

    return True

# ---------------------------------------------------------------------------
# Mesh face extraction helpers
# ---------------------------------------------------------------------------

def _face_world_vertices(mesh_obj, poly):
    matrix_world = mesh_obj.matrix_world
    mesh = mesh_obj.data
    return [matrix_world @ mesh.vertices[idx].co for idx in poly.vertices]


def _extract_horizontal_face_polygon_world_2d(mesh_obj, poly, label):
    verts_world = _face_world_vertices(mesh_obj, poly)
    z_values = [float(v.z) for v in verts_world]

    if (max(z_values) - min(z_values)) > _GEOM_TOL:
        raise RuntimeError(f"'{label}' must be horizontal.")

    points_2d = [[float(v.x), float(v.y)] for v in verts_world]
    unique_points = _collect_unique_xy_points(points_2d)

    if len(unique_points) < 3:
        raise RuntimeError(f"'{label}' does not define a valid polygon.")

    if len(unique_points) != len(points_2d):
        raise RuntimeError(
            f"'{label}' contains duplicate vertices or unclean geometry."
        )

    points_2d = ensure_anticlockwise(points_2d)

    if abs(polygon_signed_area_2d(points_2d)) < 1e-9:
        raise RuntimeError(f"'{label}' has zero or near-zero area.")

    return points_2d

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

    bottom_faces = []
    top_faces = []
    side_faces = []

    for poly in mesh.polygons:
        verts_poly = _face_world_vertices(room_obj, poly)
        z_values = [float(v.z) for v in verts_poly]

        if all(abs(z - z_floor) <= _GEOM_TOL for z in z_values):
            bottom_faces.append(poly)
        elif all(abs(z - z_ceil) <= _GEOM_TOL for z in z_values):
            top_faces.append(poly)
        else:
            side_faces.append(poly)
            for z in z_values:
                if abs(z - z_floor) > _GEOM_TOL and abs(z - z_ceil) > _GEOM_TOL:
                    raise RuntimeError(
                        "'RoomVolume' is not a valid vertical prism: "
                        "all vertices must lie only on the floor plane or the ceiling plane."
                    )

    if len(bottom_faces) != 1:
        raise RuntimeError(
            "For this stage, 'RoomVolume' must have exactly one floor face."
        )

    if len(top_faces) != 1:
        raise RuntimeError(
            "For this stage, 'RoomVolume' must have exactly one ceiling face."
        )

    floor_polygon_world_2d = _extract_horizontal_face_polygon_world_2d(
        room_obj,
        bottom_faces[0],
        "The floor face of 'RoomVolume'",
    )

    top_polygon_world_2d = _extract_horizontal_face_polygon_world_2d(
        room_obj,
        top_faces[0],
        "The ceiling face of 'RoomVolume'",
    )

    if len(floor_polygon_world_2d) != len(top_polygon_world_2d):
        raise RuntimeError(
            "'RoomVolume' is not a valid vertical prism: "
            "floor and ceiling must have the same number of vertices."
        )

    floor_keys = {_quantize_xy_point(point) for point in floor_polygon_world_2d}
    top_keys = {_quantize_xy_point(point) for point in top_polygon_world_2d}

    if floor_keys != top_keys:
        raise RuntimeError(
            "'RoomVolume' is not a valid vertical prism: "
            "the XY projection of the ceiling must match the floor."
        )

    if not _is_convex_polygon_2d(floor_polygon_world_2d):
        raise RuntimeError(
            "For this stage, the footprint of 'RoomVolume' must be a convex polygon."
        )

    expected_side_edges = {
        _unordered_edge_key_2d(
            floor_polygon_world_2d[i],
            floor_polygon_world_2d[(i + 1) % len(floor_polygon_world_2d)],
        )
        for i in range(len(floor_polygon_world_2d))
    }

    actual_side_edges = set()

    for poly in side_faces:
        verts_poly = _face_world_vertices(room_obj, poly)
        z_values = [float(v.z) for v in verts_poly]

        if not any(abs(z - z_floor) <= _GEOM_TOL for z in z_values):
            raise RuntimeError(
                "'RoomVolume' is not a valid vertical prism: "
                "each side wall must touch the floor."
            )

        if not any(abs(z - z_ceil) <= _GEOM_TOL for z in z_values):
            raise RuntimeError(
                "'RoomVolume' is not a valid vertical prism: "
                "each side wall must touch the ceiling."
            )

        unique_xy = _collect_unique_xy_points(
            [[float(v.x), float(v.y)] for v in verts_poly]
        )

        if len(unique_xy) != 2:
            raise RuntimeError(
                "For this stage, each side wall of 'RoomVolume' must be a clean "
                "vertical face connecting exactly one floor edge to the "
                "corresponding ceiling edge."
            )

        actual_side_edges.add(_unordered_edge_key_2d(unique_xy[0], unique_xy[1]))

    if actual_side_edges != expected_side_edges:
        raise RuntimeError(
            "'RoomVolume' is not a valid vertical prism: "
            "the side walls must match the edges of the footprint exactly."
        )

    if len(side_faces) != len(floor_polygon_world_2d):
        raise RuntimeError(
            "For this stage, 'RoomVolume' must have exactly one side wall for "
            "each footprint edge."
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