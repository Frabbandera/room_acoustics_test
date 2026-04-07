# room_acoustics_test

`room_acoustics_test` is a Blender + Python prototype for room-acoustic simulation and result visualization.

The current implementation exports a simplified room model from Blender, runs a simulation backend built around **Pyroomacoustics**, computes room-acoustic metrics from the generated room impulse responses (RIRs), and visualizes the results back in Blender as markers and heatmap overlays.

## What the project currently does

- Validates a room model in Blender through a dedicated `RoomVolume` object.
- Exports a normalized scene payload to `exchange/scene.json`.
- Runs a backend simulation through a single CLI entry point.
- Supports two backend execution modes:
  - `ISM_ONLY`
  - `HYBRID_RT`
- Computes per-source and source-averaged metrics for receiver grids.
- Writes structured outputs to:
  - `exchange/results.json`
  - `exchange/results.csv`
- Visualizes the selected metric in Blender using:
  - empty markers for receiver points
  - a colored heatmap mesh overlay

## General workflow

1. **Model the room in Blender** using a mesh named `RoomVolume`.
2. **Place sources** as Blender objects named `SRC_*`.
3. **Create receiver areas** as mesh objects named `MAP_*`, or generate `MAP_Main` automatically from the room footprint.
4. **Configure materials, simulation mode, band, and display settings** in the Blender sidebar.
5. **Export and run** the backend from Blender.
6. **Compute RIR-based metrics** for every receiver and source.
7. **Write results** to JSON and CSV.
8. **Render the selected metric** back in Blender as markers and/or a heatmap.

## Repository structure

```text
room_acoustics_test/
├── backend/
│   ├── __init__.py
│   ├── materials.py
│   ├── run_simulation.py
│   ├── postprocessing/
│   │   ├── __init__.py
│   │   ├── metrics.py
│   │   ├── multi_area.py
│   │   └── results.py
│   ├── setup/
│   │   ├── __init__.py
│   │   ├── room_builder.py
│   │   ├── room_geometry.py
│   │   ├── room_setup.py
│   │   └── scene_validation.py
│   └── solvers/
│       ├── __init__.py
│       ├── solver_hybrid_rt.py
│       └── solver_ism.py
├── frontend/
│   ├── __init__.py
│   ├── blender_scene/
│   │   ├── __init__.py
│   │   ├── geometry.py
│   │   └── scene_export.py
│   └── blender_ui/
│       ├── __init__.py
│       ├── helpers.py
│       ├── operators.py
│       ├── panels.py
│       ├── properties.py
│       ├── scene_state.py
│       └── visualization.py
├── shared/
│   ├── __init__.py
│   ├── catalogs.py
│   ├── result_keys.py
│   └── scene_keys.py
├── exchange/
│   ├── scene.json
│   ├── results.json
│   └── results.csv
├── blender_bridge_test.py
├── test_scene.blend
└── test_scene.blend1
```

## Architecture

### Frontend (`frontend/`)

The Blender side is split into two subpackages.

#### `frontend/blender_scene/`

This package is responsible for scene-side extraction and export logic:

- validation of the `RoomVolume` geometry
- extraction of the simplified room definition
- validation of source placement
- generation of receiver grids from `MAP_*` meshes
- serialization of the scene payload sent to the backend

Key files:

- `geometry.py`: room and mapping geometry validation/extraction
- `scene_export.py`: scene-to-JSON export logic

#### `frontend/blender_ui/`

This package contains the Blender UI and visualization layer:

- custom properties
- panels
- operators
- scene-state helpers
- UI formatting helpers
- result visualization helpers

Key files:

- `properties.py`: project settings, simulation options, display settings
- `panels.py`: sidebar layout in the 3D view
- `operators.py`: run/export operator and helper operators
- `scene_state.py`: UI-facing scene inspection helpers
- `helpers.py`: UI labels and status formatting helpers
- `visualization.py`: marker and heatmap generation inside Blender

#### Blender bootstrap

- `blender_bridge_test.py` is the minimal Blender entry point used to register the custom properties, operators, and panels.

### Backend (`backend/`)

The backend is organized around a single orchestrator and a few focused packages.

#### Entry point

- `run_simulation.py`

This is the single backend entry point. It:

- loads `scene.json`
- validates the exported payload
- resolves the requested simulation mode
- optionally seeds Pyroomacoustics for deterministic hybrid runs
- dispatches the selected solver
- writes `results.json` and `results.csv`

