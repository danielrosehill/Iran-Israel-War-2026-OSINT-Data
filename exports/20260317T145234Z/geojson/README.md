# GeoJSON Exports

Standard GeoJSON FeatureCollections for use in any GIS tool: QGIS, Mapbox, Leaflet, kepler.gl, deck.gl, Google Earth, Felt, Datawrapper.

All files cover **all 4 operations** (True Promise 1–4), **55 attack waves**, Feb 2024 – Mar 2026.

## Files

### `waves_launch_sites.geojson`
**Point features** — 55 launch sites across Iran (all 55 have coordinates).

Properties include operation code, wave number, wave ID, codenames (English/Farsi), payload description, munitions counts, interception rate, casualties, and `generic_location` flag.

### `waves_targets.geojson`
**Point features** — 55 target entries, 50 with coordinates (5 have null geometry where target coordinates are unknown).

Same property schema as launch sites. Covers Israeli cities, military bases, US/coalition installations across the Gulf region.

### `waves_combined.geojson`
**Combined layer** — 110 features (55 launch + 55 target). Each feature has a `layer` property ("launch_site" or "target") for filtering/symbology.

Use this file when you want both layers in a single import. Filter on the `layer` property to style them differently.

## Difference from ArcGIS Exports

These are lightweight GeoJSON files with core wave properties. The `arcgis/` versions add display-friendly labels (`wave_label`, `popup_summary`), epoch timestamps for time slider, and trajectory LineStrings. Use these GeoJSON files for general-purpose GIS work; use the ArcGIS versions specifically for ArcGIS Online/StoryMap.
