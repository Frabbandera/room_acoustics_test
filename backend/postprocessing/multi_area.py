"""
Multi-area receiver helpers for the Room Acoustics backend.

The module manages the conversion between grouped receiver areas in the
input scene and the flattened receiver layout used during simulation.

This file contains receiver-area flattening and result reconstruction logic.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import numpy as np

import shared.result_keys as RK
import shared.scene_keys as SK

from backend.postprocessing.metrics import (
    build_metric_summaries,
    compute_metrics_from_rir,
)

# ---------------------------------------------------------------------------
# Internal span keys
# ---------------------------------------------------------------------------

_AREA_SPAN_START_IDX = "start_idx"
_AREA_SPAN_END_IDX = "end_idx"

# ---------------------------------------------------------------------------
# Metric aggregation helpers
# ---------------------------------------------------------------------------

def average_metric_dicts(metric_dicts):
    if len(metric_dicts) == 0:
        raise ValueError("No metric dictionaries were provided for averaging.")

    keys = list(metric_dicts[0].keys())
    averaged_metrics = {}

    for key in keys:
        values = np.array([metric_dict[key] for metric_dict in metric_dicts], dtype=float)
        averaged_metrics[key] = float(np.mean(values))

    return averaged_metrics


def build_avg_metric_summaries(receivers):
    wrapped_receivers = [{"metrics": rec[RK.AVG_METRICS]} for rec in receivers]
    return build_metric_summaries(wrapped_receivers)


def build_per_source_metric_summaries(receivers, source_names):
    summaries = {}

    for source_name in source_names:
        wrapped_receivers = [
            {"metrics": rec[RK.PER_SOURCE_METRICS][source_name]}
            for rec in receivers
        ]
        summaries[source_name] = build_metric_summaries(wrapped_receivers)

    return summaries

# ---------------------------------------------------------------------------
# Receiver-area flattening
# ---------------------------------------------------------------------------

def flatten_receiver_areas(receiver_areas_in, room):
    flat_receivers = []
    area_spans = []

    for area in receiver_areas_in:
        area_name = area[SK.NAME]
        area_receivers = area[SK.RECEIVERS]

        if len(area_receivers) == 0:
            raise ValueError(
                f"Receiver area '{area_name}' does not contain any receivers."
            )

        start_idx = len(flat_receivers)

        for receiver in area_receivers:
            position = np.array(receiver[SK.POSITION], dtype=float)

            if not room.is_inside(position, include_borders=True):
                raise ValueError(
                    f"Receiver {receiver[SK.ID]} in area '{area_name}' is outside "
                    f"the room: {position.tolist()}"
                )

            flat_receivers.append({
                RK.ID: receiver[SK.ID],
                RK.POSITION: receiver[SK.POSITION],
                RK.WORLD_POSITION: receiver[SK.WORLD_POSITION],
                RK.NAME: area_name,
            })

        end_idx = len(flat_receivers)

        area_spans.append({
            RK.NAME: area_name,
            RK.MAPPING: area[SK.MAPPING],
            _AREA_SPAN_START_IDX: start_idx,
            _AREA_SPAN_END_IDX: end_idx,
        })

    if len(flat_receivers) == 0:
        raise ValueError("No receivers are available across the receiver areas.")

    return flat_receivers, area_spans

# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------

def build_output_receiver_areas(flat_receivers, area_spans, room, source_names, fs, scene=None):

    out_receiver_areas = []

    for area_span in area_spans:
        area_name = area_span[RK.NAME]
        start_idx = area_span[_AREA_SPAN_START_IDX]
        end_idx = area_span[_AREA_SPAN_END_IDX]

        out_area_receivers = []

        for mic_idx in range(start_idx, end_idx):
            receiver = flat_receivers[mic_idx]
            per_source_metrics = {}

            for src_idx, source_name in enumerate(source_names):
                rir = np.asarray(room.rir[mic_idx][src_idx], dtype=float)
                source_swl = scene.get("simulation", {}).get("source_swl", 120.0) if scene else 120.0
                metrics = compute_metrics_from_rir(rir, fs, source_swl)

                # Apply zone-based furniture correction if available
                zone_absorption = scene.get("room", {}).get("zone_absorption", {}) if scene else {}
                room_bounds = scene.get("room", {}).get("room_bounds", {}) if scene else {}
                if zone_absorption:
                    from backend.postprocessing.metrics import apply_zone_correction
                    world_pos = receiver.get(RK.WORLD_POSITION, [0, 0, 0])
                    metrics = apply_zone_correction(
                        metrics,
                        world_pos,
                        zone_absorption,
                        room_bounds,
                    )

                per_source_metrics[source_name] = metrics

            avg_metrics = average_metric_dicts(list(per_source_metrics.values()))

            out_area_receivers.append({
                RK.ID: int(receiver[RK.ID]),
                RK.POSITION: receiver[RK.POSITION],
                RK.WORLD_POSITION: receiver[RK.WORLD_POSITION],
                RK.PER_SOURCE_METRICS: per_source_metrics,
                RK.AVG_METRICS: avg_metrics,
            })

        out_receiver_areas.append({
            RK.NAME: area_name,
            RK.MAPPING: area_span[RK.MAPPING],
            RK.SUMMARY: {
                RK.NUM_RECEIVERS: len(out_area_receivers),
            },
            RK.AVG_METRIC_SUMMARIES: build_avg_metric_summaries(out_area_receivers),
            RK.PER_SOURCE_METRIC_SUMMARIES: build_per_source_metric_summaries(
                out_area_receivers,
                source_names,
            ),
            RK.RECEIVERS: out_area_receivers,
        })

    return out_receiver_areas
