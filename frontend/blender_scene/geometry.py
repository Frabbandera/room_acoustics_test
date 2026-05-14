import math
import bpy

ROOM_DEF_MODE = "mode"
ROOM_DEF_SOURCE_OBJECT_NAME = "source_object_name"
ROOM_DEF_DISPLAY_LABEL = "display_label"
ROOM_DEF_FACES = "faces"
ROOM_DEF_Z_FLOOR = "z_floor"
ROOM_DEF_HEIGHT = "height"
ROOM_DEF_FLOOR_POLYGON_WORLD_2D = "floor_polygon_world_2d"

def get_obj(name, expected_type=None):
    obj = bpy.data.objects.get(name)
    if obj is None: raise RuntimeError(f"Object '{name}' not found.")
    return obj

def extract_room_faces_3d(room_obj):
    mesh = room_obj.data
    matrix_world = room_obj.matrix_world
    faces_data = []
    for poly in mesh.polygons:
        verts_3d = []
        for idx in poly.vertices:
            co = matrix_world @ mesh.vertices[idx].co
            verts_3d.append([float(co.x), float(co.y), float(co.z)])
        verts_3d.reverse()
        normal = matrix_world.to_3x3() @ poly.normal
        if normal.z < -0.8: surface_type = "floor"
        elif normal.z > 0.8: surface_type = "ceiling"
        else: surface_type = "wall"
        faces_data.append({"vertices": verts_3d, "surface_type": surface_type})
    return faces_data

def extract_room_definition():
    room_volume = get_obj("RoomVolume", "MESH")
    faces = extract_room_faces_3d(room_volume)
    all_z = [v[2] for f in faces for v in f["vertices"]]
    z_floor = min(all_z) if all_z else 0.0
    height = (max(all_z) - z_floor) if all_z else 0.0
    
    # Fake 2D per la UI
    floor_2d = [[0.0,0.0], [1.0,0.0], [0.0,1.0]] 

    return {
        ROOM_DEF_MODE: "3d_faces",
        ROOM_DEF_SOURCE_OBJECT_NAME: room_volume.name,
        ROOM_DEF_DISPLAY_LABEL: "RoomVolume",
        ROOM_DEF_FACES: faces,
        ROOM_DEF_Z_FLOOR: float(z_floor),
        ROOM_DEF_HEIGHT: float(height),
        ROOM_DEF_FLOOR_POLYGON_WORLD_2D: floor_2d
    }

def centered_axis_points(center, size, spacing):
    num_points = max(1, int(math.floor(size / spacing)))
    return [float(center + (i - (num_points - 1) / 2.0) * spacing) for i in range(num_points)]

def validate_not_rotated(obj, label):
    rx, ry, rz = obj.rotation_euler
    if abs(rx) > 1e-6 or abs(ry) > 1e-6 or abs(rz) > 1e-6:
        raise RuntimeError(f"For this test, '{label}' must not be rotated.")


def polygon_signed_area_2d(points):
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
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
    n = len(polygon)
    if include_borders:
        for i in range(n):
            a = polygon[i]
            b = polygon[(i + 1) % n]
            if point_on_segment_2d(point, a, b):
                return True
    j = n - 1
    for i in range(n):
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
    if (max(z_values) - min(z_values)) > 1e-5:
        raise RuntimeError(
            f"'{label}' must be planar and horizontal."
        )
    points_2d = [[float(v.x), float(v.y)] for v in verts_world]
    points_2d = ensure_anticlockwise(points_2d)
    z_mean = float(sum(z_values) / len(z_values))
    return points_2d, z_mean


def get_mapping_objs():
    map_objs = sorted(
        [obj for obj in bpy.data.objects
         if obj.name.startswith("MAP_") and obj.type == "MESH"],
        key=lambda obj: obj.name,
    )
    if map_objs:
        return map_objs
    raise RuntimeError(
        "No receiver areas found. Create at least one mesh object named 'MAP_*'."
    )
