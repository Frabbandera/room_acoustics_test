"""
Scene-state helpers for the Room Acoustics frontend.

The module provides small query functions used by the Blender panels to
inspect the current scene and expose a simplified UI-ready state.

This file contains no simulation logic. Its purpose is to keep scene
inspection centralized, readable, and consistent across the frontend.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import bpy

from frontend.blender_scene.geometry import (
    ROOM_DEF_DISPLAY_LABEL,
    ROOM_DEF_HEIGHT,
    ROOM_DEF_MODE,
    ROOM_DEF_SOURCE_OBJECT_NAME,
    ROOM_DEF_Z_FLOOR,
    extract_room_definition,
)

# ---------------------------------------------------------------------------
# Object query helpers
# ---------------------------------------------------------------------------

def _get_prefixed_object_names(prefix, *, object_type=None):
    names = []

    for obj in bpy.data.objects:
        if not obj.name.startswith(prefix):
            continue
        if object_type is not None and obj.type != object_type:
            continue
        names.append(obj.name)

    return sorted(names)

# ---------------------------------------------------------------------------
# Scene-state query functions
# ---------------------------------------------------------------------------

def get_valid_receiver_area_names():
    return _get_prefixed_object_names("MAP_", object_type="MESH")


def get_valid_source_names():
    return _get_prefixed_object_names("SRC_")


def get_room_ui_status():
    room_volume = bpy.data.objects.get("RoomVolume")

    status = {
        "room_volume_present": room_volume is not None,
        "ok": False,
        "mode": "",
        "source_object_name": "",
        "display_label": "",
        "height": 0.0,
        "z_floor": 0.0,
        "error": "",
    }

    try:
        room_def = extract_room_definition()

        status["ok"] = True
        status["mode"] = room_def[ROOM_DEF_MODE]
        status["source_object_name"] = room_def[ROOM_DEF_SOURCE_OBJECT_NAME]
        status["display_label"] = room_def[ROOM_DEF_DISPLAY_LABEL]
        status["height"] = float(room_def[ROOM_DEF_HEIGHT])
        status["z_floor"] = float(room_def[ROOM_DEF_Z_FLOOR])

    except Exception as e:
        status["error"] = str(e)

    return status