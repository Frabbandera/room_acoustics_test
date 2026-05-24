"""
ISM solver helpers for the Room Acoustics backend.
"""

import numpy as np
from backend.postprocessing.multi_area import build_output_receiver_areas
from backend.setup.room_setup import build_room_setup_from_scene


def run_ism_simulation(scene):
    setup = build_room_setup_from_scene(
        scene,
        ray_tracing=False,
        use_material_scattering=False,
        override_max_order=None,
    )

    room = setup["room"]
    fs = setup["fs"]
    source_names = setup["source_names"]
    flat_receivers = setup["flat_receivers"]
    area_spans = setup["area_spans"]
    band_info = setup["band_info"]
    materials_info = setup["materials_info"]

    room.compute_rir()

    out_receiver_areas = build_output_receiver_areas(
        flat_receivers=flat_receivers,
        area_spans=area_spans,
        room=room,
        source_names=source_names,
        fs=fs,
    )

    return {
        "executed_engine": "ISM_ONLY",
        "warning_message": None,
        "fallback_active": False,
        "scene_max_order_requested": setup["scene_max_order"],
        "effective_max_order_used": setup["effective_max_order"],
        "hybrid_info": None,
        "rt_config_used": None,
        "band_info": band_info,
        "materials_info": materials_info,
        "source_names": source_names,
        "out_receiver_areas": out_receiver_areas,
    }
