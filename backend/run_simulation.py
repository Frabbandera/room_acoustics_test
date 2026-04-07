"""
Backend entry-point for the Room Acoustics simulation workflow.

The module loads an exported scene description, resolves the requested
simulation settings, runs the selected solver, and writes JSON and CSV
result files.

This file contains backend orchestration logic for solver execution and
result serialization.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import argparse
import json
import sys
from pathlib import Path


# Project bootstrap

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import pyroomacoustics as pra

import shared.result_keys as RK
import shared.scene_keys as SK

from shared.catalogs import get_ray_tracing_defaults

from backend.postprocessing.results import (
    build_results_dict,
    write_results_csv,
)
from backend.solvers.solver_hybrid_rt import run_hybrid_rt_simulation
from backend.solvers.solver_ism import run_ism_simulation
from backend.setup.scene_validation import validate_scene_payload

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_ENGINES = {"ISM_ONLY", "HYBRID_RT"}
DEFAULT_ENGINE = "ISM_ONLY"

DEFAULT_RT_CONFIG = get_ray_tracing_defaults()

# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def load_scene(scene_path):
    with scene_path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)

# ---------------------------------------------------------------------------
# Simulation request helpers
# ---------------------------------------------------------------------------

def resolve_requested_engine(scene):
    simulation_cfg = scene.get(SK.SIMULATION, {})

    requested_engine = simulation_cfg.get(SK.ENGINE, DEFAULT_ENGINE)
    if requested_engine is None:
        requested_engine = DEFAULT_ENGINE

    requested_engine = str(requested_engine).strip().upper()

    if requested_engine == "":
        requested_engine = DEFAULT_ENGINE

    if requested_engine not in SUPPORTED_ENGINES:
        raise ValueError(
            f"Invalid simulation engine: {requested_engine}. "
            f"Supported values: {sorted(SUPPORTED_ENGINES)}"
        )

    return requested_engine


def resolve_requested_random_seed(scene):
    simulation_cfg = scene.get(SK.SIMULATION, {})

    requested_engine = resolve_requested_engine(scene)
    if requested_engine == "ISM_ONLY":
        return None

    use_fixed_random_seed = bool(
        simulation_cfg.get(SK.USE_FIXED_RANDOM_SEED, True)
    )

    if not use_fixed_random_seed:
        return None

    random_seed = int(simulation_cfg.get(SK.RANDOM_SEED, 12345))

    if random_seed < 0:
        raise ValueError("random_seed must be >= 0.")

    return random_seed


def resolve_requested_rt_config(scene):
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

    return {
        RK.N_RAYS: n_rays,
        RK.RECEIVER_RADIUS: receiver_radius,
        RK.HIST_BIN_SIZE: hist_bin_size,
        RK.ENERGY_THRES: energy_thres,
        RK.TIME_THRES: time_thres,
    }


def seed_pyroomacoustics_if_needed(requested_random_seed):
    if requested_random_seed is not None:
        pra.random.seed(requested_random_seed)

# ---------------------------------------------------------------------------
# Solver dispatch
# ---------------------------------------------------------------------------

def run_solver_for_engine(scene, requested_engine):
    if requested_engine == "ISM_ONLY":
        return run_ism_simulation(scene)

    if requested_engine == "HYBRID_RT":
        return run_hybrid_rt_simulation(scene)

    raise ValueError(f"Unsupported requested engine: {requested_engine}")

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def build_simulation_info(scene, solver_output, requested_engine, requested_random_seed):
    return {
        RK.REQUESTED_ENGINE: requested_engine,
        RK.EXECUTED_ENGINE: solver_output["executed_engine"],
        RK.WARNING_MESSAGE: solver_output["warning_message"],
        RK.RANDOM_SEED_REQUESTED: requested_random_seed,
        RK.RANDOM_SEED_USED: requested_random_seed,
        RK.FALLBACK_ACTIVE: bool(solver_output.get("fallback_active", False)),
        RK.SCENE_MAX_ORDER_REQUESTED: solver_output.get("scene_max_order_requested"),
        RK.EFFECTIVE_MAX_ORDER_USED: solver_output.get("effective_max_order_used"),
        RK.RT_CONFIG_REQUESTED: resolve_requested_rt_config(scene),
        RK.RT_CONFIG_USED: solver_output.get("rt_config_used"),
    }


def print_run_summary(simulation_info):
    print(f"[RA] requested_engine = {simulation_info[RK.REQUESTED_ENGINE]}")
    print(f"[RA] executed_engine = {simulation_info[RK.EXECUTED_ENGINE]}")
    print(f"[RA] random_seed = {simulation_info[RK.RANDOM_SEED_REQUESTED]}")
    print(f"[RA] fallback_active = {simulation_info[RK.FALLBACK_ACTIVE]}")

    warning_message = simulation_info[RK.WARNING_MESSAGE]
    if warning_message is not None:
        print(f"[RA][WARNING] {warning_message}")


def write_outputs(
    out_path,
    scene,
    simulation_info,
    band_info,
    materials_info,
    source_names,
    out_receiver_areas,
):
    out_path.parent.mkdir(parents=True, exist_ok=True)

    csv_path = out_path.with_suffix(".csv")
    write_results_csv(
        csv_path,
        out_receiver_areas,
        band_info,
        materials_info,
        source_names,
    )

    results = build_results_dict(
        scene=scene,
        simulation_info=simulation_info,
        band_info=band_info,
        materials_info=materials_info,
        source_names=source_names,
        out_receiver_areas=out_receiver_areas,
        csv_path=csv_path,
    )

    with out_path.open("w", encoding="utf-8") as file_obj:
        json.dump(results, file_obj, indent=2)

    return results

# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    scene_path = Path(args.scene)
    out_path = Path(args.out)

    scene = load_scene(scene_path)
    validate_scene_payload(scene)

    requested_engine = resolve_requested_engine(scene)
    requested_random_seed = resolve_requested_random_seed(scene)

    seed_pyroomacoustics_if_needed(requested_random_seed)

    solver_output = run_solver_for_engine(scene, requested_engine)

    simulation_info = build_simulation_info(
        scene,
        solver_output,
        requested_engine,
        requested_random_seed,
    )
    print_run_summary(simulation_info)

    results = write_outputs(
        out_path=out_path,
        scene=scene,
        simulation_info=simulation_info,
        band_info=solver_output["band_info"],
        materials_info=solver_output["materials_info"],
        source_names=solver_output["source_names"],
        out_receiver_areas=solver_output["out_receiver_areas"],
    )

    print("Multi-source multi-area simulation completed successfully.")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()