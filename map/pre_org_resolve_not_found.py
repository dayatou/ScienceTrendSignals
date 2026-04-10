#!/usr/bin/env python3
import csv
from pathlib import Path

import pre_org


INPUT_PATH = Path("gis_org_not_found.csv")
OUTPUT_PATH = Path("gis_org_not_found_resolved.csv")
CACHE_PATH = Path(".org_geocode_cache.json")


def main():
    cache = pre_org.load_cache(CACHE_PATH)
    with INPUT_PATH.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    fieldnames = list(rows[0].keys()) + [
        "latitude",
        "longitude",
        "geocode_status",
        "geocode_display_name",
        "geocode_source",
        "resolved_at",
    ]

    resolved = 0
    out_rows = []

    for idx, row in enumerate(rows, start=1):
        result, _ = pre_org.resolve_org(
            org_name=row["organization_name"],
            country_code=row["country_code"],
            cache=cache,
            user_agent="pre_org.py (academic GIS incremental geocoder)",
            sleep_seconds=0.1,
            refresh_days=90,
            not_found_retry_days=0,
            request_timeout=15,
            min_request_interval=0.1,
            max_retries=1,
        )

        merged = dict(row)
        merged["latitude"] = result.get("lat", "")
        merged["longitude"] = result.get("lon", "")
        merged["geocode_status"] = result.get("status", "")
        merged["geocode_display_name"] = result.get("display_name", "")
        merged["geocode_source"] = result.get("source", "")
        merged["resolved_at"] = result.get("checked_at", "")
        out_rows.append(merged)

        if result.get("status") == "ok":
            resolved += 1

        with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(out_rows)

        if idx == 1 or idx == len(rows) or idx % 10 == 0:
            print(
                f"progress {idx}/{len(rows)} resolved={resolved} "
                f"last={row['organization_name']} status={result.get('status')}",
                flush=True,
            )

    pre_org.save_cache(CACHE_PATH, cache)
    print(f"done resolved={resolved} total={len(rows)} output={OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
