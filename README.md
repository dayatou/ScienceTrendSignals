# ScienceTrendSignals

[中文说明](./README.zh.md) | [Technical README](./README-tech.md) | [技术说明（中文）](./README-tech.zh.md)

ScienceTrendSignals is a research-analysis project for characterizing a scientific field along four dimensions:

- semantic structure
- temporal evolution
- strategic position
- geographic distribution

The repository integrates corpus analysis, spatial preprocessing, and GIS presentation within a single workflow.

## Research Scope

The project addresses the following analytical objects:

- thematic clusters in the corpus
- hierarchical relations among topics and subfields
- temporal variation in topic volume and recency
- strategic roles such as anchor, bridge, adjacent area, and frontier
- geographic concentration of authors and institutions
- temporal shifts in national, metropolitan, and institutional centers of activity

## Scientific Significance

The project combines three analytical layers that are commonly treated separately:

- semantic mapping of research topics
- strategic interpretation of topic maturity and frontier potential
- spatial mapping of author-affiliation records

This integration supports field-level interpretation rather than document-level description alone.

## Strategic Relevance

The project supports:

- identification of stable core domains
- identification of adjacent or enabling domains
- detection of bridge domains linking separate knowledge regions
- detection of high-growth or frontier-like directions
- localization of geographic centers associated with visible growth

## Current GIS Dataset

The current front-end GIS dataset contains:

- record-level author-affiliation points: `79,566`
- unique works: `17,118`
- unique authors: `40,855`
- unique author-year combinations: `65,028`
- geocoded organizations: `4,614`
- distinct coordinate pairs: `3,759`
- countries and regions represented by country code: `92`
- time span: `1982–2025`

The front-end also uses:

- administrative boundary features: `2,869`
- populated-place features: `131`

## Empirical Findings From The Current GIS Layer

### Temporal change

The visible record volume is concentrated in recent years.

- `1982–1986` combined: `2` records, `1` work, `2` authors
- `2021–2025` combined: `40,603` records, `7,696` works, `33,541` authors

Highest yearly record counts:

1. `2023`: `10,078`
2. `2022`: `8,958`
3. `2021`: `8,555`
4. `2025`: `7,100`
5. `2020`: `7,001`

Highest yearly work counts:

1. `2023`: `1,906`
2. `2021`: `1,776`
3. `2022`: `1,748`
4. `2020`: `1,488`
5. `2025`: `1,250`

Highest yearly author counts:

1. `2023`: `8,135`
2. `2022`: `7,337`
3. `2021`: `6,852`
4. `2025`: `6,011`
5. `2020`: `5,547`

### Historical stages

The current GIS record can be partitioned into four broad periods:

- `1982–1999`: sparse distribution, mainly the United States and Western Europe
- `2000–2009`: first major international expansion, with Japan as a visible East Asian pole
- `2010–2019`: dense North America-Europe-East Asia network
- `2020–2025`: maximum overall volume, with China and the United States as the dominant poles

### Geographic leadership shift

The yearly record leader is:

- `US` from `1982` through `2020`
- `CN` from `2021` through `2025`

Active country or region counts by year show expansion in geographic breadth:

- `1982`: `1`
- `2000`: `8`
- `2019`: `60`
- `2022`: `62`
- `2023`: `65`

### Spatial concentration

Top countries by record count:

1. `CN`: `21,253`
2. `US`: `18,770`
3. `IT`: `4,592`
4. `DE`: `4,493`
5. `GB`: `4,003`
6. `JP`: `3,673`
7. `FR`: `2,948`
8. `KR`: `2,908`
9. `CA`: `2,338`
10. `CH`: `1,724`

The top 10 countries account for `83.8%` of all record-level points.

Top countries by unique works:

1. `US`: `5,191`
2. `CN`: `4,741`
3. `GB`: `1,451`
4. `DE`: `1,360`
5. `IT`: `1,268`

Top countries by unique authors:

1. `CN`: `11,318`
2. `US`: `10,358`
3. `DE`: `2,361`
4. `GB`: `2,170`
5. `JP`: `2,010`

Top countries by unique organizations:

1. `CN`: `882`
2. `US`: `849`
3. `FR`: `306`
4. `GB`: `279`
5. `JP`: `277`

### Metropolitan hotspots

The top 20 coordinate pairs account for `27.3%` of all records.

Major hotspots include:

1. Beijing (`39.9075, 116.39723`): `1,914`
2. Shanghai (`31.2222, 121.4581`): `1,721`
3. London (`51.50853, -0.12574`): `1,608`
4. Hong Kong / Chinese University of Hong Kong (`22.4137, 114.2099`): `1,296`
5. Seoul (`37.5660, 126.9784`): `1,284`
6. Tokyo (`35.6895, 139.6917`): `1,250`
7. Cambridge/Boston (`42.3751, -71.10561`): `1,194`
8. Singapore (`1.28967, 103.85007`): `1,141`
9. Harbin (`45.75, 126.65`): `1,128`
10. Baltimore / Johns Hopkins (`39.3302, -76.62185`): `943`

### Institution-level concentration

Top organizations by record count:

1. `Chinese University of Hong Kong`: `1,296`
2. `Harbin Institute of Technology`: `1,003`
3. `Johns Hopkins University`: `943`
4. `Italian Institute of Technology`: `914`
5. `Shanghai Jiao Tong University`: `909`
6. `Imperial College London`: `881`
7. `Technical University of Munich`: `854`
8. `ETH Zurich`: `809`
9. `Tsinghua University`: `772`
10. `Deutsches Zentrum für Luft- und Raumfahrt e. V. (DLR)`: `768`

The top 20 organizations account for `19.3%` of all records.

### Author-order structure

Record counts by author-order group:

- `1st author`: `16,887`
- `2nd author`: `16,347`
- `3rd author`: `13,970`
- `4+ author`: `32,362`

Relative shares:

- `1st`: `21.2%`
- `2nd`: `20.5%`
- `3rd`: `17.6%`
- `4+`: `40.7%`

## Document Structure

The root-level documentation is partitioned as follows:

- `README.md`
  Research significance, strategic relevance, and empirical findings in English
- `README.zh.md`
  Research significance, strategic relevance, and empirical findings in Chinese
- `README-tech.md`
  Technical architecture and code-structure description in English
- `README-tech.zh.md`
  Technical architecture and code-structure description in Chinese

Map-specific operational documentation remains in:

- [map/README.md](./map/README.md)
- [map/README.zh.md](./map/README.zh.md)

[中文说明](./README.zh.md) | [Technical README](./README-tech.md) | [技术说明（中文）](./README-tech.zh.md)
