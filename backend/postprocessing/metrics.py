"""
Metric helpers for the Room Acoustics backend.

The module computes acoustic metrics from room impulse responses and
builds summary statistics for receiver groups.

This file contains metric computation and metric-summary helpers.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import numpy as np

from shared.catalogs import METRIC_CATALOG

# ---------------------------------------------------------------------------
# Constants and metric metadata
# ---------------------------------------------------------------------------

EPS = 1e-12

METRIC_META = {
    key: {
        "label": meta["label"],
        "unit": meta["unit"],
    }
    for key, meta in METRIC_CATALOG.items()
}

# ---------------------------------------------------------------------------
# Internal numeric helpers
# ---------------------------------------------------------------------------

def _as_float_array(rir):
    return np.asarray(rir, dtype=float)


def _split_index_from_ms(rir, fs, t_ms):
    split = int((float(t_ms) / 1000.0) * fs)
    return max(0, min(len(rir), split))

# ---------------------------------------------------------------------------
# Metric computation helpers
# ---------------------------------------------------------------------------

def clarity_from_rir(rir, fs, t_ms):
    rir = _as_float_array(rir)
    split = _split_index_from_ms(rir, fs, t_ms)

    early_energy = np.sum(rir[:split] ** 2)
    late_energy = np.sum(rir[split:] ** 2) + EPS

    return 10.0 * np.log10((early_energy + EPS) / late_energy)


def c50_from_rir(rir, fs):
    return clarity_from_rir(rir, fs, 50.0)


def c80_from_rir(rir, fs):
    return clarity_from_rir(rir, fs, 80.0)


def d50_from_rir(rir, fs):
    rir = _as_float_array(rir)
    split = _split_index_from_ms(rir, fs, 50.0)

    early_energy = np.sum(rir[:split] ** 2)
    total_energy = np.sum(rir ** 2) + EPS

    return early_energy / total_energy


def spl_from_rir(rir, source_swl=120.0):
    rir = _as_float_array(rir)
    total_energy = np.sum(rir ** 2) + EPS

    # Convert source SWL (dB re 1pW) to linear power scaling factor
    source_power_linear = 10 ** ((source_swl - 120.0) / 10.0)

    # Scale energy by source power and reference to 20 uPa (p_ref^2 = 4e-10)
    p_ref_squared = 4e-10
    absolute_energy = total_energy * source_power_linear

    return 10.0 * np.log10(absolute_energy / p_ref_squared + EPS)

# ---------------------------------------------------------------------------
# Metric collection builder
# ---------------------------------------------------------------------------

def compute_metrics_from_rir(rir, fs, source_swl=120.0):
    return {
        "c50_db": float(c50_from_rir(rir, fs)),
        "c80_db": float(c80_from_rir(rir, fs)),
        "d50": float(d50_from_rir(rir, fs)),
        "spl_db": float(spl_from_rir(rir, source_swl)),
    }


def apply_zone_correction(metrics, receiver_position, zone_absorption, room_bounds, zone_grid=3):
    """
    Apply zone-based absorption correction to metrics.
    Receivers in zones with furniture get higher absorption correction.
    """
    if not zone_absorption or not room_bounds:
        return metrics

    rx = float(receiver_position[0])
    ry = float(receiver_position[1])

    min_x = room_bounds.get("min_x", -3.0)
    max_x = room_bounds.get("max_x", 3.0)
    min_y = room_bounds.get("min_y", -2.0)
    max_y = room_bounds.get("max_y", 2.0)

    room_width = max_x - min_x
    room_depth = max_y - min_y

    if room_width < 1e-6 or room_depth < 1e-6:
        return metrics

    zone_i = min(int((rx - min_x) / room_width * zone_grid), zone_grid - 1)
    zone_j = min(int((ry - min_y) / room_depth * zone_grid), zone_grid - 1)
    zone_i = max(0, zone_i)
    zone_j = max(0, zone_j)
    zone_key = f"{zone_i}_{zone_j}"

    correction = zone_absorption.get(zone_key, 0.0)

    if correction < 1e-6:
        return metrics

    corrected = dict(metrics)
    corrected["spl_db"] = metrics["spl_db"] - correction * 10.0
    corrected["c50_db"] = metrics["c50_db"] + correction * 5.0
    corrected["c80_db"] = metrics["c80_db"] + correction * 5.0
    corrected["d50"] = min(1.0, metrics["d50"] + correction * 0.1)

    return corrected


# ---------------------------------------------------------------------------
# Metric summary builder
# ---------------------------------------------------------------------------

def build_metric_summaries(receivers):
    summaries = {}

    for metric_key, metric_meta in METRIC_META.items():
        values = np.array(
            [receiver["metrics"][metric_key] for receiver in receivers],
            dtype=float,
        )

        summaries[metric_key] = {
            "label": metric_meta["label"],
            "unit": metric_meta["unit"],
            "min_value": float(np.min(values)),
            "max_value": float(np.max(values)),
            "mean_value": float(np.mean(values)),
        }

    return summaries
