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


def spl_from_rir(rir):
    rir = _as_float_array(rir)
    total_energy = np.sum(rir ** 2) + EPS

    return 10.0 * np.log10(total_energy)

# ---------------------------------------------------------------------------
# Metric collection builder
# ---------------------------------------------------------------------------

def compute_metrics_from_rir(rir, fs):
    return {
        "c50_db": float(c50_from_rir(rir, fs)),
        "c80_db": float(c80_from_rir(rir, fs)),
        "d50": float(d50_from_rir(rir, fs)),
        "spl_db": float(spl_from_rir(rir)),
    }

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