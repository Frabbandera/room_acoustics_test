"""
UI text helpers for the Room Acoustics frontend.

The module provides small formatting and labeling helpers used by the
Blender panels and operators to present readable UI messages.

This file contains no simulation logic. Its purpose is to keep UI text
formatting centralized, readable, and consistent across the frontend.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import shared.result_keys as RK

# ---------------------------------------------------------------------------
# Private text helpers
# ---------------------------------------------------------------------------

def _compact_ui_text(text, max_len=120):
    if not text:
        return ""

    compact = " ".join(str(text).split())
    if len(compact) <= max_len:
        return compact

    return compact[: max_len - 3] + "..."

# ---------------------------------------------------------------------------
# UI label helpers
# ---------------------------------------------------------------------------

def get_engine_ui_label(engine_name):
    if engine_name == "ISM_ONLY":
        return "ISM Only"
    if engine_name == "HYBRID_RT":
        return "Hybrid RT"
    return str(engine_name)


def get_room_mode_ui_label(mode):
    if mode == "room_volume_prism":
        return "vertical prism"
    return str(mode)

# ---------------------------------------------------------------------------
# UI formatting helpers
# ---------------------------------------------------------------------------

def format_runtime_note_ui(requested_engine, executed_engine, warning_message):
    if not warning_message:
        return ""

    if requested_engine == "HYBRID_RT" and executed_engine == "ISM_ONLY":
        return (
            "Warning: HYBRID_RT failed and fell back to ISM_ONLY | "
            f"{_compact_ui_text(warning_message, 120)}"
        )

    if requested_engine == "HYBRID_RT" and executed_engine == "HYBRID_RT":
        return (
            "Note: HYBRID_RT is active | "
            "The pyroomacoustics hybrid solver is experimental. Review results carefully."
        )

    return f"Warning: {_compact_ui_text(warning_message, 120)}"


def format_random_seed_ui(simulation_info):
    if not simulation_info:
        return ""

    requested_engine = simulation_info.get(RK.REQUESTED_ENGINE)
    executed_engine = simulation_info.get(RK.EXECUTED_ENGINE)
    requested_seed = simulation_info.get(RK.RANDOM_SEED_REQUESTED)
    used_seed = simulation_info.get(RK.RANDOM_SEED_USED)

    if requested_engine == "ISM_ONLY" and executed_engine == "ISM_ONLY":
        return "Random seed: not used"

    if requested_seed is None and used_seed is None:
        return "Random seed: stochastic"

    if requested_seed == used_seed:
        return f"Random seed: {used_seed}"

    return f"Random seed: requested={requested_seed}, used={used_seed}"


def format_hybrid_max_order_warning(props):
    if props.simulation_engine != "HYBRID_RT":
        return ""

    if int(props.max_order) > 3:
        return "Warning: for HYBRID_RT, Pyroomacoustics suggests max_order ≤ 3."

    return ""


def format_active_room_geometry_ui(room_status):
    if not room_status["ok"]:
        return "N/A"

    if room_status["mode"] == "room_volume_prism":
        return "vertical prism"

    return get_room_mode_ui_label(room_status["mode"])