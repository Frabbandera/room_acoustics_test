"""
Shared metadata catalogs for the Room Acoustics repository.

The module defines project-wide catalogs for octave bands, acoustic metrics,
material presets, simulation engines, and ray-tracing defaults. It also
provides small helper functions to retrieve validated metadata entries and
to build enum items for Blender UI selectors.

This file contains no simulation logic. Its purpose is to keep shared
configuration centralized, readable, and consistent across frontend and backend
modules.
"""

# ---------------------------------------------------------------------------
# Catalog definitions
# ---------------------------------------------------------------------------

BAND_CATALOG = {
    "125": {
        "label": "125 Hz",
        "description": "125 Hz octave band",
    },
    "250": {
        "label": "250 Hz",
        "description": "250 Hz octave band",
    },
    "500": {
        "label": "500 Hz",
        "description": "500 Hz octave band",
    },
    "1000": {
        "label": "1000 Hz",
        "description": "1000 Hz octave band",
    },
    "2000": {
        "label": "2000 Hz",
        "description": "2000 Hz octave band",
    },
    "4000": {
        "label": "4000 Hz",
        "description": "4000 Hz octave band",
    },
}

METRIC_CATALOG = {
    "c50_db": {
        "label": "C50",
        "unit": "dB",
        "description": "Clarity at 50 ms",
    },
    "c80_db": {
        "label": "C80",
        "unit": "dB",
        "description": "Clarity at 80 ms",
    },
    "d50": {
        "label": "D50",
        "unit": "",
        "description": "Definition",
    },
    "spl_db": {
        "label": "SPL",
        "unit": "dB",
        "description": "Relative level derived from the RIR",
    },
}

MATERIAL_CATALOG = {
    "reflective_plaster": {
        "label": "Reflective Plaster",
        "description": "Rigid reflective wall",
        "absorption": {
            "125": 0.02,
            "250": 0.03,
            "500": 0.04,
            "1000": 0.05,
            "2000": 0.07,
            "4000": 0.08,
        },
        "scattering": 0.05,
    },
    "wood": {
        "label": "Wood",
        "description": "Wood",
        "absorption": {
            "125": 0.10,
            "250": 0.07,
            "500": 0.06,
            "1000": 0.07,
            "2000": 0.09,
            "4000": 0.10,
        },
        "scattering": 0.10,
    },
    "carpet": {
        "label": "Carpet",
        "description": "Carpet / rug",
        "absorption": {
            "125": 0.08,
            "250": 0.15,
            "500": 0.30,
            "1000": 0.45,
            "2000": 0.55,
            "4000": 0.65,
        },
        "scattering": 0.20,
    },
    "heavy_curtain": {
        "label": "Heavy Curtain",
        "description": "Heavy curtain",
        "absorption": {
            "125": 0.05,
            "250": 0.10,
            "500": 0.35,
            "1000": 0.55,
            "2000": 0.70,
            "4000": 0.70,
        },
        "scattering": 0.35,
    },
    "acoustic_ceiling": {
        "label": "Acoustic Ceiling",
        "description": "Sound-absorbing ceiling",
        "absorption": {
            "125": 0.30,
            "250": 0.60,
            "500": 0.80,
            "1000": 0.90,
            "2000": 0.80,
            "4000": 0.70,
        },
        "scattering": 0.25,
    },
    "generic_absorbent": {
        "label": "Generic Absorbent",
        "description": "Generic absorbent material",
        "absorption": {
            "125": 0.15,
            "250": 0.30,
            "500": 0.60,
            "1000": 0.75,
            "2000": 0.85,
            "4000": 0.85,
        },
        "scattering": 0.20,
    },
}

ENGINE_CATALOG = {
    "ISM_ONLY": {
        "label": "ISM Only",
        "description": "Use the pyroomacoustics image-source solver only",
    },
    "HYBRID_RT": {
        "label": "Hybrid RT",
        "description": "Use the pyroomacoustics hybrid image-source + ray-tracing solver",
    },
}

# ---------------------------------------------------------------------------
# Simulation defaults
# ---------------------------------------------------------------------------

RAY_TRACING_DEFAULTS = {
    "n_rays": 10000,
    "receiver_radius": 0.50,
    "hist_bin_size": 0.004,
    "energy_thres": 1.0e-7,
    "time_thres": 2.0,
}

def get_ray_tracing_defaults():
    return dict(RAY_TRACING_DEFAULTS)

# ---------------------------------------------------------------------------
# Catalog access helpers
# ---------------------------------------------------------------------------

def get_band_meta(band_key):
    if band_key not in BAND_CATALOG:
        raise KeyError(f"Invalid band key: {band_key}")
    return BAND_CATALOG[band_key]

def get_metric_meta(metric_key):
    if metric_key not in METRIC_CATALOG:
        raise KeyError(f"Invalid metric key: {metric_key}")
    return METRIC_CATALOG[metric_key]

def get_material_meta(material_key):
    if material_key not in MATERIAL_CATALOG:
        raise KeyError(f"Invalid material key: {material_key}")
    return MATERIAL_CATALOG[material_key]

def get_engine_meta(engine_key):
    if engine_key not in ENGINE_CATALOG:
        raise KeyError(f"Invalid simulation mode: {engine_key}")
    return ENGINE_CATALOG[engine_key]

# ---------------------------------------------------------------------------
# UI enum builders
# ---------------------------------------------------------------------------

def build_band_enum_items():
    return [
        (key, meta["label"], meta["description"])
        for key, meta in BAND_CATALOG.items()
    ]


def build_metric_enum_items():
    return [
        (key, meta["label"], meta["description"])
        for key, meta in METRIC_CATALOG.items()
    ]


def build_material_enum_items():
    return [
        (key, meta["label"], meta["description"])
        for key, meta in MATERIAL_CATALOG.items()
    ]


def build_engine_enum_items():
    return [
        (key, meta["label"], meta["description"])
        for key, meta in ENGINE_CATALOG.items()
    ]