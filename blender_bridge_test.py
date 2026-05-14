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

if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()

    # Force register RedisplayResults from fresh module
    from frontend.blender_ui import operators as _o
    import importlib
    importlib.reload(_o)
    try:
        bpy.utils.register_class(_o.RA_OT_RedisplayResults)
    except Exception:
        pass

    print("Room Acoustics registered successfully.")
