#!/usr/bin/env python3
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import shapefile

INVALID_TEXT = {"", "/", "-", "N/A", "n/a", "NA", "null", "NULL"}


def normalize_text(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in INVALID_TEXT:
        return None
    return text


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def load_org_lookup(path: Path):
    lookup = {}
    country_codes = set()
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            org_name = normalize_text(row.get("organization_name"))
            lat = row.get("latitude")
            lon = row.get("longitude")
            if not org_name or not lat or not lon:
                continue
            country_code = normalize_text(row.get("country_code")) or ""
            lookup[org_name] = {
                "country_code": country_code,
                "latitude": float(lat),
                "longitude": float(lon),
            }
            if country_code:
                country_codes.add(country_code)
    return lookup, country_codes


def resolve_authorship(entry):
    author_name = None
    country_code = None
    org_name = None

    if isinstance(entry, list):
        if len(entry) >= 1:
            author_name = normalize_text(entry[0])
        if len(entry) >= 2:
            cc = normalize_text(entry[1])
            country_code = cc.upper() if cc else None
        if len(entry) >= 3:
            org_name = normalize_text(entry[2])
    elif isinstance(entry, dict):
        author_name = normalize_text(
            entry.get("author_name") or entry.get("author") or entry.get("name")
        )
        cc = normalize_text(entry.get("country_code") or entry.get("country"))
        country_code = cc.upper() if cc else None
        org_name = normalize_text(
            entry.get("institution_name")
            or entry.get("institution")
            or entry.get("organization")
            or entry.get("org")
        )

    return author_name, country_code, org_name


def author_order_group(author_order: int):
    if author_order <= 3:
        return str(author_order)
    return "4+"


def build_author_points(input_path: Path, org_lookup):
    rows = []
    year_min = None
    year_max = None
    missing_orgs = Counter()

    with input_path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            record = json.loads(line)
            title = normalize_text(record.get("title")) or "(Untitled)"
            work_id = normalize_text(record.get("id")) or ""
            doi = ""
            ids = record.get("ids")
            if isinstance(ids, dict):
                doi = normalize_text(ids.get("doi")) or ""
            if not doi:
                doi = normalize_text(record.get("doi")) or ""

            try:
                publication_year = int(record.get("publication_year"))
            except (TypeError, ValueError):
                continue

            authorships = record.get("authorships")
            if not isinstance(authorships, list):
                continue

            year_min = publication_year if year_min is None else min(year_min, publication_year)
            year_max = publication_year if year_max is None else max(year_max, publication_year)

            for index, entry in enumerate(authorships, start=1):
                author_name, country_code, org_name = resolve_authorship(entry)
                if not author_name or not org_name:
                    continue

                org_data = org_lookup.get(org_name)
                if not org_data:
                    missing_orgs[org_name] += 1
                    continue

                final_country_code = org_data["country_code"] or country_code or ""
                rows.append(
                    {
                        "work_id": work_id,
                        "title": title,
                        "publication_year": publication_year,
                        "author_name": author_name,
                        "author_order": index,
                        "author_order_group": author_order_group(index),
                        "organization_name": org_name,
                        "country_code": final_country_code,
                        "latitude": org_data["latitude"],
                        "longitude": org_data["longitude"],
                        "doi": doi,
                    }
                )

            if line_no % 50000 == 0:
                print(f"processed records: {line_no}")

    meta = {
        "record_count": len(rows),
        "year_min": year_min,
        "year_max": year_max,
        "missing_org_count": sum(missing_orgs.values()),
        "missing_org_examples": [
            {"organization_name": org_name, "count": count}
            for org_name, count in missing_orgs.most_common(20)
        ],
    }
    return rows, meta


def write_author_points_csv(rows, output_path: Path):
    fieldnames = [
        "work_id",
        "title",
        "publication_year",
        "author_name",
        "author_order",
        "author_order_group",
        "organization_name",
        "country_code",
        "latitude",
        "longitude",
        "doi",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def shape_record_to_feature(shape_record, fields, property_names):
    values = shape_record.record.as_dict()
    properties = {name: values.get(name) for name in property_names}
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": shape_record.shape.__geo_interface__,
    }


def convert_populated_places(shp_path: Path, output_path: Path, country_codes):
    reader = shapefile.Reader(str(shp_path))
    property_names = [
        "FEATURECLA",
        "NAME",
        "NAMEASCII",
        "ADM0NAME",
        "ADM0_A3",
        "ADM1NAME",
        "LATITUDE",
        "LONGITUDE",
        "POP_MAX",
    ]
    features = []
    for shape_record in reader.iterShapeRecords():
        values = shape_record.record.as_dict()
        if values.get("ISO_A2") not in country_codes:
            continue
        features.append(shape_record_to_feature(shape_record, reader.fields[1:], property_names))
    payload = {"type": "FeatureCollection", "features": features}
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return len(features)


def convert_admin_boundaries(shp_path: Path, output_path: Path, country_codes):
    reader = shapefile.Reader(str(shp_path))
    property_names = [
        "name",
        "name_alt",
        "type_en",
        "postal",
        "iso_a2",
        "adm0_a3",
        "geonunit",
    ]
    features = []
    for shape_record in reader.iterShapeRecords():
        values = shape_record.record.as_dict()
        if values.get("iso_a2") not in country_codes:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {name: values.get(name) for name in property_names},
                "geometry": shape_record.shape.__geo_interface__,
            }
        )
    payload = {"type": "FeatureCollection", "features": features}
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return len(features)


def write_meta(meta, output_path: Path):
    output_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate frontend CSV and GeoJSON assets for the author history map."
    )
    parser.add_argument("--input", default="paperMerge.txt")
    parser.add_argument("--org-gis", default="gis_org.csv")
    parser.add_argument("--public-dir", default="vue/public")
    parser.add_argument(
        "--admin-shp",
        default="ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp",
    )
    parser.add_argument(
        "--places-shp",
        default="ne_110m_populated_places/ne_110m_populated_places.shp",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input)
    org_gis_path = Path(args.org_gis)
    public_dir = Path(args.public_dir)
    ensure_dir(public_dir)

    org_lookup, country_codes = load_org_lookup(org_gis_path)
    print(f"loaded org coordinates: {len(org_lookup)}")
    print(f"countries with data: {len(country_codes)}")

    rows, meta = build_author_points(input_path, org_lookup)
    author_csv = public_dir / "author_map_points.csv"
    write_author_points_csv(rows, author_csv)
    print(f"wrote author points: {author_csv} ({len(rows)} rows)")

    places_geojson = public_dir / "ne_110m_populated_places.geojson"
    places_count = convert_populated_places(Path(args.places_shp), places_geojson, country_codes)
    print(f"wrote populated places: {places_geojson} ({places_count} features)")

    admin_geojson = public_dir / "ne_10m_admin_1_states_provinces.geojson"
    admin_count = convert_admin_boundaries(Path(args.admin_shp), admin_geojson, country_codes)
    print(f"wrote admin boundaries: {admin_geojson} ({admin_count} features)")

    meta.update(
        {
            "organization_count_with_coordinates": len(org_lookup),
            "admin_feature_count": admin_count,
            "populated_place_feature_count": places_count,
        }
    )
    meta_path = public_dir / "author_map_meta.json"
    write_meta(meta, meta_path)
    print(f"wrote meta: {meta_path}")


if __name__ == "__main__":
    main()
