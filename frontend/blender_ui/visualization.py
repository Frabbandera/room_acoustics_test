"""
Result-visualization helpers for the Room Acoustics frontend.

The module builds Blender objects used to display simulation results,
including per-receiver markers and heatmap meshes.

This file contains frontend visualization logic for result payloads.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import bpy

import shared.result_keys as RK
import shared.scene_keys as SK


# ---------------------------------------------------------------------------
# Collection helpers
# ---------------------------------------------------------------------------

def ensure_named_collection(scene, collection_name):
    collection = bpy.data.collections.get(collection_name)

    if collection is None:
        collection = bpy.data.collections.new(collection_name)

    already_linked = False
    for child in scene.collection.children:
        if child.name == collection.name:
            already_linked = True
            break

    if not already_linked:
        scene.collection.children.link(collection)

    return collection


def clear_collection_objects(collection):
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

# ---------------------------------------------------------------------------
# Room-volume display helpers
# ---------------------------------------------------------------------------

def apply_room_volume_display_mode(context):
    props = context.scene.ra_test_props
    room_obj = bpy.data.objects.get("RoomVolume")

    if room_obj is None:
        return False

    mode = props.room_volume_display_mode

    if mode == "hide":
        room_obj.hide_viewport = True
        return True

    room_obj.hide_viewport = False

    if mode == "wire":
        room_obj.display_type = "WIRE"
    else:
        room_obj.display_type = "TEXTURED"

    return True

# ---------------------------------------------------------------------------
# Numeric and color helpers
# ---------------------------------------------------------------------------

def normalize_value(value, min_value, max_value):
    if abs(max_value - min_value) < 1e-12:
        return 0.5

    return max(0.0, min(1.0, (value - min_value) / (max_value - min_value)))

def lerp(a, b, t):
    return a + (b - a) * t


def heatmap_rgb(t):
    if t <= 0.25:
        local_t = t / 0.25
        return (0.0, lerp(0.0, 1.0, local_t), 1.0)

    if t <= 0.50:
        local_t = (t - 0.25) / 0.25
        return (0.0, 1.0, lerp(1.0, 0.0, local_t))

    if t <= 0.75:
        local_t = (t - 0.50) / 0.25
        return (lerp(0.0, 1.0, local_t), 1.0, 0.0)

    local_t = (t - 0.75) / 0.25
    return (1.0, lerp(1.0, 0.0, local_t), 0.0)

# ---------------------------------------------------------------------------
# Result-selection helpers
# ---------------------------------------------------------------------------

def get_selected_area_result(results, area_name):
    for area in results[RK.RECEIVER_AREAS]:
        if area[RK.NAME] == area_name:
            return area

    if len(results[RK.RECEIVER_AREAS]) == 1:
        return results[RK.RECEIVER_AREAS][0]

    raise RuntimeError(f"Receiver area '{area_name}' not found in the results.")


def get_display_summary(area_results, metric_key, display_mode, selected_source):
    if display_mode == "single":
        if selected_source not in area_results[RK.PER_SOURCE_METRIC_SUMMARIES]:
            raise RuntimeError(
                f"Source '{selected_source}' not found in the results for area "
                f"{area_results[RK.NAME]}."
            )
        return area_results[RK.PER_SOURCE_METRIC_SUMMARIES][selected_source][metric_key]

    return area_results[RK.AVG_METRIC_SUMMARIES][metric_key]


def get_display_value(receiver_result, metric_key, display_mode, selected_source):
    if display_mode == "single":
        if selected_source not in receiver_result[RK.PER_SOURCE_METRICS]:
            raise RuntimeError(
                f"Source '{selected_source}' not found in receiver "
                f"{receiver_result[RK.ID]}."
            )
        return float(receiver_result[RK.PER_SOURCE_METRICS][selected_source][metric_key])

    return float(receiver_result[RK.AVG_METRICS][metric_key])

# ---------------------------------------------------------------------------
# Material builder
# ---------------------------------------------------------------------------

def build_heatmap_material():
    material_name = "RA_Heatmap_Mat"
    material = bpy.data.materials.get(material_name)

    if material is None:
        material = bpy.data.materials.new(material_name)

    material.use_nodes = True
    node_tree = material.node_tree
    nodes = node_tree.nodes
    links = node_tree.links

    nodes.clear()

    node_attr = nodes.new(type="ShaderNodeAttribute")
    node_attr.attribute_name = "ra_heatmap"
    node_attr.location = (-400, 0)

    node_emission = nodes.new(type="ShaderNodeEmission")
    node_emission.location = (-100, 0)
    node_emission.inputs["Strength"].default_value = 1.0

    node_output = nodes.new(type="ShaderNodeOutputMaterial")
    node_output.location = (200, 0)

    links.new(node_attr.outputs["Color"], node_emission.inputs["Color"])
    links.new(node_emission.outputs["Emission"], node_output.inputs["Surface"])

    return material

# ---------------------------------------------------------------------------
# Visualization builders
# ---------------------------------------------------------------------------

def create_result_markers(
    context,
    area_results,
    band_label,
    metric_key,
    display_mode,
    selected_source,
):
    props = context.scene.ra_test_props

    collection = ensure_named_collection(context.scene, "RA_Results")
    clear_collection_objects(collection)

    metric_info = get_display_summary(
        area_results,
        metric_key,
        display_mode,
        selected_source,
    )
    metric_label = metric_info[RK.LABEL]
    metric_unit = metric_info[RK.UNIT]

    for receiver_result in area_results[RK.RECEIVERS]:
        world_pos = receiver_result[RK.WORLD_POSITION]
        value = get_display_value(
            receiver_result,
            metric_key,
            display_mode,
            selected_source,
        )

        obj = bpy.data.objects.new(
            f"R_{area_results[RK.NAME]}_{int(receiver_result[RK.ID]):03d}",
            None,
        )
        obj.empty_display_type = "SPHERE"
        obj.empty_display_size = props.marker_size
        obj.location = world_pos

        obj["metric_key"] = metric_key
        obj["metric_label"] = metric_label
        obj["metric_value"] = value
        obj["metric_unit"] = metric_unit
        obj["band_label"] = band_label
        obj["display_mode"] = display_mode
        obj["display_source"] = (
            selected_source if display_mode == "single" else "average"
        )
        obj["receiver_area"] = area_results[RK.NAME]

        collection.objects.link(obj)


def create_heatmap_object(
    context,
    area_results,
    band_label,
    metric_key,
    display_mode,
    selected_source,
):
    props = context.scene.ra_test_props

    mapping = area_results[RK.MAPPING]
    spacing = float(mapping[SK.SPACING])

    if spacing <= 0:
        raise RuntimeError("Invalid mapping spacing.")

    receivers = area_results[RK.RECEIVERS]
    if not receivers:
        raise RuntimeError("No receivers available to create the heatmap.")

    collection = ensure_named_collection(context.scene, "RA_Heatmap")
    clear_collection_objects(collection)

    verts = []
    faces = []
    point_colors = []

    metric_summary = get_display_summary(
        area_results,
        metric_key,
        display_mode,
        selected_source,
    )

    # Collect all values for percentile calculation
    all_values = [
        get_display_value(r, metric_key, display_mode, selected_source)
        for r in receivers
    ]
    all_values_sorted = sorted(all_values)
    n = len(all_values_sorted)

    # Use 5th and 95th percentile to ignore outliers
    p5_index  = max(0, int(0.05 * n))
    p95_index = min(n - 1, int(0.95 * n))
    min_value = all_values_sorted[p5_index]
    max_value = all_values_sorted[p95_index]

    # Fallback to min/max if percentiles are too close
    if abs(max_value - min_value) < 1e-6:
        min_value = float(metric_summary[RK.MIN_VALUE])
        max_value = float(metric_summary[RK.MAX_VALUE])

    half_spacing = spacing / 2.0

    for receiver_result in receivers:
        world_pos = receiver_result[RK.WORLD_POSITION]
        x = float(world_pos[0])
        y = float(world_pos[1])
        z = float(world_pos[2]) + props.heatmap_offset

        value = get_display_value(
            receiver_result,
            metric_key,
            display_mode,
            selected_source,
        )
        t = normalize_value(value, min_value, max_value)
        r, g, b = heatmap_rgb(t)

        base_index = len(verts)

        verts.extend([
            (x - half_spacing, y - half_spacing, z),
            (x + half_spacing, y - half_spacing, z),
            (x + half_spacing, y + half_spacing, z),
            (x - half_spacing, y + half_spacing, z),
        ])

        faces.append((
            base_index,
            base_index + 1,
            base_index + 2,
            base_index + 3,
        ))

        point_colors.extend([
            (r, g, b, 1.0),
            (r, g, b, 1.0),
            (r, g, b, 1.0),
            (r, g, b, 1.0),
        ])

    mesh = bpy.data.meshes.new("RA_Heatmap_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    color_attr = mesh.color_attributes.new(
        name="ra_heatmap",
        type="FLOAT_COLOR",
        domain="POINT",
    )

    if len(color_attr.data) != len(point_colors):
        raise RuntimeError(
            f"Inconsistent color count: expected {len(color_attr.data)}, "
            f"found {len(point_colors)}."
        )

    for index, rgba in enumerate(point_colors):
        color_attr.data[index].color = rgba

    obj = bpy.data.objects.new("RA_Heatmap", mesh)
    collection.objects.link(obj)

    obj["metric_key"] = metric_key
    obj["metric_label"] = metric_summary[RK.LABEL]
    obj["metric_unit"] = metric_summary[RK.UNIT]
    obj["band_label"] = band_label
    obj["display_mode"] = display_mode
    obj["display_source"] = (
        selected_source if display_mode == "single" else "average"
    )
    obj["receiver_area"] = area_results[RK.NAME]

    material = build_heatmap_material()

    if len(obj.data.materials) == 0:
        obj.data.materials.append(material)
    else:
        obj.data.materials[0] = material

    return obj

def create_heatmap_legend(
    context,
    metric_key,
    metric_label,
    metric_unit,
    min_value,
    max_value,
    band_label,
):
    """Creates a color legend mesh next to the heatmap."""
    props = context.scene.ra_test_props

    collection = ensure_named_collection(context.scene, "RA_Legend")
    clear_collection_objects(collection)

    num_steps = 20
    step_height = 0.15
    step_width = 0.4
    legend_x = 2.0
    legend_y = 0.0
    legend_z = float(props.audience_height) + float(props.heatmap_offset) + 0.1

    verts = []
    faces = []
    colors = []

    for i in range(num_steps):
        t = i / (num_steps - 1)
        r, g, b = heatmap_rgb(t)

        x = legend_x
        y = legend_y + i * step_height
        z = legend_z

        base = len(verts)
        verts.extend([
            (x, y, z),
            (x + step_width, y, z),
            (x + step_width, y + step_height, z),
            (x, y + step_height, z),
        ])
        faces.append((base, base + 1, base + 2, base + 3))
        colors.extend([(r, g, b, 1.0)] * 4)

    mesh = bpy.data.meshes.new("RA_Legend_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    color_attr = mesh.color_attributes.new(
        name="ra_heatmap",
        type="FLOAT_COLOR",
        domain="POINT",
    )
    for index, rgba in enumerate(colors):
        color_attr.data[index].color = rgba

    obj = bpy.data.objects.new("RA_Legend", mesh)
    collection.objects.link(obj)

    material = build_heatmap_material()
    if len(obj.data.materials) == 0:
        obj.data.materials.append(material)
    else:
        obj.data.materials[0] = material

    # Add min and max text labels
    unit_text = f" {metric_unit}" if metric_unit else ""

    for label_text, label_z in [
        (f"max: {max_value:.1f}{unit_text}", legend_z + num_steps * step_height + 0.1),
        (f"min: {min_value:.1f}{unit_text}", legend_z - 0.3),
        (f"{metric_label} @ {band_label}", legend_z + num_steps * step_height + 0.4),
    ]:
        curve = bpy.data.curves.new(label_text, type='FONT')
        curve.body = label_text
        curve.size = 0.15
        text_obj = bpy.data.objects.new(label_text, curve)
        text_obj.location = (legend_x, legend_y, label_z)
        collection.objects.link(text_obj)

    create_heatmap_legend(
        context,
        metric_key,
        metric_summary[RK.LABEL],
        metric_summary[RK.UNIT],
        min_value,
        max_value,
        band_label,
    )

    return obj
