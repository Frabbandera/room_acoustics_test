"""
Result-output helpers for the Room Acoustics backend.

The module writes result files produced by the backend, including the
receiver-level CSV export and the final JSON-compatible result payload.

This file contains output serialization helpers for simulation results.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import csv

import shared.result_keys as RK
import shared.scene_keys as SK

from backend.postprocessing.metrics import METRIC_META

# ---------------------------------------------------------------------------
# CSV schema constants
# ---------------------------------------------------------------------------

_BASE_CSV_FIELDS = [
    "area_name",
    "receiver_id",
    "band_key",
    "band_label",
    "walls_material_key",
    "walls_material_label",
    "floor_material_key",
    "floor_material_label",
    "ceiling_material_key",
    "ceiling_material_label",
    "world_x",
    "world_y",
    "world_z",
    "room_x",
    "room_y",
    "room_z",
]

# ---------------------------------------------------------------------------
# CSV output helpers
# ---------------------------------------------------------------------------

def _build_results_csv_fieldnames(source_names):
    fieldnames = list(_BASE_CSV_FIELDS)

    for metric_key in METRIC_META.keys():
        fieldnames.append(f"avg__{metric_key}")

    for source_name in source_names:
        for metric_key in METRIC_META.keys():
            fieldnames.append(f"{source_name}__{metric_key}")

    return fieldnames


def write_results_csv(csv_path, receiver_areas, band_info, materials_info, source_names):
    fieldnames = _build_results_csv_fieldnames(source_names)

    with csv_path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()

        for area in receiver_areas:
            area_name = area[RK.NAME]

            for receiver in area[RK.RECEIVERS]:
                world_position = receiver[RK.WORLD_POSITION]
                room_position = receiver[RK.POSITION]

                row = {
                    "area_name": area_name,
                    "receiver_id": receiver[RK.ID],
                    "band_key": band_info[RK.KEY],
                    "band_label": band_info[RK.LABEL],
                    "walls_material_key": materials_info[RK.WALLS][RK.KEY],
                    "walls_material_label": materials_info[RK.WALLS][RK.LABEL],
                    "floor_material_key": materials_info[RK.FLOOR][RK.KEY],
                    "floor_material_label": materials_info[RK.FLOOR][RK.LABEL],
                    "ceiling_material_key": materials_info[RK.CEILING][RK.KEY],
                    "ceiling_material_label": materials_info[RK.CEILING][RK.LABEL],
                    "world_x": world_position[0],
                    "world_y": world_position[1],
                    "world_z": world_position[2],
                    "room_x": room_position[0],
                    "room_y": room_position[1],
                    "room_z": room_position[2],
                }

                for metric_key, value in receiver[RK.AVG_METRICS].items():
                    row[f"avg__{metric_key}"] = value

                for source_name in source_names:
                    for metric_key, value in receiver[RK.PER_SOURCE_METRICS][source_name].items():
                        row[f"{source_name}__{metric_key}"] = value

                writer.writerow(row)

# ---------------------------------------------------------------------------
# Result payload builder
# ---------------------------------------------------------------------------

def build_results_dict(
    scene,
    simulation_info,
    band_info,
    materials_info,
    source_names,
    out_receiver_areas,
    csv_path,
):
    total_receivers = sum(
        area[RK.SUMMARY][RK.NUM_RECEIVERS]
        for area in out_receiver_areas
    )

    return {
        RK.STATUS: "ok",
        RK.ROOM: scene[SK.ROOM],
        RK.SOURCES: scene[SK.SOURCES],
        RK.SIMULATION: simulation_info,
        RK.BAND: band_info,
        RK.MATERIALS: materials_info,
        RK.SUMMARY: {
            RK.NUM_SOURCES: len(source_names),
            RK.NUM_RECEIVER_AREAS: len(out_receiver_areas),
            RK.NUM_TOTAL_RECEIVERS: total_receivers,
        },
        RK.SOURCE_NAMES: source_names,
        RK.RECEIVER_AREAS: out_receiver_areas,
        RK.CSV_PATH: str(csv_path),
    }