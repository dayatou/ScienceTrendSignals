#!/usr/bin/env python3
import argparse
import csv
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

LOGGER = logging.getLogger("pre_author")
INVALID_TEXT = {"/", "-", "N/A", "n/a", "NA", "null", "NULL"}
ORG_COUNTRY_FALLBACKS = {
    "Institute of Robotics": "US",
    "Shanghai Artificial Intelligence Laboratory": "CN",
    "Kuaishou (China)": "CN",
    "UNC Lineberger Comprehensive Cancer Center": "US",
    "Moores Cancer Center": "US",
}


def setup_logging(level_name):
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def should_log_progress(index, total, every):
    return index == 1 or index == total or index % every == 0


def normalize_text(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in INVALID_TEXT:
        return None
    return text


def load_org_country_lookup(path: Path):
    # 使用 gis_org.csv 中已清洗的机构国家码，覆盖源数据里的噪声 country_code。
    if not path.exists():
        LOGGER.warning("Organization GIS file not found, skip country normalization: %s", path)
        return {}

    lookup = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            org_name = normalize_text(row.get("organization_name"))
            country_code = normalize_text(row.get("country_code"))
            if not org_name:
                continue
            if country_code:
                lookup[org_name] = country_code.upper()
                continue
            fallback_country_code = ORG_COUNTRY_FALLBACKS.get(org_name)
            if fallback_country_code:
                lookup[org_name] = fallback_country_code

    LOGGER.info("Loaded organization country normalization entries: %d", len(lookup))
    return lookup


def iter_records(input_path: Path):
    # 与 pre_org 保持一致：统一支持 JSON/JSONL 输入。
    if input_path.suffix.lower() == ".json":
        LOGGER.info("Loading JSON input: %s", input_path)
        with input_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict):
            yield payload
            return
        if isinstance(payload, list):
            total = len(payload)
            for idx, item in enumerate(payload, start=1):
                if should_log_progress(idx, total, 1000):
                    LOGGER.info("Read JSON records: %d/%d", idx, total)
                if isinstance(item, dict):
                    yield item
            return
        return

    LOGGER.info("Streaming JSONL input: %s", input_path)
    with input_path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                LOGGER.warning("Skip invalid JSON at line %d", line_no)
                continue
            if line_no % 100000 == 0:
                LOGGER.info("Read JSONL lines: %d", line_no)
            if isinstance(record, dict):
                yield record


def resolve_authorship(entry):
    # 兼容 authorships 的两种形态：数组 [name, country, org] / 对象字段。
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


def extract_author_history(input_path: Path, progress_every: int):
    LOGGER.info("Step 1/2: extracting author-year-organization history")
    # 复合键：作者 + 年份 + 机构。值里只保留国家码计数用于回填最常见国家。
    stats = defaultdict(lambda: {"country_codes": Counter()})

    record_count = 0
    skipped_year = 0
    skipped_entry = 0

    for record in iter_records(input_path):
        record_count += 1
        if record_count % progress_every == 0:
            LOGGER.info("Processed records: %d", record_count)

        publication_year = record.get("publication_year")
        if not isinstance(publication_year, int):
            try:
                publication_year = int(publication_year)
            except (TypeError, ValueError):
                skipped_year += 1
                continue

        authorships = record.get("authorships", [])
        if not isinstance(authorships, list):
            continue

        for idx, entry in enumerate(authorships, start=1):
            author_name, country_code, org_name = resolve_authorship(entry)
            if not author_name or not org_name:
                skipped_entry += 1
                continue

            # 这里故意按复合键去重，不做文章次数统计（后续脚本再做统计层）。
            key = (author_name, publication_year, org_name)
            bucket = stats[key]
            if country_code:
                bucket["country_codes"][country_code] += 1

    LOGGER.info(
        "Finished extraction: records=%d, composite_keys=%d, skipped_year=%d, skipped_entry=%d",
        record_count,
        len(stats),
        skipped_year,
        skipped_entry,
    )
    return stats


def build_rows(stats, org_country_lookup, progress_every: int):
    rows = []
    normalized_country_count = 0
    # 输出前排序，保证生成 CSV 稳定可复现（便于 diff）。
    sorted_keys = sorted(stats.keys(), key=lambda x: (x[1], x[0], x[2]))
    total = len(sorted_keys)

    for idx, key in enumerate(sorted_keys, start=1):
        author_name, publication_year, org_name = key
        bucket = stats[key]
        country_counter = bucket["country_codes"]
        country_code = country_counter.most_common(1)[0][0] if country_counter else ""
        normalized_country_code = org_country_lookup.get(org_name)
        if normalized_country_code and normalized_country_code != country_code:
            normalized_country_count += 1
            country_code = normalized_country_code

        rows.append(
            {
                "author_name": author_name,
                "publication_year": publication_year,
                "organization_name": org_name,
                "country_code": country_code,
            }
        )

        if should_log_progress(idx, total, progress_every):
            percent = (idx / total) * 100 if total else 100.0
            LOGGER.info(
                "Build row progress: %d/%d (%.1f%%) | last=%s | year=%s",
                idx,
                total,
                percent,
                author_name,
                publication_year,
            )

    LOGGER.info(
        "Applied organization-based country normalization to %d rows",
        normalized_country_count,
    )
    return rows


def write_csv(output_path: Path, rows):
    fieldnames = [
        "author_name",
        "publication_year",
        "organization_name",
        "country_code",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    LOGGER.info("Step 2/2: wrote %d rows to %s", len(rows), output_path)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate author-year-organization metadata CSV from paper records "
            "(unique key: author + publication_year + organization)."
        )
    )
    parser.add_argument(
        "--input",
        default="paperMerge.txt",
        help="Input JSON/JSONL file (default: paperMerge.txt)",
    )
    parser.add_argument(
        "--output",
        default="his_author.csv",
        help="Output CSV file (default: his_author.csv)",
    )
    parser.add_argument(
        "--org-gis",
        default="gis_org.csv",
        help="Organization GIS CSV used to normalize country_code (default: gis_org.csv)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=500,
        help="Log progress every N records/rows (default: 500)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.log_level)

    input_path = Path(args.input)
    output_path = Path(args.output)
    org_gis_path = Path(args.org_gis)
    progress_every = max(1, args.progress_every)

    LOGGER.info(
        "Start pre_author with input=%s output=%s org_gis=%s",
        input_path,
        output_path,
        org_gis_path,
    )
    if not input_path.exists():
        LOGGER.error("Input file not found: %s", input_path)
        return 1

    org_country_lookup = load_org_country_lookup(org_gis_path)
    stats = extract_author_history(input_path, progress_every=progress_every)
    rows = build_rows(
        stats,
        org_country_lookup=org_country_lookup,
        progress_every=progress_every,
    )
    write_csv(output_path, rows)
    LOGGER.info("Done: wrote %d composite records", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
