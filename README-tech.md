# ScienceTrendSignals Technical README

[中文技术说明](./README-tech.zh.md) | [Project README](./README.md) | [项目说明（中文）](./README.zh.md)

This document records the technical structure of the repository.

## Repository Architecture

The repository contains three connected code layers:

- repository-level corpus analysis in `src/`
- spatial preprocessing in `map/`
- interactive GIS presentation in `map/vue/src/`

The pipeline order is:

1. corpus alignment and cleaning
2. semantic and strategic topic analysis
3. institution geocoding and author-affiliation normalization
4. GIS asset generation
5. interactive map rendering and export

## Layer 1: Repository-Level `src/`

Main files:

- `src/stage0-13realouputs.py`
- `src/suppl_figtabel_datagen.py`
- `src/suppl_tables.py`

### `stage0-13realouputs.py`

This file implements the staged analysis pipeline.

Stage functions:

1. Stage 0: align encoded TSV and metadata JSON/JSONL
2. Stage 1: extract core fields, reconstruct abstracts, filter language, deduplicate
3. Stage 2: rebuild cleaned text with keywords
4. Stage 3: compute TF-IDF + SVD embeddings
5. Stage 4: cluster documents with MiniBatchKMeans
6. Stage 5: generate cluster-level names and summaries
7. Stage 6: assign semantic hierarchy and fine areas
8. Stage 7: compute cluster and domain time trends
9. Stage 8: generate a 2D knowledge map with UMAP
10. Stage 9: estimate domain coverage and time-horizon state
11. Stage 10: assign structural roles
12. Stage 11: estimate frontier potential
13. Stage 12: compute anchor alignment and frontier potential
14. Stage 13: place clusters into a 3×3 strategic matrix

Primary output directory:

- `realoutputs/`

### `suppl_figtabel_datagen.py`

Function:

- read staged outputs from `realoutputs/`
- generate supplementary CSV files for figures and tables

Primary output directory:

- `suppl_data/`

### `suppl_tables.py`

Function:

- render selected supplementary tables from CSV to PNG

Primary output directory:

- `visualization_suppl/`

## Layer 2: Spatial Processing In `map/`

Main files:

- `map/pre_org.py`
- `map/pre_org_resolve_not_found.py`
- `map/pre_org_merge_resolved.py`
- `map/pre_author.py`
- `map/generate_author_map_assets.py`

### `pre_org.py`

Function:

- extract organizations
- normalize organization strings
- geocode institutions
- maintain the main organization GIS table
- maintain unresolved-organization tracking

Primary outputs:

- `map/gis_org.csv`
- `map/gis_org_not_found.csv`

### `pre_org_resolve_not_found.py`

Function:

- reprocess unresolved organizations using additional matching and fallback logic

### `pre_org_merge_resolved.py`

Function:

- merge recovered geocoding results into the main organization GIS table

### `pre_author.py`

Function:

- generate author-year-organization history records
- normalize countries using the organization GIS table

Primary output:

- `map/his_author.csv`

### `generate_author_map_assets.py`

Function:

- join paper authorships with geocoded organizations
- generate front-end point records
- generate front-end metadata
- subset and export supporting GeoJSON layers

Primary outputs:

- `map/vue/public/author_map_points.csv`
- `map/vue/public/author_map_meta.json`
- `map/vue/public/ne_10m_admin_1_states_provinces.geojson`
- `map/vue/public/ne_110m_populated_places.geojson`

## Layer 3: GIS Front-End In `map/vue/src/`

Main files:

- `map/vue/src/App.vue`
- `map/vue/src/main.js`
- `map/vue/src/style.css`

### `App.vue`

Function:

- load CSV and GeoJSON assets
- maintain year-range selection state
- compute filtered records and summary statistics
- render author-affiliation points
- switch labels between institution and author modes
- toggle GIS overlays
- maintain the linked record dock
- export the current map view as SVG

### `main.js`

Function:

- bootstrap and mount the Vue application

### `style.css`

Function:

- define layout and styling for the map, panels, timeline, legends, and responsive states

## Front-End Assets

The front-end consumes:

- `author_map_points.csv`
- `author_map_meta.json`
- `ne_10m_admin_1_states_provinces.geojson`
- `ne_110m_populated_places.geojson`

Main front-end dependencies:

- Vue 3
- Vite
- Leaflet
- PapaParse

## Deployment Notes

The project is configured for GitHub Pages deployment from the root `docs/` directory.

Current deployment conditions:

- Vite base path: `/ScienceTrendSignals/`
- built assets must be copied into `docs/`
- public data requests use BASE_URL-aware paths

## Documentation Partition

- `README.md` and `README.zh.md`
  research significance, strategic relevance, and empirical results
- `README-tech.md` and `README-tech.zh.md`
  technical architecture and code structure
- `map/README.md` and `map/README.zh.md`
  map-module workflow and front-end operation

[中文技术说明](./README-tech.zh.md) | [Project README](./README.md) | [项目说明（中文）](./README.zh.md)
