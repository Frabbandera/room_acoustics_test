"""
Blender operators for the Room Acoustics frontend.

The module defines the operators used to create receiver geometry and to run
the simulation workflow from Blender.

This file contains UI-triggered application logic that connects scene export,
backend execution, and result visualization.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import json
import subprocess
from pathlib import Path

import bpy
from bpy.types import Operator

import shared.result_keys as RK

from frontend.blender_scene.geometry import (
    ROOM_DEF_DISPLAY_LABEL,
    ROOM_DEF_FLOOR_POLYGON_WORLD_2D,
    ROOM_DEF_HEIGHT,
    ROOM_DEF_Z_FLOOR,
    extract_room_definition,
)
from frontend.blender_scene.scene_export import build_scene_dict

from frontend.blender_ui.helpers import (
    get_engine_ui_label,
    format_runtime_note_ui,
    format_random_seed_ui,
)
from frontend.blender_ui.visualization import (
    get_selected_area_result,
    get_display_summary,
    create_result_markers,
    create_heatmap_object,
    apply_room_volume_display_mode,
)

# ---------------------------------------------------------------------------
# RoomVolume display operator
# ---------------------------------------------------------------------------

class RA_OT_ApplyRoomVolumeDisplay(Operator):
    bl_idname = "ra.apply_room_volume_display"
    bl_label = "Apply Room View"
    bl_description = "Apply the selected RoomVolume viewport display mode"

    def execute(self, context):
        success = apply_room_volume_display_mode(context)

        if not success:
            self.report({'WARNING'}, "RoomVolume not found.")
            return {'CANCELLED'}

        self.report({'INFO'}, "RoomVolume display updated.")
        return {'FINISHED'}

# ---------------------------------------------------------------------------
# Audience-area operator
# ---------------------------------------------------------------------------

class RA_OT_CreateAudienceArea(Operator):
    bl_idname = "ra.create_audience_area"
    bl_label = "Create Audience Area"
    bl_description = "Create or update MAP_Main from the active room geometry"

    def execute(self, context):
        props = context.scene.ra_test_props

        try:
            room_def = extract_room_definition()

            room_label = room_def[ROOM_DEF_DISPLAY_LABEL]
            floor_polygon_world_2d = room_def[ROOM_DEF_FLOOR_POLYGON_WORLD_2D]
            z_floor = float(room_def[ROOM_DEF_Z_FLOOR])
            room_height = float(room_def[ROOM_DEF_HEIGHT])

            audience_height = float(props.audience_height)

            if audience_height < 0.0:
                raise RuntimeError("Audience Height must be >= 0.")

            if audience_height > room_height:
                raise RuntimeError(
                    f"Audience Height ({audience_height:.3f} m) exceeds the room height "
                    f"({room_height:.3f} m) defined by {room_label}."
                )

            map_z = z_floor + audience_height
            map_name = "MAP_Main"

            existing = bpy.data.objects.get(map_name)
            if existing is not None:
                if existing.type != "MESH":
                    raise RuntimeError(
                        f"An object named '{map_name}' already exists, but it is not a mesh."
                    )

                old_mesh = existing.data
                bpy.data.objects.remove(existing, do_unlink=True)

                if old_mesh is not None and old_mesh.users == 0:
                    bpy.data.meshes.remove(old_mesh)

            verts = [
                (float(x), float(y), float(map_z))
                for x, y in floor_polygon_world_2d
            ]
            face = [list(range(len(verts)))]

            mesh = bpy.data.meshes.new(map_name)
            mesh.from_pydata(verts, [], face)
            mesh.update(calc_edges=True)

            map_obj = bpy.data.objects.new(map_name, mesh)
            context.scene.collection.objects.link(map_obj)

            map_obj.location = (0.0, 0.0, 0.0)
            map_obj.rotation_euler = (0.0, 0.0, 0.0)
            map_obj.scale = (1.0, 1.0, 1.0)

            self.report(
                {'INFO'},
                f"'{map_name}' created from {room_label} at elevation {map_z:.2f} m.",
            )
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

# ---------------------------------------------------------------------------
# Simulation operator
# ---------------------------------------------------------------------------

class RA_OT_RunGridTest(Operator):
    bl_idname = "ra.run_grid_test"
    bl_label = "Run Acoustic Test"

    def execute(self, context):
        props = context.scene.ra_test_props

        try:
            props.simulation_progress = 5
            props.simulation_status = "Exporting scene..."
            for area in bpy.context.screen.areas:
                area.tag_redraw()

            # Resolve project paths.

            project_dir = Path(bpy.path.abspath(props.project_dir))
            if not project_dir.exists():
                raise RuntimeError("Invalid Project Dir.")

            conda_python = Path(bpy.path.abspath(props.conda_python))
            if not conda_python.exists():
                raise RuntimeError("Invalid Conda Python.")

            backend_script = project_dir / "backend" / "run_simulation.py"
            if not backend_script.exists():
                raise RuntimeError(f"Backend script not found: {backend_script}")

            exchange_dir = project_dir / "exchange"
            exchange_dir.mkdir(parents=True, exist_ok=True)

            scene_path = exchange_dir / "scene.json"
            results_path = exchange_dir / "results.json"

            # Export the current Blender scene.

            scene_dict = build_scene_dict(context)

            with scene_path.open("w", encoding="utf-8") as f:
                json.dump(scene_dict, f, indent=2)

            # Run the backend simulation.

            # Run the backend simulation with progress updates.

            props.simulation_progress = 25
            props.simulation_status = "Running simulation..."
            for area in bpy.context.screen.areas:
                area.tag_redraw()   

            cmd = [
                str(conda_python),
                str(backend_script),
                "--scene",
                str(scene_path),
                "--out",
                str(results_path),
            ]

            props.simulation_progress = 25
            props.simulation_status = "Running simulation..."
            for area in bpy.context.screen.areas:
                area.tag_redraw()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            props.simulation_progress = 75
            props.simulation_status = "Computing metrics..."
            for area in bpy.context.screen.areas:
                area.tag_redraw()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    "Backend error.\n\nSTDOUT:\n"
                    + result.stdout
                    + "\n\nSTDERR:\n"
                    + result.stderr
                )

            if not results_path.exists():
                raise RuntimeError("results.json not found after execution.")

            # Load backend results.

            with results_path.open("r", encoding="utf-8") as f:
                results = json.load(f)
                props.last_results_path = str(results_path)

            simulation_info = results.get(RK.SIMULATION, {})
            requested_engine = simulation_info.get(
                RK.REQUESTED_ENGINE,
                props.simulation_engine,
            )
            executed_engine = simulation_info.get(
                RK.EXECUTED_ENGINE,
                requested_engine,
            )
            warning_message = simulation_info.get(RK.WARNING_MESSAGE)

            requested_engine_label = get_engine_ui_label(requested_engine)
            executed_engine_label = get_engine_ui_label(executed_engine)

            fallback_active = requested_engine != executed_engine

            # Update run-status UI fields.

            if fallback_active:
                props.last_engine_status = (
                    f"Engine req={requested_engine_label} | "
                    f"exec={executed_engine_label} | fallback active"
                )
            elif warning_message:
                props.last_engine_status = (
                    f"Engine req={requested_engine_label} | "
                    f"exec={executed_engine_label} | note present"
                )
            else:
                props.last_engine_status = (
                    f"Engine req={requested_engine_label} | "
                    f"exec={executed_engine_label}"
                )

            props.last_runtime_note = format_runtime_note_ui(
                requested_engine,
                executed_engine,
                warning_message,
            )
            props.last_random_seed_note = format_random_seed_ui(simulation_info)

            # Resolve display selection.

            metric_key = props.selected_metric
            display_mode = props.display_mode
            selected_source = props.selected_display_source
            selected_area_name = props.selected_receiver_area

            if display_mode == "single":
                if not selected_source or selected_source not in results[RK.SOURCE_NAMES]:
                    selected_source = results[RK.SOURCE_NAMES][0]
            else:
                selected_source = ""

            available_area_names = [
                area[RK.NAME]
                for area in results[RK.RECEIVER_AREAS]
            ]
            if not selected_area_name or selected_area_name not in available_area_names:
                selected_area_name = available_area_names[0]

            area_results = get_selected_area_result(results, selected_area_name)

            # Build summary strings for the UI.

            metric_summary = get_display_summary(
                area_results,
                metric_key,
                display_mode,
                selected_source,
            )
            metric_label = metric_summary[RK.LABEL]
            metric_unit = metric_summary[RK.UNIT]
            band_label = results[RK.BAND][RK.LABEL]

            unit_text = f" {metric_unit}" if metric_unit else ""

            if display_mode == "single":
                display_label = selected_source
            else:
                display_label = "Source Average"

            props.last_result = (
                f"{metric_label} @ {band_label} | "
                f"{display_label} | "
                f"Area={selected_area_name} | "
                f"N={area_results[RK.SUMMARY][RK.NUM_RECEIVERS]} | "
                f"min={metric_summary[RK.MIN_VALUE]:.2f}{unit_text} | "
                f"max={metric_summary[RK.MAX_VALUE]:.2f}{unit_text} | "
                f"mean={metric_summary[RK.MEAN_VALUE]:.2f}{unit_text}"
            )

            mats = results[RK.MATERIALS]
            props.last_context = (
                f"Sources={results[RK.SUMMARY][RK.NUM_SOURCES]} | "
                f"Areas={results[RK.SUMMARY][RK.NUM_RECEIVER_AREAS]} | "
                f"Walls={mats[RK.WALLS][RK.LABEL]} | "
                f"Floor={mats[RK.FLOOR][RK.LABEL]} | "
                f"Ceiling={mats[RK.CEILING][RK.LABEL]}"
            )

            # Apply RoomVolume viewport display mode.

            apply_room_volume_display_mode(context)

            # Create optional scene visualization outputs.

            if props.create_markers:
                create_result_markers(
                    context,
                    area_results,
                    band_label,
                    metric_key,
                    display_mode,
                    selected_source,
                )

            if props.create_heatmap:
                create_heatmap_object(
                    context,
                    area_results,
                    band_label,
                    metric_key,
                    display_mode,
                    selected_source,
                )

            # Report final operator status.

            if fallback_active:
                self.report(
                    {'WARNING'},
                    f"HYBRID_RT failed: falling back to {executed_engine_label}.",
                )
            else:
                self.report(
                    {'INFO'},
                    f"Acoustic simulation completed with {executed_engine_label}.",
                )

            print(result.stdout)
            props.simulation_progress = 100
            props.simulation_status = "Complete!"
            for area in bpy.context.screen.areas:
                area.tag_redraw()
            return {'FINISHED'}

        except Exception as e:
            props.last_result = f"Error: {str(e)}"
            props.last_engine_status = ""
            props.last_runtime_note = ""
            props.last_random_seed_note = ""
            props.last_context = ""
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

class RA_OT_RedisplayResults(Operator):
    bl_idname = "ra.redisplay_results"
    bl_label = "Redisplay Results"
    bl_description = "Redraw markers and heatmap from last results without rerunning the simulation"

    def execute(self, context):
        props = context.scene.ra_test_props

        if not props.last_results_path:
            self.report({"ERROR"}, "No results found. Run the simulation first.")
            return {"CANCELLED"}

        results_path = Path(props.last_results_path)
        if not results_path.exists():
            self.report({"ERROR"}, "Results file not found. Run the simulation first.")
            return {"CANCELLED"}

        try:
            with results_path.open("r", encoding="utf-8") as f:
                results = json.load(f)

            metric_key = props.selected_metric
            display_mode = props.display_mode
            selected_source = props.selected_display_source
            selected_area_name = props.selected_receiver_area

            if display_mode == "single":
                if not selected_source or selected_source not in results[RK.SOURCE_NAMES]:
                    selected_source = results[RK.SOURCE_NAMES][0]
            else:
                selected_source = ""

            available_area_names = [
                area[RK.NAME]
                for area in results[RK.RECEIVER_AREAS]
            ]
            if not selected_area_name or selected_area_name not in available_area_names:
                selected_area_name = available_area_names[0]

            area_results = get_selected_area_result(results, selected_area_name)
            band_label = results[RK.BAND][RK.LABEL]

            if props.create_markers:
                create_result_markers(
                    context,
                    area_results,
                    band_label,
                    metric_key,
                    display_mode,
                    selected_source,
                )

            if props.create_heatmap:
                create_heatmap_object(
                    context,
                    area_results,
                    band_label,
                    metric_key,
                    display_mode,
                    selected_source,
                )

            self.report({"INFO"}, f"Redisplayed {metric_key} from last results.")
            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}


# ---------------------------------------------------------------------------
# Furniture operators
# ---------------------------------------------------------------------------

class RA_OT_AddSofa(Operator):
    bl_idname = "ra.add_sofa"
    bl_label = "Add Sofa"
    bl_description = "Add a sofa obstacle with high absorption (heavy curtain material)"

    def execute(self, context):
        try:
            # Create sofa mesh (simple box approximation)
            verts = [
                # Seat
                (-0.9, -0.4, 0.0), (0.9, -0.4, 0.0),
                (0.9,  0.4, 0.0),  (-0.9,  0.4, 0.0),
                (-0.9, -0.4, 0.45), (0.9, -0.4, 0.45),
                (0.9,  0.4, 0.45), (-0.9,  0.4, 0.45),
                # Backrest
                (-0.9, 0.25, 0.45), (0.9, 0.25, 0.45),
                (0.9,  0.40, 0.45), (-0.9, 0.40, 0.45),
                (-0.9, 0.25, 1.0),  (0.9, 0.25, 1.0),
                (0.9,  0.40, 1.0),  (-0.9, 0.40, 1.0),
            ]
            faces = [
                [0,1,2,3], [4,5,6,7], [0,1,5,4],
                [1,2,6,5], [2,3,7,6], [3,0,4,7],
                [8,9,10,11], [12,13,14,15], [8,9,13,12],
                [9,10,14,13], [10,11,15,14], [11,8,12,15],
            ]
            mesh = bpy.data.meshes.new("Sofa_Mesh")
            mesh.from_pydata(verts, [], faces)
            mesh.update()
            obj = bpy.data.objects.new("FURN_Sofa", mesh)
            obj.location = (0.0, 0.0, 0.0)
            obj.parent = None
            obj["acoustic_material"] = "heavy_curtain"
            obj["acoustic_object"] = True
            context.scene.collection.objects.link(obj)
            self.report({'INFO'}, "Sofa added — move it inside the room then run simulation")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}


class RA_OT_AddBookshelf(Operator):
    bl_idname = "ra.add_bookshelf"
    bl_label = "Add Bookshelf"
    bl_description = "Add a bookshelf with medium absorption and diffusion (wood material)"

    def execute(self, context):
        try:
            verts = [
                (-0.15, -1.0, 0.0), (0.15, -1.0, 0.0),
                (0.15,  1.0, 0.0),  (-0.15,  1.0, 0.0),
                (-0.15, -1.0, 2.0), (0.15, -1.0, 2.0),
                (0.15,  1.0, 2.0),  (-0.15,  1.0, 2.0),
            ]
            faces = [
                [0,1,2,3], [4,5,6,7], [0,1,5,4],
                [1,2,6,5], [2,3,7,6], [3,0,4,7],
            ]
            mesh = bpy.data.meshes.new("Bookshelf_Mesh")
            mesh.from_pydata(verts, [], faces)
            mesh.update()
            obj = bpy.data.objects.new("FURN_Bookshelf", mesh)
            obj.location = (0.0, 0.0, 0.0)
            obj.parent = None
            obj["acoustic_material"] = "wood"
            obj["acoustic_object"] = True
            context.scene.collection.objects.link(obj)
            self.report({'INFO'}, "Bookshelf added — move it inside the room then run simulation")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}


class RA_OT_AddWindow(Operator):
    bl_idname = "ra.add_window"
    bl_label = "Add Window"
    bl_description = "Add a window panel with low absorption (reflective plaster material)"

    def execute(self, context):
        try:
            verts = [
                (-0.02, -0.8, 0.0), (0.02, -0.8, 0.0),
                (0.02,  0.8, 0.0),  (-0.02,  0.8, 0.0),
                (-0.02, -0.8, 1.5), (0.02, -0.8, 1.5),
                (0.02,  0.8, 1.5),  (-0.02,  0.8, 1.5),
            ]
            faces = [
                [0,1,2,3], [4,5,6,7], [0,1,5,4],
                [1,2,6,5], [2,3,7,6], [3,0,4,7],
            ]
            mesh = bpy.data.meshes.new("Window_Mesh")
            mesh.from_pydata(verts, [], faces)
            mesh.update()
            obj = bpy.data.objects.new("FURN_Window", mesh)
            obj.location = (0.0, 0.0, 0.0)
            obj.parent = None
            obj["acoustic_material"] = "reflective_plaster"
            obj["acoustic_object"] = True
            context.scene.collection.objects.link(obj)
            self.report({'INFO'}, "Window added — move it to a wall then run simulation")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
