"""
Blender bootstrap script for the Room Acoustics test frontend.

The file provides a minimal development entry-point for registering the
custom Room Acoustics UI inside Blender. It configures the project import
path, reloads selected frontend modules, registers properties, operators,
and panels, and activates the dedicated sidebar tab in the 3D View.

The actual application logic is implemented in:
- frontend.blender_scene: scene extraction and export support
- frontend.blender_ui: properties, operators, panels, and visualization
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import bpy
import sys
from pathlib import Path

from bpy.props import (
    PointerProperty,
)


# Project path bootstrap

PROJECT_ROOT = Path(bpy.path.abspath("//")).resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import frontend.blender_scene.geometry as geometry_module
import frontend.blender_scene.scene_export as scene_export_module


# Development module reload support

import importlib

importlib.reload(geometry_module)
importlib.reload(scene_export_module)


# UI imports

from frontend.blender_ui.properties import RA_TestProperties

from frontend.blender_ui.panels import (
    RA_PT_GridPanel,
    RA_PT_MaterialsPanel,
    RA_PT_SimulationPanel,
    RA_PT_ReceiversPanel,
    RA_PT_OutputPanel,
    RA_PT_RunStatusPanel,
    RA_PT_EnvironmentPanel,
)

from frontend.blender_ui.operators import (
    RA_OT_ApplyRoomVolumeDisplay,
    RA_OT_RunGridTest,
    RA_OT_CreateAudienceArea,
)

# ---------------------------------------------------------------------------
# Registration registry
# ---------------------------------------------------------------------------

classes = (
    RA_TestProperties,
    RA_OT_ApplyRoomVolumeDisplay,
    RA_OT_RunGridTest,
    RA_OT_CreateAudienceArea,
    RA_PT_GridPanel,
    RA_PT_MaterialsPanel,
    RA_PT_ReceiversPanel,
    RA_PT_SimulationPanel,
    RA_PT_OutputPanel,
    RA_PT_RunStatusPanel,
    RA_PT_EnvironmentPanel,
)

# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def activate_room_acoustics_tab():
    target_category = "Room Acoustics"

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

# ---------------------------------------------------------------------------
# Blender lifecycle
# ---------------------------------------------------------------------------

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ra_test_props = PointerProperty(type=RA_TestProperties)
    bpy.app.timers.register(activate_room_acoustics_tab, first_interval=0.1)


def unregister():
    del bpy.types.Scene.ra_test_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

# ---------------------------------------------------------------------------
# Manual execution entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass

    register()
    print("Room Acoustics Multi-Zone Test registered successfully.")