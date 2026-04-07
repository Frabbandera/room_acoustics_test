"""
Material helpers for the Room Acoustics backend.

The module provides small access helpers for material and band metadata
stored in the shared catalogs.

This file contains no simulation logic. Its purpose is to keep material
lookups centralized, readable, and consistent across the backend.
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

from shared.catalogs import (
    BAND_CATALOG,
    get_band_meta,
    get_material_meta,
)

# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

def get_band_label(band_key):
    return get_band_meta(band_key)["label"]


def get_material_label(material_key):
    return get_material_meta(material_key)["label"]

# ---------------------------------------------------------------------------
# Material property helpers
# ---------------------------------------------------------------------------

def get_material_absorption(material_key, band_key):
    material_meta = get_material_meta(material_key)

    if band_key not in BAND_CATALOG:
        raise KeyError(f"Invalid band key: {band_key}")

    return float(material_meta["absorption"][band_key])


def get_material_scattering(material_key):
    material_meta = get_material_meta(material_key)

    value = float(material_meta.get("scattering", 0.0))

    if value < 0.0 or value > 1.0:
        raise ValueError(
            f"Invalid scattering value for material {material_key}: {value}. "
            "The value must be in the range [0, 1]."
        )

    return value