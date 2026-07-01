"""
Blender bootstrap script for the Room Acoustics test frontend.
"""

import bpy
import sys
import importlib
from pathlib import Path
from bpy.props import PointerProperty

# Project path bootstrap
PROJECT_ROOT = Path(bpy.path.abspath("//")).resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Module imports
import frontend.blender_scene.geometry as geometry_module
import frontend.blender_scene.scene_export as scene_export_module
import frontend.blender_ui.properties as properties_module
import frontend.blender_ui.operators as operators_module
import frontend.blender_ui.panels as panels_module

# Force reload all modules
importlib.reload(geometry_module)
importlib.reload(scene_export_module)
importlib.reload(properties_module)
importlib.reload(operators_module)
importlib.reload(panels_module)

# Import classes from freshly reloaded modules
RA_TestProperties = properties_module.RA_TestProperties

RA_OT_ApplyRoomVolumeDisplay = operators_module.RA_OT_ApplyRoomVolumeDisplay
RA_OT_RunGridTest = operators_module.RA_OT_RunGridTest
RA_OT_CreateAudienceArea = operators_module.RA_OT_CreateAudienceArea
RA_OT_RedisplayResults = operators_module.RA_OT_RedisplayResults

RA_PT_GridPanel = panels_module.RA_PT_GridPanel
RA_PT_MaterialsPanel = panels_module.RA_PT_MaterialsPanel
RA_PT_SimulationPanel = panels_module.RA_PT_SimulationPanel
RA_PT_ReceiversPanel = panels_module.RA_PT_ReceiversPanel
RA_PT_OutputPanel = panels_module.RA_PT_OutputPanel
RA_PT_RunStatusPanel = panels_module.RA_PT_RunStatusPanel
RA_PT_EnvironmentPanel = panels_module.RA_PT_EnvironmentPanel

# Registration registry
classes = (
    RA_TestProperties,
    RA_OT_ApplyRoomVolumeDisplay,
    RA_OT_RunGridTest,
    RA_OT_CreateAudienceArea,
    RA_OT_RedisplayResults,
    RA_PT_GridPanel,
    RA_PT_MaterialsPanel,
    RA_PT_ReceiversPanel,
    RA_PT_SimulationPanel,
    RA_PT_OutputPanel,
    RA_PT_RunStatusPanel,
    RA_PT_EnvironmentPanel,
)

def activate_room_acoustics_tab():
    target_category = "Room Acoustics"

    # Force register RedisplayResults after everything else is loaded
    try:
        from frontend.blender_ui.operators import RA_OT_RedisplayResults
        try:
            bpy.utils.register_class(RA_OT_RedisplayResults)
        except Exception:
            pass
    except Exception:
        pass

    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type != 'UI':
                    continue
                try:
                    if region.width == 1:
                        with bpy.context.temp_override(window=window, area=area, region=region):
                            bpy.ops.wm.context_toggle(data_path='space_data.show_region_ui')
                    region.active_panel_category = target_category
                    region.tag_redraw()
                except Exception:
                    pass
    return None

def register():
    from frontend.blender_ui import operators as _o
    import importlib
    importlib.reload(_o)
    _fresh_redisplay = _o.RA_OT_RedisplayResults

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass

    try:
        bpy.utils.register_class(_fresh_redisplay)
    except Exception:
        pass

    bpy.types.Scene.ra_test_props = PointerProperty(type=RA_TestProperties)
    bpy.app.timers.register(activate_room_acoustics_tab, first_interval=0.1)

def unregister():
    try:
        del bpy.types.Scene.ra_test_props
    except Exception:
        pass
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

def setup_default_objects():
    """Create SRC_1 and MAP_Main if they don't exist, as standalone objects."""

    # Create SRC_1 if missing
    if bpy.data.objects.get("SRC_1") is None:
        src = bpy.data.objects.new("SRC_1", None)
        src.empty_display_type = "SPHERE"
        src.empty_display_size = 0.2
        src.location = (0.0, 0.0, 1.5)
        src.parent = None
        bpy.context.scene.collection.objects.link(src)
        print("[RA] SRC_1 created at (0, 0, 1.5)")

    # Create MAP_Main if missing
    if bpy.data.objects.get("MAP_Main") is None:
        verts = [(-1.5, -1.0, 1.2), (1.5, -1.0, 1.2),
                 (1.5,  1.0, 1.2), (-1.5,  1.0, 1.2)]
        face = [[0, 1, 2, 3]]
        mesh = bpy.data.meshes.new("MAP_Main")
        mesh.from_pydata(verts, [], face)
        mesh.update()
        map_obj = bpy.data.objects.new("MAP_Main", mesh)
        map_obj.parent = None
        bpy.context.scene.collection.objects.link(map_obj)
        print("[RA] MAP_Main created at z=1.2m")

    # Make sure neither is parented to anything
    for name in ["SRC_1", "MAP_Main"]:
        obj = bpy.data.objects.get(name)
        if obj and obj.parent is not None:
            obj.parent = None
            print(f"[RA] {name} unparented")


if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()
    setup_default_objects()
    print("Room Acoustics registered successfully.")
