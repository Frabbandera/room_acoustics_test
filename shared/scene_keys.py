"""
Shared scene-payload keys for the Room Acoustics repository.

The module defines the string constants used to build and read scene
dictionaries across the Blender export layer and simulation backend.

This file contains no logic. Its purpose is to keep scene-field names
centralized, readable, and consistent across the project.
"""

# ---------------------------------------------------------------------------
# Top-level scene sections
# ---------------------------------------------------------------------------

ROOM = "room"
SIMULATION = "simulation"
MATERIALS = "materials"
SOURCES = "sources"
RECEIVER_AREAS = "receiver_areas"

# ---------------------------------------------------------------------------
# Scene and input context
# ---------------------------------------------------------------------------

BAND = "band"
KEY = "key"
NAME = "name"
ID = "id"

POSITION = "position"
WORLD_POSITION = "world_position"

# ---------------------------------------------------------------------------
# Room geometry keys
# ---------------------------------------------------------------------------

FLOOR_POLYGON = "floor_polygon"
HEIGHT = "height"
Z_FLOOR = "z_floor"
GEOMETRY_MODE = "geometry_mode"
SOURCE_OBJECT_NAME = "source_object_name"

# ---------------------------------------------------------------------------
# Material keys
# ---------------------------------------------------------------------------

WALLS = "walls"
FLOOR = "floor"
CEILING = "ceiling"

MATERIAL_DETAILS = "material_details"
ABSORPTION = "absorption"
SCATTERING = "scattering"

# ---------------------------------------------------------------------------
# Simulation keys
# ---------------------------------------------------------------------------

ENGINE = "engine"
USE_FIXED_RANDOM_SEED = "use_fixed_random_seed"
RANDOM_SEED = "random_seed"

RAY_TRACING = "ray_tracing"
N_RAYS = "n_rays"
RECEIVER_RADIUS = "receiver_radius"
HIST_BIN_SIZE = "hist_bin_size"
ENERGY_THRES = "energy_thres"
TIME_THRES = "time_thres"

FS = "fs"
MAX_ORDER = "max_order"
AIR_ABSORPTION = "air_absorption"

# ---------------------------------------------------------------------------
# Receiver area keys
# ---------------------------------------------------------------------------

MAPPING = "mapping"
SPACING = "spacing"
NUM_X = "num_x"
NUM_Y = "num_y"
NUM_RECEIVERS = "num_receivers"

WORLD_Z = "world_z"
AREA_WIDTH = "area_width"
AREA_DEPTH = "area_depth"
POLYGON = "polygon"

RECEIVERS = "receivers"