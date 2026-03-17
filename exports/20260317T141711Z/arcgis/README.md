# ArcGIS StoryMap Exports

Optimized for import into ArcGIS Online as hosted feature layers, then embedding into ArcGIS StoryMaps.

All files cover **all 4 operations** (True Promise 1–4), **55 attack waves**, Feb 2024 – Mar 2026.

## Files

### `arcgis_launch_sites.geojson`
**Point features** — 55 launch origins across Iran.

Each point represents a single attack wave's launch site. Properties include human-readable `wave_label` (e.g. "TP4 Wave 14 — Fattah Hypersonic Strike"), `operation_label`, `popup_summary` for ArcGIS pop-ups, and `timestamp_epoch` (Unix ms) for time slider animation. The `launch_generic` boolean indicates whether coordinates are an approximate regional centroid (`true`) or a specifically geolocated site (`false`).

**Suggested symbology:** Red markers, sized by `estimated_munitions_count`, colored by `operation_short`.

### `arcgis_targets.geojson`
**Point features** — 50 target/impact points across Israel, Jordan, UAE, Kuwait, Bahrain, Qatar, Saudi Arabia, and the Mediterranean.

Same property schema as launch sites. Five waves lack target coordinates (null geometry). The `target_generic` boolean distinguishes approximate city centroids from specifically geolocated impact sites.

**Suggested symbology:** Blue markers, shaped by target type (Israeli city vs. US base), colored by `operation_short`.

### `arcgis_trajectories.geojson`
**LineString features** — 50 straight-line arcs from launch site to target.

Each line connects one wave's launch origin to its target. Not flight paths — these are great-circle approximations for visualization. Properties match the point layers. Only waves with both launch and target coordinates are included (50 of 55).

**Suggested symbology:** Dashed lines, colored by `operation_short`, with arrow direction from launch → target.

### `arcgis_waves.csv`
**Flat CSV** — 55 rows, 32 columns. Fallback for drag-and-drop import into ArcGIS Online if GeoJSON upload has issues.

Contains `launch_lat`/`launch_lon` and `target_lat`/`target_lon` columns that ArcGIS can geocode on import. Only produces point data (no trajectory arcs). Same properties as the GeoJSON files.

## Key Properties (all files)

| Property | Type | Description |
|----------|------|-------------|
| `operation_label` | string | Full name, e.g. "True Promise 4 (Feb–Mar 2026)" |
| `operation_short` | string | Short code: TP1, TP2, TP3, TP4 |
| `wave_label` | string | Display title for pop-ups |
| `popup_summary` | string | Compact summary: time, payload, munitions, intercept rate, casualties |
| `timestamp_utc` | string | ISO 8601 timestamp |
| `timestamp_epoch` | integer | Unix epoch milliseconds — use for ArcGIS time slider |
| `conflict_day` | integer | Day number within the operation |
| `icon_type` | string | "launch", "target", or "trajectory" |

## Import Workflow

1. **ArcGIS Online → Content → New item → Your device**
2. Upload each `.geojson` file as a separate hosted feature layer
3. Create a **Web Map** and add all three layers
4. Enable the **time slider** using the `timestamp_epoch` field
5. Create a **StoryMap** and embed the web map in sidecar slides
