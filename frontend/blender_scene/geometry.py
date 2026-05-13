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