#### `backend/setup/`

Shared setup logic for building the simulation state:

- `scene_validation.py`: validates the exported payload structure and value ranges
- `room_setup.py`: resolves common simulation configuration from the scene
- `room_builder.py`: builds and populates the Pyroomacoustics room
- `room_geometry.py`: converts the prismatic room into Pyroomacoustics walls

#### `backend/solvers/`

Solver-specific execution logic:

- `solver_ism.py`: image-source-only execution
- `solver_hybrid_rt.py`: hybrid image-source + ray-tracing execution, with fallback to `ISM_ONLY` if hybrid execution fails

#### `backend/postprocessing/`

RIR-based metric extraction and output serialization:

- `metrics.py`: computes `C50`, `C80`, `D50`, and relative `SPL`
- `multi_area.py`: flattens receiver areas for simulation and rebuilds grouped outputs
- `results.py`: writes CSV output and assembles the final JSON results payload

#### `backend/materials.py`

Small backend-side helpers for looking up band and material metadata from the shared catalogs.

### Shared (`shared/`)

Shared constants and catalogs used by both frontend and backend:

- `catalogs.py`: octave bands, metrics, material presets, engine labels, and RT defaults
- `scene_keys.py`: scene payload keys
- `result_keys.py`: result payload keys

## Simulation modes

### `ISM_ONLY`

This mode builds a Pyroomacoustics room using the image-source solver only.

Characteristics:

- deterministic geometry-based image-source simulation
- no ray-tracing branch
- material scattering is **not** used computationally in this mode
- simpler and more stable execution path

### `HYBRID_RT`

This mode enables Pyroomacoustics ray tracing in addition to the image-source branch.

Characteristics:

- uses a hybrid ISM + ray-tracing workflow
- accepts RT-specific parameters:
  - `n_rays`
  - `receiver_radius`
  - `hist_bin_size`
  - `energy_thres`
  - `time_thres`
- supports deterministic runs through a fixed random seed
- emits a warning in the UI because the hybrid path should be reviewed carefully
- automatically falls back to `ISM_ONLY` if hybrid execution fails

The UI also warns when `HYBRID_RT` is requested with `max_order > 3`, matching the caution embedded in the current code.

## Acoustic metrics currently supported

The project currently computes the following receiver-level metrics from each RIR:

- `C50`
- `C80`
- `D50`
- `SPL` (relative level derived from total RIR energy)

These metrics are computed:

- **per source**
- **per receiver**
- and also as a **source average** for display purposes

## Output files

### `exchange/scene.json`

The Blender-exported simulation payload.

It contains:

- room geometry definition
- simulation settings
- selected frequency band
- material configuration
- source positions
- grouped receiver areas with generated receiver coordinates

### `exchange/results.json`

The main structured simulation output.

It contains:

- execution metadata
- selected band information
- resolved material information
- global summary counts
- source names
- receiver area results
- per-area metric summaries
- per-receiver per-source metrics
- source-averaged metrics
- path to the CSV export

The simulation metadata also stores:

- requested engine
- executed engine
- warning message
- fallback status
- requested / used random seed
- requested / used ray-tracing configuration

### `exchange/results.csv`

A flattened tabular export with one row per receiver.

Each row includes:

- receiver area name
- receiver id
- band metadata
- material metadata
- world-space coordinates
- room-space coordinates
- source-averaged metric values
- per-source metric values

## Blender visualization

The frontend can visualize simulation results directly inside Blender.

Two visualization modes are currently implemented:

### Receiver markers

Creates empties in a dedicated collection for each receiver position and stores the metric value as object custom properties.

### Heatmap overlay

Creates a mesh overlay above the selected receiver area and colors it using a generated heatmap material.

## Current room-model assumptions

The current implementation is intentionally strict and supports a simplified room model.

### `RoomVolume` assumptions

The room must be a mesh object named **`RoomVolume`** and it must satisfy all of the following:

- it must be a closed manifold mesh
- it must not be rotated
- it must contain exactly two Z levels
- it must represent a vertical prism
- it must have exactly one floor face
- it must have exactly one ceiling face
- the floor and ceiling must share the same XY footprint
- the footprint must be convex
- each side wall must correspond to exactly one footprint edge

### Source assumptions

