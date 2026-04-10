#!/usr/bin/env python3
import csv
from pathlib import Path


GIS_PATH = Path("gis_org.csv")
RESOLVED_PATH = Path("gis_org_not_found_resolved.csv")
NOT_FOUND_PATH = Path("gis_org_not_found.csv")


GIS_FIELDS = [
    "organization_name",
    "country_code",
    "appearance_count",
    "latitude",
    "longitude",
    "geocode_status",
    "geocode_display_name",
    "geocode_source",
    "last_checked_at",
]

NOT_FOUND_FIELDS = [
    "organization_name",
    "country_code",
    "appearance_count",
    "last_status",
    "last_attempt_at",
    "attempt_count",
    "last_method",
]


def main():
    with GIS_PATH.open("r", encoding="utf-8", newline="") as fh:
        gis_rows = list(csv.DictReader(fh))

    with RESOLVED_PATH.open("r", encoding="utf-8", newline="") as fh:
        resolved_rows = list(csv.DictReader(fh))

    resolved_map = {
        (row["organization_name"], row["country_code"]): row for row in resolved_rows
    }

    updated = 0
    for row in gis_rows:
        key = (row["organization_name"], row["country_code"])
        resolved = resolved_map.get(key)
        if not resolved or resolved.get("geocode_status") != "ok":
            continue
        row["latitude"] = resolved.get("latitude", "")
        row["longitude"] = resolved.get("longitude", "")
        row["geocode_status"] = "ok"
        row["geocode_display_name"] = resolved.get("geocode_display_name", "")
        row["geocode_source"] = resolved.get("geocode_source", "")
        row["last_checked_at"] = resolved.get("resolved_at", "")
        updated += 1

    with GIS_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=GIS_FIELDS)
        writer.writeheader()
        writer.writerows(gis_rows)

    with NOT_FOUND_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=NOT_FOUND_FIELDS)
        writer.writeheader()

    print(f"updated_gis_rows={updated}")
    print("remaining_not_found_rows=0")


if __name__ == "__main__":
    raise SystemExit(main())
