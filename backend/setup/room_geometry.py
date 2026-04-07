"""
Room-geometry builders for the Room Acoustics backend.

The module converts a 2D room footprint and acoustic surface parameters
into Pyroomacoustics wall objects.

This file contains geometry validation and wall-construction helpers for
simple prismatic rooms.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import numpy as np
import pyroomacoustics as pra

# ---------------------------------------------------------------------------
# Geometry validation helpers
# ---------------------------------------------------------------------------

def validate_polygon(floor_polygon):
    if len(floor_polygon) < 3:
        raise ValueError("floor_polygon must contain at least 3 vertices.")

    unique_points = {tuple(point) for point in floor_polygon}
    if len(unique_points) < 3:
        raise ValueError(
            "Invalid floor_polygon: at least 3 distinct vertices are required."
        )


def validate_height(height):
    height = float(height)

    if height <= 0.0:
        raise ValueError("height must be > 0.")

    return np.float32(height)

# ---------------------------------------------------------------------------
# Material-parameter helpers
# ---------------------------------------------------------------------------

def _as_unit_interval_array(name, value):
    value = float(value)

    if value < 0.0 or value > 1.0:
        raise ValueError(
            f"Invalid value for {name}: {value}. The value must be in the range [0, 1]."
        )

    return np.array([[value]], dtype=np.float32)

# ---------------------------------------------------------------------------
# Main wall builder
# ---------------------------------------------------------------------------

def build_prismatic_room_walls(
    floor_polygon,
    height,
    wall_abs,
    floor_abs,
    ceiling_abs,
    wall_scat=0.0,
    floor_scat=0.0,
    ceiling_scat=0.0,
):
    """
    Build a 3D prismatic room from a 2D floor polygon.

    The floor polygon is assumed to be counter-clockwise in the XY plane.
    """
    validate_polygon(floor_polygon)

    z0 = np.float32(0.0)
    z1 = validate_height(height)
    num_vertices = len(floor_polygon)

    wall_abs_arr = _as_unit_interval_array("wall_abs", wall_abs)
    floor_abs_arr = _as_unit_interval_array("floor_abs", floor_abs)
    ceiling_abs_arr = _as_unit_interval_array("ceiling_abs", ceiling_abs)

    wall_scat_arr = _as_unit_interval_array("wall_scat", wall_scat)
    floor_scat_arr = _as_unit_interval_array("floor_scat", floor_scat)
    ceiling_scat_arr = _as_unit_interval_array("ceiling_scat", ceiling_scat)

    walls = []

    # Vertical walls

    for index in range(num_vertices):
        p0 = floor_polygon[index]
        p1 = floor_polygon[(index + 1) % num_vertices]

        corners = np.array(
            [
                [float(p0[0]), float(p1[0]), float(p1[0]), float(p0[0])],
                [float(p0[1]), float(p1[1]), float(p1[1]), float(p0[1])],
                [z0, z0, z1, z1],
            ],
            dtype=np.float32,
        )

        walls.append(
            pra.wall_factory(
                corners,
                wall_abs_arr,
                wall_scat_arr,
                name=f"wall_{index}",
            )
        )

    # Floor

    floor_polygon_reversed = list(reversed(floor_polygon))
    floor_corners = np.array(
        [
            [float(point[0]) for point in floor_polygon_reversed],
            [float(point[1]) for point in floor_polygon_reversed],
            [z0] * num_vertices,
        ],
        dtype=np.float32,
    )

    walls.append(
        pra.wall_factory(
            floor_corners,
            floor_abs_arr,
            floor_scat_arr,
            name="floor",
        )
    )

    # Ceiling

    ceiling_corners = np.array(
        [
            [float(point[0]) for point in floor_polygon],
            [float(point[1]) for point in floor_polygon],
            [z1] * num_vertices,
        ],
        dtype=np.float32,
    )

    walls.append(
        pra.wall_factory(
            ceiling_corners,
            ceiling_abs_arr,
            ceiling_scat_arr,
            name="ceiling",
        )
    )

    return walls