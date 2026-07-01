"""
Blender property definitions for the Room Acoustics frontend.

The module defines the custom Blender properties used to configure the
simulation workflow and store UI state across the Room Acoustics panels.

This file contains property declarations and enum helpers for the frontend.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import bpy

from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)

from bpy.types import PropertyGroup

from shared.catalogs import (
    build_band_enum_items,
    build_engine_enum_items,
    build_material_enum_items,
    build_metric_enum_items,
    get_ray_tracing_defaults,
)

# ---------------------------------------------------------------------------
# Static enum item caches
# ---------------------------------------------------------------------------

BAND_ITEMS = build_band_enum_items()
METRIC_ITEMS = build_metric_enum_items()
MATERIAL_ITEMS = build_material_enum_items()
ENGINE_ITEMS = build_engine_enum_items()
RT_DEFAULTS = get_ray_tracing_defaults()

ROOM_VOLUME_DISPLAY_ITEMS = [
    (
        "normal",
        "Normal",
        "Show RoomVolume as a regular viewport object",
    ),
    (
        "wire",
        "Wire",
        "Show RoomVolume as wireframe during result inspection",
    ),
    (
        "hide",
        "Hidden",
        "Hide RoomVolume in the viewport during result inspection",
    ),
]

DISPLAY_MODE_ITEMS = [
    (
        "average",
        "Source Average",
        "Average results across all valid sources",
    ),
    (
        "single",
        "Single Source",
        "Show results for one selected source",
    ),
]

DISPLAY_MODE_SINGLE_ONLY_ITEMS = [
    (
        "single",
        "Single Source",
        "Show results for the only available source",
    ),
]

# ---------------------------------------------------------------------------
# Dynamic enum helpers
# ---------------------------------------------------------------------------

def _on_room_volume_display_mode_changed(self, context):
    if context is None:
        return

    from frontend.blender_ui.visualization import apply_room_volume_display_mode

    apply_room_volume_display_mode(context)

def _get_prefixed_object_names(prefix, *, object_type=None):
    names = []

    for obj in bpy.data.objects:
        if not obj.name.startswith(prefix):
            continue
        if object_type is not None and obj.type != object_type:
            continue
        names.append(obj.name)

    return sorted(names)


def source_enum_items(self, context):
    names = _get_prefixed_object_names("SRC_")

    if names:
        return [
            (name, name, f"Show results for source {name}")
            for name in names
        ]

    return [
        (
            "__NONE__",
            "No valid SRC_* sources",
            "Create at least one source object named 'SRC_*'",
        )
    ]


def receiver_area_enum_items(self, context):
    names = _get_prefixed_object_names("MAP_", object_type="MESH")

    if names:
        return [
            (name, name, f"Show results for receiver area {name}")
            for name in names
        ]

    return [
        (
            "__NONE__",
            "No valid MAP_* receiver areas",
            "Create at least one mesh object named 'MAP_*'",
        )
    ]

# ---------------------------------------------------------------------------
# Property group
# ---------------------------------------------------------------------------

class RA_TestProperties(PropertyGroup):

    # Environment

    project_dir: StringProperty(
        name="Project Directory",
        subtype="DIR_PATH",
        default="",
    )

    conda_python: StringProperty(
        name="Python Executable",
        subtype="FILE_PATH",
        default="",
    )

    # Room and simulation

    audience_height: FloatProperty(
        name="Audience Height",
        default=1.20,
        min=0.1,
    )

    simulation_engine: EnumProperty(
        name="Simulation Mode",
        description="Select the requested simulation mode",
        items=ENGINE_ITEMS,
        default="ISM_ONLY",
    )

    fs: IntProperty(
        name="Fs",
        default=16000,
        min=1000,
    )

    max_order: IntProperty(
        name="Max Order",
        default=3,
        min=0,
        max=50,
    )

    air_absorption: BoolProperty(
        name="Air Absorption",
        default=True,
    )

    use_fixed_random_seed: BoolProperty(
        name="Fixed Seed",
        description="If enabled, the backend sets a deterministic random seed before the simulation",
        default=True,
    )

    random_seed: IntProperty(
        name="Random Seed",
        description="Seed used to make stochastic simulation branches reproducible",
        default=12345,
        min=0,
    )

    rt_n_rays: IntProperty(
        name="Rays Number",
        description="Number of rays used by the pyroomacoustics ray-tracing branch",
        default=RT_DEFAULTS["n_rays"],
        min=100,
        soft_max=200000,
    )

    rt_receiver_radius: FloatProperty(
        name="Receiver Radius (m)",
        description="Effective receiver radius for the ray-tracing branch",
        default=RT_DEFAULTS["receiver_radius"],
        min=0.01,
        soft_max=5.0,
    )

    rt_hist_bin_size: FloatProperty(
        name="Histogram Bin Size (s)",
        description="Time step of the ray-tracing energy histogram",
        default=RT_DEFAULTS["hist_bin_size"],
        min=0.0001,
        soft_max=0.050,
        precision=4,
    )

    rt_energy_thres: FloatProperty(
        name="Energy Threshold",
        description="Energy threshold used to stop the ray-tracing branch",
        default=RT_DEFAULTS["energy_thres"],
        min=1.0e-12,
        soft_max=1.0e-3,
        precision=8,
    )

    rt_time_thres: FloatProperty(
        name="Time Threshold (s)",
        description="Maximum duration considered by the ray-tracing branch",
        default=RT_DEFAULTS["time_thres"],
        min=0.01,
        soft_max=10.0,
        precision=3,
    )

    source_swl: bpy.props.FloatProperty(
    	name="Source Power (dB SWL)",
    	description="Sound power level of the source in dB re 1 pW. Typical values: speech ~70 dB, loudspeaker ~110 dB, reference ~120 dB",
    	default=120.0,
    	min=0.0,
    	max=200.0,
    )

    # Materials

    wall_material: EnumProperty(
        name="Wall Material",
        items=MATERIAL_ITEMS,
        default="reflective_plaster",
    )

    floor_material: EnumProperty(
        name="Floor Material",
        items=MATERIAL_ITEMS,
        default="carpet",
    )

    ceiling_material: EnumProperty(
        name="Ceiling Material",
        items=MATERIAL_ITEMS,
        default="acoustic_ceiling",
    )

    # Receiver layout

    selected_band: EnumProperty(
        name="Frequency Band",
        items=BAND_ITEMS,
        default="500",
    )

    grid_spacing: FloatProperty(
        name="Grid Spacing",
        default=0.5,
        min=0.05,
    )

    max_receivers: IntProperty(
        name="Max Receivers",
        default=500,
        min=1,
    )

    selected_receiver_area: EnumProperty(
        name="Receiver Area (MAP_*)",
        items=receiver_area_enum_items,
    )

    # Display options

    room_volume_display_mode: EnumProperty(
        name="Room Volume Display",
        items=ROOM_VOLUME_DISPLAY_ITEMS,
        default="normal",
        update=_on_room_volume_display_mode_changed,
    )

    selected_metric: EnumProperty(
        name="Metric",
        items=METRIC_ITEMS,
        default="c80_db",
    )

    display_mode: EnumProperty(
        name="Display Mode",
        items=DISPLAY_MODE_ITEMS,
        default="single",
    )

    display_mode_single_only: EnumProperty(
        name="Display Mode",
        items=DISPLAY_MODE_SINGLE_ONLY_ITEMS,
    )

    selected_display_source: EnumProperty(
        name="Display Source (SRC_*)",
        items=source_enum_items,
    )

    create_markers: BoolProperty(
        name="Create Markers",
        default=True,
    )

    marker_size: FloatProperty(
        name="Marker Size",
        default=0.08,
        min=0.01,
    )

    create_heatmap: BoolProperty(
        name="Create Heatmap",
        default=True,
    )

    heatmap_offset: FloatProperty(
        name="Heatmap Offset",
        default=0.02,
        min=0.0,
    )

    # Run status

    last_result: StringProperty(
        name="Last Result",
        default="No run executed yet.",
    )

    last_engine_status: StringProperty(
        name="Last Engine Status",
        default="",
    )

    last_runtime_note: StringProperty(
        name="Last Runtime Note",
        default="",
    )

    last_random_seed_note: StringProperty(
        name="Last Random Seed Note",
        default="",
    )

    last_context: StringProperty(
        name="Last Context",
        default="",
    )

    last_results_path: StringProperty(
        name="Last Results Path",
        default="",
    )

    simulation_progress: IntProperty(
        name="Simulation Progress",
        default=0,
        min=0,
        max=100,
        subtype='PERCENTAGE',
    )

    simulation_status: StringProperty(
        name="Simulation Status",
        default="",
    )
