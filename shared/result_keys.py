"""
Shared result-payload keys for the Room Acoustics repository.

The module defines the string constants used to build and read result
dictionaries across the backend, export layer, and Blender frontend.

This file contains no logic. Its purpose is to keep result-field names
centralized, readable, and consistent across the project.
"""

# ---------------------------------------------------------------------------
# Top-level result sections
# ---------------------------------------------------------------------------

STATUS = "status"

ROOM = "room"
SOURCES = "sources"
BAND = "band"
MATERIALS = "materials"
SIMULATION = "simulation"
SUMMARY = "summary"

# ---------------------------------------------------------------------------
# Scene and input context
# ---------------------------------------------------------------------------

NAME = "name"
ID = "id"
KEY = "key"
LABEL = "label"
UNIT = "unit"

POSITION = "position"
WORLD_POSITION = "world_position"

SOURCE_NAMES = "source_names"
RECEIVER_AREAS = "receiver_areas"
RECEIVERS = "receivers"
MAPPING = "mapping"

# ---------------------------------------------------------------------------
# Surface and material payload keys
# ---------------------------------------------------------------------------

WALLS = "walls"
FLOOR = "floor"
CEILING = "ceiling"

ABSORPTION = "absorption"
SCATTERING = "scattering"

# ---------------------------------------------------------------------------
# Simulation execution metadata
# ---------------------------------------------------------------------------

REQUESTED_ENGINE = "requested_engine"
EXECUTED_ENGINE = "executed_engine"
WARNING_MESSAGE = "warning_message"

RANDOM_SEED_REQUESTED = "random_seed_requested"
RANDOM_SEED_USED = "random_seed_used"

FALLBACK_ACTIVE = "fallback_active"

SCENE_MAX_ORDER_REQUESTED = "scene_max_order_requested"
EFFECTIVE_MAX_ORDER_USED = "effective_max_order_used"

RT_CONFIG_REQUESTED = "rt_config_requested"
RT_CONFIG_USED = "rt_config_used"

N_RAYS = "n_rays"
RECEIVER_RADIUS = "receiver_radius"
HIST_BIN_SIZE = "hist_bin_size"
ENERGY_THRES = "energy_thres"
TIME_THRES = "time_thres"

SAMPLE_RATE_HZ = "sample_rate_hz"

# ---------------------------------------------------------------------------
# Metric payload keys
# ---------------------------------------------------------------------------

PER_SOURCE_METRICS = "per_source_metrics"
AVG_METRICS = "avg_metrics"

AVG_METRIC_SUMMARIES = "avg_metric_summaries"
PER_SOURCE_METRIC_SUMMARIES = "per_source_metric_summaries"

MIN_VALUE = "min_value"
MAX_VALUE = "max_value"
MEAN_VALUE = "mean_value"

# ---------------------------------------------------------------------------
# Summary and receiver layout
# ---------------------------------------------------------------------------

NUM_SOURCES = "num_sources"
NUM_RECEIVER_AREAS = "num_receiver_areas"
NUM_TOTAL_RECEIVERS = "num_total_receivers"
NUM_RECEIVERS = "num_receivers"

# ---------------------------------------------------------------------------
# Output artifact keys
# ---------------------------------------------------------------------------

CSV_PATH = "csv_path"
