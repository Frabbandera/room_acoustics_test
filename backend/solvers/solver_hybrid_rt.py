"""
Hybrid RT solver helpers for the Room Acoustics backend.

The module resolves the ray-tracing configuration, runs the hybrid
Pyroomacoustics simulation path, and falls back to ISM when needed.

This file contains the HYBRID_RT solver entry-point and its fallback logic.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import shared.scene_keys as SK

from shared.catalogs import get_ray_tracing_defaults

from backend.setup.room_setup import build_room_setup_from_scene
from backend.solvers.solver_ism import run_ism_simulation
from backend.postprocessing.multi_area import build_output_receiver_areas

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_RT_CONFIG = get_ray_tracing_defaults()

# ---------------------------------------------------------------------------
# Ray-tracing config helpers
# ---------------------------------------------------------------------------

def resolve_ray_tracing_config(scene):
    simulation_cfg = scene.get(SK.SIMULATION, {})
    rt_cfg = simulation_cfg.get(SK.RAY_TRACING, {}) or {}

    n_rays = int(rt_cfg.get(SK.N_RAYS, DEFAULT_RT_CONFIG["n_rays"]))
    receiver_radius = float(
        rt_cfg.get(SK.RECEIVER_RADIUS, DEFAULT_RT_CONFIG["receiver_radius"])
    )
    hist_bin_size = float(
        rt_cfg.get(SK.HIST_BIN_SIZE, DEFAULT_RT_CONFIG["hist_bin_size"])
    )
    energy_thres = float(
        rt_cfg.get(SK.ENERGY_THRES, DEFAULT_RT_CONFIG["energy_thres"])
    )
    time_thres = float(
        rt_cfg.get(SK.TIME_THRES, DEFAULT_RT_CONFIG["time_thres"])
    )

    if n_rays <= 0:
        raise ValueError("Invalid RT config: n_rays must be > 0.")

    if receiver_radius <= 0.0:
        raise ValueError("Invalid RT config: receiver_radius must be > 0.")

    if hist_bin_size <= 0.0:
        raise ValueError("Invalid RT config: hist_bin_size must be > 0.")

    if energy_thres <= 0.0:
        raise ValueError("Invalid RT config: energy_thres must be > 0.")

    if time_thres <= 0.0:
        raise ValueError("Invalid RT config: time_thres must be > 0.")

    return {
        "n_rays": n_rays,
        "receiver_radius": receiver_radius,
        "hist_bin_size": hist_bin_size,
        "energy_thres": energy_thres,
        "time_thres": time_thres,
    }

# ---------------------------------------------------------------------------
# Hybrid solver entry-point
# ---------------------------------------------------------------------------

def run_hybrid_rt_simulation(scene):
    rt_config = resolve_ray_tracing_config(scene)

    scene_max_order = int(scene[SK.SIMULATION][SK.MAX_ORDER])
    effective_max_order = scene_max_order

    try:
        setup = build_room_setup_from_scene(
            scene,
            ray_tracing=True,
            ray_tracing_kwargs=rt_config,
            use_material_scattering=True,
            override_max_order=effective_max_order,
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

        warning_message = (
            "HYBRID_RT executed with pyroomacoustics and active ray tracing. "
            f"max_order={effective_max_order}. "
            "Pyroomacoustics suggests using max_order=3 with the hybrid simulator."
        )

        return {
            "executed_engine": "HYBRID_RT",
            "warning_message": warning_message,
            "fallback_active": False,
            "rt_config_used": dict(rt_config),
            "scene_max_order_requested": scene_max_order,
            "effective_max_order_used": effective_max_order,
            "band_info": band_info,
            "materials_info": materials_info,
            "source_names": source_names,
            "out_receiver_areas": out_receiver_areas,
        }

    except Exception as exc:
        solver_output = run_ism_simulation(scene)

        solver_output["executed_engine"] = "ISM_ONLY"
        solver_output["warning_message"] = (
            "HYBRID_RT execution failed; fallback to ISM_ONLY was applied. "
            f"scene max_order={scene_max_order}, "
            f"Reason: {exc}"
        )
        solver_output["fallback_active"] = True
        solver_output["rt_config_used"] = None
        solver_output["scene_max_order_requested"] = scene_max_order
        solver_output["effective_max_order_used"] = None

        return solver_output