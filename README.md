# EpiScope

This repository contains the synthetic EpiScope data pack and a lightweight prototype pipeline and D3 dashboard. The dashboard is a demo, not a complete implementation of every assignment requirement.

## Team

| Member | Student ID | Name |
|---|---|---|
| 1 | 0222210005101120 | Priyantu Das Antu |
| 2 | 0222210005101125 | Shuvo Shil |

## Dataset
The project uses synthetic data generated deterministically from the included data generator:

```bash
python generator/generate.py --sf 0.004 --seed 42
```

## Run the project

### Start the dashboard

The dashboard is a static demo. It needs Python 3 to serve the files, but no Python packages. The included synthetic dataset is ready to use.

1. Download or clone the project, then open a terminal in the project root (the directory containing this `README.md`).
2. Check that Python 3 is available:

   ```bash
   python --version
   ```

   On Windows, use `py --version` if the `python` command is not recognized.
3. Start a local web server from the project root:

   ```bash
   python -m http.server 8000 --bind 127.0.0.1
   ```

   On Windows, if `python` is not recognized, run:

   ```powershell
   py -m http.server 8000 --bind 127.0.0.1
   ```

4. Open <http://localhost:8000/dashboard/> in your browser.
5. Keep the terminal open while using the dashboard. Press `Ctrl+C` in that terminal to stop the server.

Run the server from the project root, not from `dashboard/`, so the page can load files from `data/synthetic`. If port 8000 is already in use, replace `8000` in the command and URL with another available port.

### Regenerate the synthetic dataset (optional)

The generated dataset is already included, so this is not needed to view the dashboard. To regenerate it, install the generator's Python dependencies and run the generator from the project root:

```bash
python -m pip install numpy pandas
python generator/generate.py --sf 0.004 --seed 42
```

On Windows, use `py -m pip` and `py generator/generate.py` if `python` is not recognized. This writes the generated files under `data/synthetic`.

### Build the optional gold tables

To run the prototype pipeline and write its Parquet summaries to `pipeline/gold/`, install its dependencies and run it from the project root:

```bash
python -m pip install pandas pyarrow
python pipeline/build_gold.py
```

On Windows, use `py -m pip` and `py pipeline/build_gold.py` if needed. This step is separate from starting the dashboard.

The dashboard presents:
- Synthetic encounter counts by disease, week, and district, with an illustrative four-week trend projection.
- A district-centroid bubble map based on approximate reference geography (not district boundary polygons).
- Seasonal disease heatmap, recent top-five signals, planning estimates, and an illustrative preparedness calendar.
- Data-quality flag counts for duplicate encounter IDs, invalid ages, and facility references.

The current dataset preview contains 64 reference districts, 640 facilities, and 99,392 unique encounter records. Forecasts, alert levels, resource estimates, and calendar actions are demonstrative and are not validated public-health guidance.

## Optional: build gold tables

```bash
python -m pip install pandas pyarrow
python pipeline/build_gold.py
```

This writes weekly alert and stock-summary Parquet files under `pipeline/gold/`. PySpark is listed for the larger assignment pipeline, but the current prototype gold builder uses pandas.

## Requirement traceability
- Synthetic data generation: `generator/generate.py`
- Prototype weekly/stock summaries: `pipeline/build_gold.py`
- Interactive demonstration dashboard: `dashboard/index.html`

## Not yet implemented
- Complete bronze/silver/gold lakehouse ingestion, quarantine, and lineage flow.
- Validated outbreak detection and forecast backtesting.
- Optimized resource allocation, full district-boundary map, and hidden incremental-drop validation.
- Final assignment report and recorded presentation/video.

## Video link
TBD

## AI usage
See `AI_USAGE.md`.
