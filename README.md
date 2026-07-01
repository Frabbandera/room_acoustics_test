cat > README.md << 'READMEEOF'
# BlenderAcoustics

An open-source room acoustic simulation and visualization tool built on top of Blender and [Pyroomacoustics](https://github.com/LCAV/pyroomacoustics). Model room geometry directly in Blender, simulate sound propagation, and visualize acoustic metrics as interactive heatmaps in the viewport.

Developed as part of the MAE Capstone Course at Politecnico di Milano.

## Features

- Room geometry with hybrid bounding-box ISM simulation, including sloped ceiling detection
- `ISM_ONLY` and `HYBRID_RT` (ISM + ray tracing) solver modes
- ISO 3382-1 clarity metrics: C50, C80, D50, relative SPL
- Zone-based furniture absorption modeling
- Color-coded, percentile-normalized heatmap visualization with legend
- Receiver marker and heatmap mesh overlay visualization inside Blender

## Installation

A dedicated Python environment is recommended, since the backend depends on **Pyroomacoustics**. This project has been run successfully with Pyroomacoustics 0.10.0 in a separate Conda environment.

```bash
conda create -n pra_test python=3.10
conda activate pra_test
conda install -c conda-forge pyroomacoustics=0.10.0 numpy scipy
```

You do not need to use this exact environment name, and the project folder does not need to live in any specific location. What matters is that:

- the backend dependencies are installed in the selected environment
- Blender's **Python Executable** field points to that environment's interpreter
- Blender's **Project Directory** field points to the root folder of this repository

Typical interpreter paths:

- Windows: `.../miniconda3/envs/pra_test/python.exe`
- macOS / Linux: `.../miniconda3/envs/pra_test/bin/python`

## Usage

BlenderAcoustics is used entirely from inside Blender. Every simulation follows the same steps below. Follow them in order the first time you use the tool; once you're familiar with the workflow you'll usually only touch the later steps for repeat runs on the same scene.

**Object naming matters.** The frontend discovers scene objects by name to know which one is the room, the sources, and the receiver areas. If you rename an object away from these conventions, the frontend won't recognize it any more.

### Step 1 — Launch Blender and open the project scene

Open Blender and load the scene file you want to simulate (e.g. `newtest.blend` shipped with the repository), or start a fresh scene if you want to build a room from scratch.

### Step 2 — Load the add-on script

BlenderAcoustics runs as a script inside Blender rather than as a packaged add-on, so you must load it each time you open Blender or reload the file:

1. Click the **Scripting** tab at the top of the Blender window (in the workspace tab bar, next to Layout / Modeling / Sculpting / etc.).
2. Open **`Blender Script.txt`** from the project folder in a text editor, and copy its full contents.
3. In the Scripting workspace's text editor, paste the copied script into a new text block.
4. With the script text active in the editor, click the **Run Script** button (▶ play icon) at the top-right of the text editor header, or press `Alt+P`.
5. If nothing seems to happen, open the System Console to check for errors:
   - **Windows**: `Window > Toggle System Console`
   - **macOS / Linux**: launch Blender from a terminal to see stdout/stderr there.
6. On success, a new **Room Acoustics** tab appears in the 3D Viewport's right-hand sidebar. If the sidebar is hidden, hover your mouse over the 3D Viewport and press `N` to open it, then click the **Room Acoustics** tab.

### Step 3 — Point Blender at the backend environment

In the Room Acoustics sidebar, set:

- **Project Directory** — the root folder of this repository (so the backend and `exchange/` folder can be located).
- **Python Executable** — the interpreter of the Conda/virtual environment where `pyroomacoustics` is installed (see [Installation](#installation)).

These fields need to be set each time you open the file, unless the `.blend` file was saved with these values already populated.

### Step 4 — Set up the room geometry

The room must be a single mesh object named **`RoomVolume`**. For ISM simulation, an area-weighted bounding box is automatically computed from this mesh: for flat ceilings the exact height is used, and for sloped ceilings an area-weighted average height is computed automatically — so the room can have a sloped or non-flat ceiling while the solver still receives a compatible representation. Internal obstacles are supported by joining the obstacle mesh with the `RoomVolume` mesh.

Build or import your room mesh, then rename it to `RoomVolume` in the Outliner (double-click its name to rename). If the room has internal obstacles (furniture, columns, structural elements) that should occlude sound geometrically, select the obstacle mesh first, then shift-select `RoomVolume` so it becomes the active object, and press `Ctrl+J` to join them.

### Step 5 — Place sources and receiver areas

Two families of objects are discovered by naming convention:

- **Sources** — any object named with the **`SRC_*`** prefix (e.g. `SRC_1`, `SRC_Main`). Every source must lie inside the room footprint and between floor and ceiling.
- **Receiver areas** — any mesh object named with the **`MAP_*`** prefix (e.g. `MAP_Main`). Each `MAP_*` object must be a mesh with exactly one horizontal face, must not be rotated, and all its vertices must lie inside the room footprint. The receiver grid is generated from a uniform spacing value and clipped against the `MAP_*` polygon.

**Auto-creation.** If the scene has no source or receiver area yet, the add-on can auto-create a default `SRC_1` and generate `MAP_Main` from the room footprint via the sidebar operator.

**Manual placement.** Select the object in the 3D Viewport:
- `G` grabs it, `G` then `Z` constrains movement to the vertical axis (useful for setting listening or source height).
- Numeric input works too: type `G`, `Z`, `2`, `Enter` to move exactly 2 metres up.
- Use the Item panel (`N` panel → Item tab → Location) to set coordinates precisely.
- Resize a `MAP_*` object using the Item panel's Dimensions fields so it covers the room area you care about.

### Step 6 — (Optional) Add furniture for zone-based absorption

BlenderAcoustics models furniture through a 3×3 zone-based absorption grid on the floor. To add a piece of furniture:

1. Add or import a mesh into the scene.
2. Rename it in the Outliner to one of the recognized furniture presets: `sofa`, `bookshelf`, or `window`.
3. Position it on the floor where it belongs. The add-on automatically determines which of the 3×3 floor zones its centroid falls into.

At simulation time, each furniture object contributes its preset acoustic material (e.g. heavy curtain for `sofa`, wood for `bookshelf`, reflective plaster for `window`) to the absorption coefficient seen by receivers inside its zone. No further configuration is required.

### Step 7 — Configure the simulation parameters

Still in the Room Acoustics sidebar, review and set the simulation parameters before you run:

- **Octave band** — the current implementation simulates **one octave band per run**; select the band from the dropdown.
- **Surface materials** — assign acoustic material presets per surface class (floor, walls, ceiling). Material assignment is currently global by surface class, not per-face.
- **Solver mode** — choose either:
  - **`ISM_ONLY`** — deterministic image-source method only. No ray-tracing branch; material scattering is not used computationally in this mode. Simpler, more stable execution path.
  - **`HYBRID_RT`** — adds Pyroomacoustics ray tracing on top of ISM. Accepts RT-specific parameters (`n_rays`, `receiver_radius`, `hist_bin_size`, `energy_thres`, `time_thres`) and supports deterministic runs through a fixed random seed. Automatically falls back to `ISM_ONLY` if hybrid execution fails. The UI warns when `HYBRID_RT` is requested with `max_order > 3`.
- **Reflection order (`max_order`)** — a minimum of **10** is strongly recommended; lower values produce degenerate C50/C80/D50 values because the late-energy integrals collapse to zero.
- **Source power** — the sound power of the source in dB SWL (default **120 dB**), used for absolute SPL calibration.

### Step 8 — Run the simulation

Click **Run Acoustic Test** in the sidebar. Under the hood this does the following:

1. The frontend validates `RoomVolume`, source, and receiver-area geometry, and serializes the scene (room definition, simulation settings, selected band, materials, source positions, and generated receiver coordinates) to `exchange/scene.json`.
2. Blender launches the backend as a subprocess using the configured Python interpreter, effectively running:
```bash
   python backend/run_simulation.py --scene exchange/scene.json --out exchange/results.json
```
3. The backend loads and validates the scene file, dispatches the selected solver, and computes C50, C80, D50, and relative SPL per receiver, per source, and as a source average (arithmetic mean of per-source values — not a physically combined multi-source RIR).
4. Results are written to `exchange/results.json` (full structured output, including execution metadata, resolved materials, fallback status, and requested/used random seed and ray-tracing configuration) and `exchange/results.csv` (flattened, one row per receiver).

**If the simulation appears stuck or produces no output**, check the System Console (see Step 2) for backend errors — most issues at this stage come from a missing or misnamed scene object, an invalid material selection, an unmet `RoomVolume` constraint, or the Python Executable not pointing at an environment with Pyroomacoustics installed.

### Step 9 — View and explore results

Two visualization modes are available in the sidebar:

- **Receiver markers** — creates an empty object in a dedicated collection for each receiver position, storing the metric value as an object custom property.
- **Heatmap overlay** — creates a mesh overlay above the selected receiver area, colored using a generated heatmap material. Colours range from **blue** (low value) through cyan, green, and yellow to **red** (high value), with percentile-based normalization (5th–95th percentile) so subtle spatial variations remain visible. A colour legend shows the metric name, minimum, and maximum values.

To inspect raw numbers directly, open `exchange/results.csv` in any spreadsheet application — each row includes the receiver area name, receiver id, band and material metadata, world-space and room-space coordinates, source-averaged metric values, and per-source metric values.

## Project structure

```text
room_acoustics_test/
├── backend/
│   ├── run_simulation.py       # single backend entry point
│   ├── materials.py             # band/material metadata lookups
│   ├── setup/
│   │   ├── scene_validation.py  # validates exported payload structure and value ranges
│   │   ├── room_setup.py         # resolves simulation configuration from the scene
│   │   ├── room_builder.py        # builds and populates the Pyroomacoustics room
│   │   └── room_geometry.py        # converts RoomVolume into an area-weighted bounding box for Pyroomacoustics walls
│   ├── solvers/
│   │   ├── solver_ism.py         # image-source-only execution
│   │   └── solver_hybrid_rt.py    # hybrid ISM + ray-tracing execution, with ISM_ONLY fallback
│   └── postprocessing/
│       ├── metrics.py             # computes C50, C80, D50, relative SPL
│       ├── multi_area.py           # flattens/regroups receiver areas
│       └── results.py               # writes CSV and assembles JSON results payload
├── frontend/
│   ├── blender_scene/
│   │   ├── geometry.py            # room/mapping geometry validation and extraction
│   │   └── scene_export.py         # scene-to-JSON export logic
│   └── blender_ui/
│       ├── properties.py          # project settings, simulation options, display settings
│       ├── panels.py               # sidebar layout in the 3D view
│       ├── operators.py             # run/export operator and helpers
│       ├── scene_state.py            # UI-facing scene inspection helpers
│       ├── helpers.py                 # UI labels and status formatting
│       └── visualization.py           # marker and heatmap generation inside Blender
├── shared/
│   ├── catalogs.py                # octave bands, metrics, material presets, engine labels, RT defaults
│   ├── scene_keys.py               # scene payload keys
│   └── result_keys.py               # result payload keys
├── exchange/
│   ├── scene.json                 # exported scene payload
│   ├── results.json                # structured simulation output
│   └── results.csv                  # flattened tabular output
├── blender_bridge_test.py          # Blender entry point — registers properties, operators, panels
├── Blender Script.txt               # script pasted into the Scripting tab to load the add-on
└── newtest.blend                    # reference test scene
```

## Current limitations

The codebase is well-structured but still a constrained prototype:

1. **The bounding-box ISM approximation has geometric limits.** While sloped ceilings are supported via an area-weighted average height, very complex non-convex or multi-volume spaces may not be fully captured by the bounding-box representation used for simulation.
2. **Only one octave band is simulated per run.** The selected band is chosen in the UI and passed through the entire pipeline.
3. **Material assignment is global by surface class.** There is no per-face material mapping yet.
4. **The metric set is limited to C50, C80, D50, and relative SPL.**
5. **Source averaging is metric-wise, not physically combined.** The displayed source average is the arithmetic mean of per-source metric values, not a physically combined multi-source RIR.
6. **The frontend depends on exact Blender naming conventions** (`RoomVolume`, `SRC_*`, `MAP_*`).
7. **Validation is currently limited to one room configuration** against Pachyderm Acoustics, at 500 Hz with ISM order 10.

## Validation

Validated against Pachyderm Acoustics at 500 Hz (ISM order 10): D50 and C80 agree within ~1 JND, C50 within ~2 dB. SPL shows a larger gap, consistent with the known tendency of the bounding-box ISM approximation to underestimate total reflected energy relative to full geometric ray tracing.

## Possible future extensions

- full geometry-aware acoustic computation (e.g. FEM or FDTD solvers) for complex non-convex geometries, beyond the current bounding-box approximation
- support for per-face material assignment
- multi-band batch execution in a single run
- additional room-acoustic parameters (e.g. reverberation-time metrics: EDT, T20, T30)
- directivity-aware sources
- a physically combined multi-source RIR option, distinct from display-only averaging
- asynchronous / incremental backend execution
- automated tests for scene validation and result generation
- packaging of backend dependencies for easier reproducibility

## Authors

Ferrão Benedito, Bandera Francesco, Pappalardo Antonio — DEIB, Politecnico di Milano
Supervisors: Prof. Ilario Mazzieri, Prof. Luca Commanduci, Prof. Gerardo Cicalese, Prof. Alberto Bernardini

## Repository

<https://github.com/Frabbandera/room_acoustics_test>
READMEEOF
