"""
Blender panels for the Room Acoustics frontend.

The module defines the sidebar panels used to edit scene settings,
configure simulations, and inspect run results inside Blender.

This file contains UI layout logic for the Room Acoustics workspace.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import bpy
from bpy.types import Panel

from frontend.blender_ui.scene_state import (
    get_room_ui_status,
    get_valid_source_names,
    get_valid_receiver_area_names,
)

from frontend.blender_ui.helpers import (
    get_engine_ui_label,
    format_hybrid_max_order_warning,
    format_active_room_geometry_ui,
)

# ---------------------------------------------------------------------------
# Shared panel constants
# ---------------------------------------------------------------------------

ROOM_ACOUSTICS_CATEGORY = "Room Acoustics"
ROOT_PANEL_ID = "RA_PT_grid_panel"

# ---------------------------------------------------------------------------
# Root panel
# ---------------------------------------------------------------------------

class RA_PT_GridPanel(Panel):
    bl_label = "Room Acoustics"
    bl_idname = ROOT_PANEL_ID
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ra_test_props
        room_status = get_room_ui_status()

        root_box = layout.box()

        req_box = root_box.box()
        req_col = req_box.column(align=True)
        req_col.label(text="ROOM REQUIREMENTS")
        req_col.label(text="Required Object: RoomVolume")
        req_col.label(text="Scene Naming: SRC_* and MAP_*")
        req_col.label(text="Requirements: closed, non-rotated, clean vertical prism.")

        active_box = root_box.box()
        active_col = active_box.column(align=True)
        active_col.label(text="ACTIVE ROOM")

        if room_status["ok"]:
            detected_name = room_status["source_object_name"] or "RoomVolume"
            active_col.label(text=f"Detected Object: {detected_name}")
            active_col.label(
                text=f"Geometry: {format_active_room_geometry_ui(room_status)}"
            )
            active_col.label(text=f"Height: {room_status['height']:.2f} m")

            active_col.prop(props, "room_volume_display_mode", text="Viewport Display")
        else:
            row = active_col.row()
            row.alert = True
            row.label(text="RoomVolume is missing or invalid.")
            if room_status["error"]:
                active_col.label(text=room_status["error"])

# ---------------------------------------------------------------------------
# Child panels
# ---------------------------------------------------------------------------

class RA_PT_MaterialsPanel(Panel):
    bl_label = "Materials"
    bl_idname = "RA_PT_materials_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ra_test_props

        col = layout.column(align=True)
        col.prop(props, "floor_material")
        col.prop(props, "wall_material")
        col.prop(props, "ceiling_material")

class RA_PT_FurniturePanel(Panel):
    bl_label = "Furniture"
    bl_idname = "RA_PT_furniture_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        info_box = layout.box()
        info_col = info_box.column(align=True)
        info_col.label(text="ACOUSTIC OBJECTS")
        info_col.label(text="Add objects, position them,")
        info_col.label(text="then run simulation.")

        layout.operator("ra.add_sofa", icon="MESH_CUBE")
        layout.operator("ra.add_bookshelf", icon="MESH_CUBE")
        layout.operator("ra.add_window", icon="MESH_PLANE")

        # Show existing furniture objects
        furn_objs = [o for o in bpy.data.objects if o.get("acoustic_object")]
        if furn_objs:
            furn_box = layout.box()
            furn_col = furn_box.column(align=True)
            furn_col.label(text="PLACED OBJECTS")
            for obj in furn_objs:
                mat = obj.get("acoustic_material", "unknown")
                furn_col.label(text=f"{obj.name} [{mat}]")

class RA_PT_ReceiversPanel(Panel):
    bl_label = "Receivers"
    bl_idname = "RA_PT_receivers_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ra_test_props
        room_status = get_room_ui_status()

        # Audience area

        audience_box = layout.box()
        audience_col = audience_box.column(align=True)
        audience_col.label(text="AUDIENCE AREA")
        audience_col.prop(props, "audience_height")
        audience_col.operator("ra.create_audience_area", icon="PLAY")

        if room_status["ok"]:
            audience_col.label(
                text=f"MAP_Main will be derived from {room_status['display_label']}."
            )
        else:
            row = audience_col.row()
            row.alert = True
            row.label(text="Fix RoomVolume before creating MAP_Main.")

        valid_receiver_areas = get_valid_receiver_area_names()

        if valid_receiver_areas:
            if props.selected_receiver_area not in valid_receiver_areas:
                props.selected_receiver_area = valid_receiver_areas[0]
            audience_col.prop(props, "selected_receiver_area")
        else:
            row = audience_col.row()
            row.alert = True
            row.label(text="No valid receiver areas found.")
            audience_col.label(
                text="Create at least one mesh object named 'MAP_*'."
            )

        # Receiver grid

        grid_box = layout.box()
        grid_col = grid_box.column(align=True)
        grid_col.label(text="RECEIVER GRID")
        grid_col.prop(props, "grid_spacing")
        grid_col.prop(props, "max_receivers")

        # Source display

        source_box = layout.box()
        source_col = source_box.column(align=True)
        source_col.label(text="SOURCE DISPLAY")

        valid_sources = get_valid_source_names()

        if valid_sources:
            if len(valid_sources) == 1:
                remaining_source = valid_sources[0]
                source_col.prop(props, "display_mode_single_only")
                source_col.label(text=f"Source: {remaining_source}")
            else:
                if props.selected_display_source not in valid_sources:
                    props.selected_display_source = valid_sources[0]

                source_col.prop(props, "display_mode")

                if props.display_mode == "single":
                    source_col.prop(props, "selected_display_source")
        else:
            row = source_col.row()
            row.alert = True
            row.label(text="No valid sources found.")
            source_col.label(text="Create at least one object named 'SRC_*'.")


class RA_PT_SimulationPanel(Panel):
    bl_label = "Simulation"
    bl_idname = "RA_PT_simulation_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ra_test_props

        engine_box = layout.box()
        engine_col = engine_box.column(align=True)
        engine_col.label(text="SIMULATION ENGINE")
        engine_col.prop(props, "simulation_engine")
        engine_col.label(
            text=f"Selected engine: {get_engine_ui_label(props.simulation_engine)}"
        )
        engine_col.prop(props, "fs")
        engine_col.prop(props, "max_order")
        engine_col.separator()
        engine_col.label(text="SOURCE POWER")
        engine_col.prop(props, "source_swl")

        warning_text = format_hybrid_max_order_warning(props)
        if warning_text:
            warn_box = engine_col.box()
            warn_col = warn_box.column(align=True)
            warn_col.alert = True
            warn_col.label(text=warning_text)

        engine_col.prop(props, "air_absorption")

        if props.simulation_engine == "HYBRID_RT":
            rt_box = layout.box()
            rt_col = rt_box.column(align=True)
            rt_col.label(text="RT PARAMETERS")
            rt_col.prop(props, "rt_n_rays")
            rt_col.prop(props, "rt_receiver_radius")
            rt_col.prop(props, "rt_hist_bin_size")
            rt_col.prop(props, "rt_energy_thres")
            rt_col.prop(props, "rt_time_thres")

            seed_box = layout.box()
            seed_col = seed_box.column(align=True)
            seed_col.label(text="RANDOMNESS")
            seed_col.prop(props, "use_fixed_random_seed")
            if props.use_fixed_random_seed:
                seed_col.prop(props, "random_seed")


class RA_PT_OutputPanel(Panel):
    bl_label = "Output"
    bl_idname = "RA_PT_output_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ra_test_props

        display_box = layout.box()
        display_col = display_box.column(align=True)
        display_col.label(text="DISPLAY STYLE")

        display_col.prop(props, "create_markers")
        if props.create_markers:
            display_col.prop(props, "marker_size")

        display_col.prop(props, "create_heatmap")
        if props.create_heatmap:
            display_col.prop(props, "heatmap_offset")

        quantity_box = layout.box()
        quantity_col = quantity_box.column(align=True)
        quantity_col.label(text="DISPLAYED QUANTITY")
        quantity_col.prop(props, "selected_band")
        quantity_col.prop(props, "selected_metric")
      
        layout.separator()
        layout.operator("ra.run_grid_test", icon="PLAY")

        if props.simulation_progress > 0 and props.simulation_progress < 100:
            progress_box = layout.box()
            progress_col = progress_box.column(align=True)
            progress_col.label(text=f"Progress: {props.simulation_progress}%")
            progress_col.prop(props, "simulation_progress", slider=True, text="")
            if props.simulation_status:
                progress_col.label(text=props.simulation_status)    

        try:
            from frontend.blender_ui.operators import RA_OT_RedisplayResults
            try:
                bpy.utils.register_class(RA_OT_RedisplayResults)
            except Exception:
                pass
            layout.operator("ra.redisplay_results", icon="FILE_REFRESH")
        except Exception as e:
            layout.label(text=f"Redisplay unavailable: {str(e)[:30]}")

class RA_PT_RunStatusPanel(Panel):
    bl_label = "Run Status"
    bl_idname = "RA_PT_run_status_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ra_test_props

        root_box = layout.box()

        summary_box = root_box.box()
        summary_col = summary_box.column(align=True)
        summary_col.label(text="RUN SUMMARY")

        if props.last_result:
            summary_col.label(text=f"Result: {props.last_result}")
        else:
            summary_col.label(text="Result: No run executed yet.")

        if props.last_engine_status:
            summary_col.label(text=f"Engine: {props.last_engine_status}")

        if props.last_runtime_note:
            note_box = summary_col.box()
            note_row = note_box.row()
            note_row.alert = True
            note_row.label(text=props.last_runtime_note)

        details_box = root_box.box()
        details_col = details_box.column(align=True)
        details_col.label(text="EXECUTION DETAILS")

        if props.last_context:
            details_col.label(text=f"Context: {props.last_context}")
        else:
            details_col.label(text="Context: N/A")

        if props.last_random_seed_note:
            details_col.label(text=props.last_random_seed_note)
        else:
            details_col.label(text="Random seed: N/A")


class RA_PT_EnvironmentPanel(Panel):
    bl_label = "Environment"
    bl_idname = "RA_PT_environment_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ra_test_props

        col = layout.column(align=True)
        col.prop(props, "project_dir")
        col.prop(props, "conda_python")

class RA_PT_FurniturePanel(Panel):
    bl_label = "Furniture"
    bl_idname = "RA_PT_furniture_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = ROOM_ACOUSTICS_CATEGORY
    bl_parent_id = ROOT_PANEL_ID
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout

        info_box = layout.box()
        info_col = info_box.column(align=True)
        info_col.label(text="ACOUSTIC OBJECTS")
        info_col.label(text="Add objects, position them,")
        info_col.label(text="then run simulation.")

        layout.operator("ra.add_sofa", icon="MESH_CUBE")
        layout.operator("ra.add_bookshelf", icon="MESH_CUBE")
        layout.operator("ra.add_window", icon="MESH_PLANE")

        # Show existing furniture objects
        furn_objs = [o for o in bpy.data.objects if o.get("acoustic_object")]
        if furn_objs:
            furn_box = layout.box()
            furn_col = furn_box.column(align=True)
            furn_col.label(text="PLACED OBJECTS")
            for obj in furn_objs:
                mat = obj.get("acoustic_material", "unknown")
                furn_col.label(text=f"{obj.name} [{mat}]")