- sources are discovered by the `SRC_*` naming convention
- every source must lie inside the room footprint and between floor and ceiling

### Receiver-area assumptions

- receiver areas are discovered by the `MAP_*` naming convention
- each `MAP_*` object must be a mesh with exactly one horizontal face
- receiver areas must not be rotated
- all receiver-area vertices must lie inside the room footprint
- the receiver grid is generated from a uniform spacing value and clipped against the `MAP_*` polygon

### Coordinate convention

The exported room-space coordinates currently preserve **world X/Y** and only normalize **Z** relative to the floor level.

## Current limitations

The current codebase is already well-structured, but it is still a constrained prototype. Important limitations include:

1. **Only simplified prismatic rooms are supported.**
   Arbitrary non-convex rooms, sloped ceilings, multi-volume spaces, and internal obstacles are not supported.

2. **Only one octave band is simulated per run.**
   The selected band is chosen in the UI and passed through the entire pipeline.

3. **Material assignment is global by surface class.**
   Walls, floor, and ceiling each get one selected material preset; there is no per-face material mapping yet.

4. **The metric set is limited.**
   The current backend computes only `C50`, `C80`, `D50`, and relative `SPL`.

5. **Source averaging is metric-wise, not wave-physically combined.**
   The displayed “Source Average” is the arithmetic mean of per-source metric values, not a physically combined multi-source RIR.

6. **The frontend depends on Blender naming conventions.**
   The workflow currently relies on exact object-name prefixes and a fixed `RoomVolume` object name.

7. **There is no environment/package manifest yet.**
   The repository currently lacks a `requirements.txt`, `pyproject.toml`, or Conda environment file.

## Possible future extensions

Natural next steps suggested by the current codebase are:

- support for more general room geometries
- support for per-face material assignment
- multi-band batch execution in a single run
- additional room-acoustic parameters such as reverberation-time-related metrics
- directivity-aware sources and binaural receiver handling
- better distinction between physical multi-source combination and display-only averaging
- asynchronous / incremental backend execution
- richer export formats and plotting/report utilities
- packaging of the backend dependencies for easier reproducibility
- automated tests for scene validation and result generation

## Practical usage notes

The current prototype is typically run from Blender, while the simulation backend is executed with a separate Python interpreter selected in the UI.

A practical setup is:

- keep the project folder anywhere you want (for example on the Desktop, in a workspace folder, or inside a Git clone)
- install the backend dependencies in a dedicated Python environment
- point Blender to that environment through the `Python Executable` field

### Recommended environment setup

A dedicated environment is recommended because the backend depends on **Pyroomacoustics**, and in practice this project has been run successfully with **Pyroomacoustics 0.10.0** installed in a separate Conda environment.

Example with Miniconda / Conda:

```bash
conda create -n pra_test python=3.10
conda activate pra_test
conda install -c conda-forge pyroomacoustics=0.10.0 numpy scipy
```

You do not need to use the exact same environment name, and the project folder does not need to live in any specific location. What matters is that:

- the backend dependencies are installed in the selected environment
- `Python Executable` points to the interpreter of that environment
- `Project Directory` points to the root folder of this repository

Typical interpreter paths are for example:

- Windows: `.../miniconda3/envs/pra_test/python.exe`
- macOS / Linux: `.../miniconda3/envs/pra_test/bin/python`

### Blender-side setup

To run the prototype from Blender:

1. Open the project scene or your own test `.blend` file in Blender.
2. Register `blender_bridge_test.py`.
3. In the Room Acoustics sidebar, set:
   - `Project Directory` to the root folder of this repository
   - `Python Executable` to the Python interpreter of the environment where `pyroomacoustics` is installed
4. Ensure the scene contains:
   - one valid `RoomVolume`
   - at least one `SRC_*` object
   - at least one `MAP_*` area, or generate `MAP_Main`
5. Choose materials, simulation mode, band, and visualization options.
6. Run **Run Acoustic Test**.

When the operator is executed, Blender exports the scene to the `exchange/` folder and launches the backend as a subprocess using the configured interpreter.

The backend command is effectively:

```bash
python backend/run_simulation.py --scene exchange/scene.json --out exchange/results.json
```

In the current implementation, `scene.json`, `results.json`, and `results.csv` are expected to live inside the project's `exchange/` directory, so the selected `Project Directory` should always be the repository root.