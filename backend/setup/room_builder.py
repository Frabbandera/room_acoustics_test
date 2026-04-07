"""
Pyroomacoustics room builders for the Room Acoustics backend.

The module builds and populates Pyroomacoustics Room objects starting
from already-resolved scene configuration data.

This file contains shared helpers for PRA room construction.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import numpy as np
import pyroomacoustics as pra

import shared.result_keys as RK
import shared.scene_keys as SK

from backend.setup.room_geometry import build_prismatic_room_walls

# ---------------------------------------------------------------------------
# Room construction helpers
# ---------------------------------------------------------------------------

def build_pra_room(
    cfg,
    *,
    ray_tracing=False,
    ray_tracing_kwargs=None,
):
    walls = build_prismatic_room_walls(
        floor_polygon=cfg["floor_polygon"],
        height=cfg["height"],
        wall_abs=cfg["wall_abs"],
        floor_abs=cfg["floor_abs"],
        ceiling_abs=cfg["ceiling_abs"],
        wall_scat=cfg["wall_scat"],
        floor_scat=cfg["floor_scat"],
        ceiling_scat=cfg["ceiling_scat"],
    )

    room_kwargs = {
        "walls": walls,
        "fs": cfg["fs"],
        "max_order": cfg["max_order"],
        "air_absorption": cfg["air_absorption"],
    }

    if ray_tracing:
        room_kwargs["ray_tracing"] = True

    room = pra.Room(**room_kwargs)

    if ray_tracing:
        rt_kwargs = dict(ray_tracing_kwargs or {})
        room.set_ray_tracing(**rt_kwargs)

    return room

# ---------------------------------------------------------------------------
# Room population helpers
# ---------------------------------------------------------------------------

def add_sources_to_room(room, sources):
    source_names = []

    for source in sources:
        source_name = source[SK.NAME]
        source_position = np.array(source[SK.POSITION], dtype=float)

        if not room.is_inside(source_position, include_borders=True):
            raise ValueError(
                f"Source {source_name} is outside the room: "
                f"{source_position.tolist()}"
            )

        room.add_source(source_position)
        source_names.append(source_name)

    return source_names


def add_microphones_to_room(room, flat_receivers):
    mic_positions = np.array(
        [receiver[RK.POSITION] for receiver in flat_receivers],
        dtype=float,
    ).T

    room.add_microphone_array(mic_positions)