# ScienceTrendSignals Map Module

[中文说明 / Chinese version](./README.zh.md) | [Project README](../README.md) | [Technical README](../README-tech.md)

This directory contains the spatial-processing pipeline and the GIS front-end of ScienceTrendSignals.

Repository-level research findings and empirical summaries are documented at the root:

- [Project README](../README.md)
- [Project README, Chinese](../README.zh.md)

Repository-level technical structure is documented here:

- [Technical README](../README-tech.md)
- [Technical README, Chinese](../README-tech.zh.md)

## Module Scope

The `map/` directory performs three tasks:

- geocode and normalize institution locations
- generate map-ready CSV and GeoJSON assets
- render these assets in a Vue + Leaflet interface

## Main Files

### Spatial preprocessing

- `pre_org.py`
  organization extraction, normalization, geocoding, and maintenance of `gis_org.csv`
- `pre_org_resolve_not_found.py`
  recovery workflow for unresolved institutions
- `pre_org_merge_resolved.py`
  merge-back workflow for recovered geocoding results
- `pre_author.py`
  author-year-organization history generation
- `generate_author_map_assets.py`
  generation of GIS front-end assets

### Data files

- `gis_org.csv`
  main organization GIS table
- `gis_org_not_found.csv`
  unresolved organizations after the initial geocoding pass
- `gis_org_not_found_resolved.csv`
  resolved organizations from the recovery workflow
- `his_author.csv`
  author-year-organization history table

### Front-end files

- `vue/src/App.vue`
  main GIS application logic
- `vue/src/main.js`
  Vue bootstrap entry
- `vue/src/style.css`
  front-end styling
- `vue/vite.config.js`
  build and deployment configuration

## Generated Front-End Assets

The GIS front-end uses the following generated files in `vue/public/`:

- `author_map_points.csv`
- `author_map_meta.json`
- `ne_10m_admin_1_states_provinces.geojson`
- `ne_110m_populated_places.geojson`

Generation script:

- `generate_author_map_assets.py`

## Workflow

### 1. Build or update organization GIS data

```bash
python3 pre_org.py
python3 pre_org_resolve_not_found.py
python3 pre_org_merge_resolved.py
```

### 2. Build author history

```bash
python3 pre_author.py
```

### 3. Generate GIS front-end assets

```bash
python3 generate_author_map_assets.py
```

### 4. Run the front-end

```bash
cd vue
npm install
npm run dev
```

Production build:

```bash
npm run build
```

## Front-End Functions

The front-end provides:

- year-range brushing
- world-map point display
- author-order color encoding
- institution-label or author-label display
- optional GIS overlays
- linked record dock
- SVG export

## Related Documentation

- [Project README](../README.md)
- [Project README, Chinese](../README.zh.md)
- [Technical README](../README-tech.md)
- [Technical README, Chinese](../README-tech.zh.md)
- [Chinese map-module README](./README.zh.md)

[中文说明 / Chinese version](./README.zh.md) | [Project README](../README.md) | [Technical README](../README-tech.md)
