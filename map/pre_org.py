#!/usr/bin/env python3
import argparse
import csv
import difflib
import json
import logging
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

LOGGER = logging.getLogger("pre_org")
INVALID_TEXT = {"", "/", "-", "N/A", "n/a", "NA", "null", "NULL"}
LAST_REQUEST_TS = 0.0

# 主表：机构维度GIS数据，既可首次创建，也可后续增量更新。
CSV_FIELDNAMES = [
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

NOT_FOUND_FIELDNAMES = [
    "organization_name",
    "country_code",
    "appearance_count",
    "last_status",
    "last_attempt_at",
    "attempt_count",
    "last_method",
]

COUNTRY_CODE_TO_NAME = {
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "CA": "Canada",
    "CN": "China",
    "JP": "Japan",
    "KR": "South Korea",
    "IN": "India",
    "AU": "Australia",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "CH": "Switzerland",
    "AT": "Austria",
    "BE": "Belgium",
    "IE": "Ireland",
    "PT": "Portugal",
    "PL": "Poland",
    "CZ": "Czechia",
    "HU": "Hungary",
    "SG": "Singapore",
    "HK": "Hong Kong",
    "TW": "Taiwan",
    "BR": "Brazil",
    "MX": "Mexico",
    "AR": "Argentina",
    "CL": "Chile",
    "ZA": "South Africa",
    "TR": "Turkey",
    "IL": "Israel",
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "TH": "Thailand",
    "MY": "Malaysia",
    "VN": "Vietnam",
    "ID": "Indonesia",
    "KZ": "Kazakhstan",
    "PH": "Philippines",
    "GR": "Greece",
    "MA": "Morocco",
    "NZ": "New Zealand",
    "EG": "Egypt",
    "PK": "Pakistan",
    "RO": "Romania",
    "RU": "Russia",
    "UA": "Ukraine",
    "IR": "Iran",
    "IQ": "Iraq",
}

COUNTRY_NAME_TO_CODE = {
    name.upper(): code for code, name in COUNTRY_CODE_TO_NAME.items()
}
COUNTRY_NAME_TO_CODE.update(
    {
        "UNITED STATES OF AMERICA": "US",
        "USA": "US",
        "U S A": "US",
        "U S": "US",
        "UK": "GB",
        "U K": "GB",
    }
)

ORG_ALIAS_HINTS = {
    "Amsterdam UMC Location VUmc": ("VUmc", "NL"),
    "Azienda Socio Sanitaria Territoriale Santi Paolo e Carlo": (
        "ASST Santi Paolo e Carlo",
        "IT",
    ),
    "Center for Research and Advanced Studies of the National Polytechnic Institute": (
        "Cinvestav",
        "MX",
    ),
    "Center for Scientific Research and Higher Education at Ensenada": (
        "CICESE",
        "MX",
    ),
    "Centre de Recherche Inria Bordeaux - Sud-Ouest": ("Inria Bordeaux", "FR"),
    "Centre de recherche Inria Lille - Nord Europe": ("Inria Lille", "FR"),
    "Institute of Plant and Microbial Biology,Academia Sinica": (
        "Institute of Plant and Microbial Biology Academia Sinica",
        "TW",
    ),
    "Rio de Janeiro Federal Institute of Education,Science and Technology": (
        "Federal Institute of Rio de Janeiro",
        "BR",
    ),
    "Wellcome/Cancer Research UK Gurdon Institute": ("Gurdon Institute", "GB"),
    "Zero to Three": ("ZERO TO THREE", "US"),
    "Osaka Medical Center for Cancer and Cardiovascular Diseases": (
        "Osaka International Cancer Institute",
        "JP",
    ),
    "Southern California University for Professional Studies": (
        "California Southern University",
        "US",
    ),
}

ORG_MANUAL_RESOLUTION_HINTS = {
    "Center for Research and Telecommunication Experimentation for Networked Communities": {
        "mode": "geocode_query",
        "query": "CREATE NET / FBK, 56d Via alla Cascata, Trento, Italy",
        "country_code": "IT",
    },
    "Centre de Recherche en Acquisition et Traitement de l'Image pour la Santé": {
        "mode": "copy_existing",
        "target": "Université Claude Bernard Lyon 1",
    },
    "Consejo Nacional de Humanidades,Ciencias y Tecnologías": {
        "mode": "geocode_query",
        "query": "Av. Insurgentes Sur 1582, Benito Juarez, Mexico City, Mexico",
        "country_code": "MX",
    },
    "Deleted Institution": {
        "mode": "geocode_query",
        "query": "Barcelona, Spain",
        "country_code": "ES",
    },
    "European Centre for Living Technology": {
        "mode": "geocode_query",
        "query": "Venice, Italy",
        "country_code": "IT",
    },
    "European Neuroendocrine Tumor Society": {
        "mode": "geocode_query",
        "query": "Langenbeck-Virchow-Haus Berlin",
        "country_code": "DE",
    },
    "Institut des Sciences Cognitives Marc Jeannerod": {
        "mode": "geocode_query",
        "query": "Bron, France",
        "country_code": "FR",
    },
    "Laboratoire Images,signaux et systèmes intelligents": {
        "mode": "copy_existing",
        "target": "Paris-Est Sup",
    },
    "Laboratoire d’Imagerie Biomédicale": {
        "mode": "copy_existing",
        "target": "Shenzhen University",
    },
    "Max Planck School Matter to Life": {
        "mode": "geocode_query",
        "query": "Jahnstrasse 29, 69120 Heidelberg, Germany",
        "country_code": "DE",
    },
    "Milano University Press": {
        "mode": "geocode_query",
        "query": "Milan, Italy",
        "country_code": "IT",
    },
    "NSWC Indian Head": {
        "mode": "geocode_query",
        "query": "Indian Head, Maryland, United States",
        "country_code": "US",
    },
    "Osaka Medical Center for Cancer and Cardiovascular Diseases": {
        "mode": "geocode_query",
        "query": "1-3-3 Nakamichi, Higashinari-ku, Osaka 537-8511, Japan",
        "country_code": "JP",
    },
    "Pain and Rehabilitation Medicine": {
        "mode": "copy_existing",
        "target": "Ruijin Hospital",
    },
    "Rutgers Sexual and Reproductive Health and Rights": {
        "mode": "geocode_query",
        "query": "Arthur van Schendelstraat 696, Utrecht, Netherlands",
        "country_code": "NL",
    },
    "Sirius University of Science and Technology": {
        "mode": "geocode_query",
        "query": "Sochi, Russia",
        "country_code": "RU",
    },
    "Southern California University for Professional Studies": {
        "mode": "geocode_query",
        "query": "Chandler, Arizona, United States",
        "country_code": "US",
    },
    "State Key Laboratory of Mechanical System and Vibration": {
        "mode": "copy_existing",
        "target": "Shanghai Jiao Tong University",
    },
    "State Key Laboratory of Medicinal Chemical Biology": {
        "mode": "copy_existing",
        "target": "Nankai University",
    },
    "State Key Laboratory of New Ceramics and Fine Processing": {
        "mode": "copy_existing",
        "target": "Beijing Institute of Technology",
    },
    "State Key Laboratory of Nonlinear Mechanics": {
        "mode": "copy_existing",
        "target": "Chinese Academy of Sciences",
    },
    "State Key Laboratory of Oncology in South China": {
        "mode": "copy_existing",
        "target": "Sun Yat-sen University Cancer Center",
    },
    "State Key Laboratory of Robotics": {
        "mode": "geocode_query",
        "query": "Shenyang, Liaoning, China",
        "country_code": "CN",
    },
    "State Key Laboratory of Robotics and Systems": {
        "mode": "copy_existing",
        "target": "Harbin Institute of Technology",
    },
    "State Key Laboratory of Supramolecular Structure and Materials": {
        "mode": "copy_existing",
        "target": "Jilin University",
    },
    "State Key Laboratory of Synthetical Automation for Process Industries": {
        "mode": "copy_existing",
        "target": "Northeastern University",
    },
    "State Key Laboratory of Tribology": {
        "mode": "copy_existing",
        "target": "Tsinghua University",
    },
    "State Key Laboratory of Turbulence and Complex Systems": {
        "mode": "copy_existing",
        "target": "Peking University",
    },
    "State Key Laboratory of Virtual Reality Technology and Systems": {
        "mode": "copy_existing",
        "target": "Beihang University",
    },
    "Swedish e-Science Research Centre": {
        "mode": "geocode_query",
        "query": "Stockholm, Sweden",
        "country_code": "SE",
    },
    "Swiss Distance University Institute": {
        "mode": "geocode_query",
        "query": "Schinerstrasse 18, 3900 Brig, Switzerland",
        "country_code": "CH",
    },
    "Taylor Geospatial Institute": {
        "mode": "copy_existing",
        "target": "Saint Louis University",
    },
    "Tianjin Polytechnic University": {
        "mode": "geocode_query",
        "query": "Tianjin Polytechnic University, Tianjin, China",
        "country_code": "CN",
    },
    "U.S. Air Force Research Laboratory Aerospace Systems Directorate": {
        "mode": "geocode_query",
        "query": "Wright-Patterson Air Force Base, Ohio, United States",
        "country_code": "US",
    },
    "UCLA Jonsson Comprehensive Cancer Center": {
        "mode": "geocode_query",
        "query": "10833 Le Conte Ave, Los Angeles, CA 90024, United States",
        "country_code": "US",
    },
    "Universidade Estadual do Piau": {
        "mode": "geocode_query",
        "query": "Universidade Estadual do Piaui, Teresina, Brazil",
        "country_code": "BR",
    },
    "University Hospitals Bristol and Weston NHS Foundation Trust": {
        "mode": "geocode_query",
        "query": "Marlborough Street, Bristol BS1 3NU, United Kingdom",
        "country_code": "GB",
    },
    "University of Maryland Marlene and Stewart Greenebaum Comprehensive Cancer Center": {
        "mode": "geocode_query",
        "query": "22 S Greene Street, Baltimore, MD 21201, United States",
        "country_code": "US",
    },
    "Università degli Studi del Piemonte Orientale “Amedeo Avogadro”": {
        "mode": "geocode_query",
        "query": "Via Duomo 6, 13100 Vercelli, Italy",
        "country_code": "IT",
    },
    "Vietnam Military Medical University": {
        "mode": "geocode_query",
        "query": "Hanoi, Vietnam",
        "country_code": "VN",
    },
}


# Extension point:
# Add new geocoding source functions with signature:
#   func(org_name, country_code, user_agent, request_timeout, min_request_interval, max_retries) -> dict | None
# Returned dict for success should include: lat, lon, display_name, source.


def setup_logging(level_name):
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def now_utc_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def should_log_progress(index, total, every):
    return index == 1 or index == total or index % every == 0


def normalize_text(value):
    if value is None:
        return None
    text = str(value).strip()
    if text in INVALID_TEXT:
        return None
    return text


def normalize_name_for_match(text):
    lowered = str(text).lower()
    cleaned = re.sub(r"\([^)]*\)", " ", lowered)
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_country_hint(org_name):
    text = normalize_text(org_name) or ""
    for part in re.findall(r"\(([^)]{2,80})\)", text):
        normalized = re.sub(r"[^A-Za-z]+", " ", part).strip().upper()
        if not normalized:
            continue
        code = COUNTRY_NAME_TO_CODE.get(normalized)
        if code:
            return code
    return None


def effective_country_code(org_name, country_code):
    hint = extract_country_hint(org_name)
    if hint:
        return hint
    cc = normalize_text(country_code)
    return cc.upper() if cc else None


def strip_country_hint(org_name):
    text = normalize_text(org_name) or ""
    return re.sub(r"\(([^)]{2,80})\)", " ", text).strip(" ,;-")


def name_variants(org_name):
    # 机构名规范化变体，用于提高检索命中率（去括号、去部门后缀、截断副标题等）。
    variants = []
    base = normalize_text(org_name)
    if not base:
        return variants

    def add_variant(v):
        vv = normalize_text(v)
        if vv and vv not in variants:
            variants.append(vv)

    add_variant(base)
    add_variant(strip_country_hint(base))
    add_variant(re.sub(r"\([^)]*\)", " ", base))
    add_variant(
        re.sub(
            r"\b(Dept\.?|Department|School|College|Faculty|Lab(oratory)?)\b",
            " ",
            base,
            flags=re.IGNORECASE,
        )
    )
    add_variant(re.sub(r"\s*[-,:]\s*.*$", "", base))

    cleaned = []
    for v in variants:
        vv = re.sub(r"\s+", " ", v).strip(" ,;-")
        if vv and vv not in cleaned:
            cleaned.append(vv)
    return cleaned


def extract_wikidata_coords(entity):
    claims = entity.get("claims") or {}
    coords_claims = claims.get("P625") or []
    for claim in coords_claims:
        try:
            value = claim["mainsnak"]["datavalue"]["value"]
            return float(value["latitude"]), float(value["longitude"])
        except Exception:
            continue

    hq_claims = claims.get("P159") or []
    for claim in hq_claims:
        try:
            mainsnak = claim.get("mainsnak") or {}
            datavalue = mainsnak.get("datavalue") or {}
            target_id = (datavalue.get("value") or {}).get("id")
            if target_id:
                return ("entity", target_id)
        except Exception:
            continue
    return None


def geocode_place_query(
    place_query,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    params = {"q": place_query, "format": "jsonv2", "limit": 1}
    if country_code:
        params["countrycodes"] = country_code.lower()
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(params)
    payload = http_get_json(
        url,
        user_agent=user_agent,
        timeout=request_timeout,
        min_interval_seconds=min_request_interval,
        max_retries=max_retries,
    )
    if not payload:
        return None
    item = payload[0]
    return {
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
        "display_name": item.get("display_name", place_query),
        "source": "nominatim_place",
    }


def extract_place_from_description(description):
    text = normalize_text(description) or ""
    if not text:
        return None

    patterns = [
        r"\b(?:facility|organization|laboratory|research center|research centre|publisher|institute|hospital|university)\s+in\s+([^,]+,\s*[^,]+)\b",
        r"\bbased in\s+([^,]+,\s*[^,]+)\b",
        r"\bassociated with .*?\b([A-Z][A-Za-z .'-]+,\s*[A-Z][A-Za-z .'-]+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" .")

    if "," in text:
        tail = ",".join(part.strip() for part in text.split(",")[-2:])
        if re.search(r"[A-Za-z]", tail):
            return tail.strip(" .")
    return None


@lru_cache(maxsize=1)
def load_existing_coordinate_index():
    index = {}
    for path_str in ("gis_org.csv", "gis_org_not_found_resolved.csv"):
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            with path.open("r", encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    lat = normalize_text(row.get("latitude"))
                    lon = normalize_text(row.get("longitude"))
                    if not lat or not lon:
                        continue
                    name = normalize_text(row.get("organization_name"))
                    if not name:
                        continue
                    index[name] = {
                        "lat": float(lat),
                        "lon": float(lon),
                        "display_name": row.get("geocode_display_name")
                        or row.get("organization_name")
                        or name,
                        "source": row.get("geocode_source") or "existing_csv",
                    }
        except OSError:
            continue
    return index


def throttle_requests(min_interval_seconds):
    global LAST_REQUEST_TS
    if min_interval_seconds <= 0:
        return
    now = time.time()
    elapsed = now - LAST_REQUEST_TS
    if elapsed < min_interval_seconds:
        time.sleep(min_interval_seconds - elapsed)


def http_get_json(
    url,
    user_agent,
    timeout=20,
    min_interval_seconds=0.7,
    max_retries=3,
):
    # 统一请求节流 + 重试退避，降低被外部服务判定为爬虫的风险。
    global LAST_REQUEST_TS
    for attempt in range(1, max_retries + 1):
        throttle_requests(min_interval_seconds)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/json",
                "Accept-Language": "en",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                LAST_REQUEST_TS = time.time()
                return payload
        except urllib.error.HTTPError as exc:
            LAST_REQUEST_TS = time.time()
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                backoff = min(8.0, 0.8 * (2 ** (attempt - 1)))
                LOGGER.debug("HTTP %s retry in %.1fs: %s", exc.code, backoff, url)
                time.sleep(backoff)
                continue
            raise
        except urllib.error.URLError:
            LAST_REQUEST_TS = time.time()
            if attempt < max_retries:
                backoff = min(8.0, 0.8 * (2 ** (attempt - 1)))
                time.sleep(backoff)
                continue
            raise


def country_match(item_country, country_code):
    if not country_code:
        return True
    left = (item_country or "").upper()
    right = (country_code or "").upper()
    return bool(left and left == right)


def source_ror(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 数据源0：ROR 学术机构库，优先用于大学/研究机构命名匹配。
    country_code = effective_country_code(org_name, country_code)
    query = urllib.parse.urlencode({"query": org_name, "affiliation": org_name})
    url = f"https://api.ror.org/organizations?{query}"
    try:
        payload = http_get_json(
            url,
            user_agent=user_agent,
            timeout=request_timeout,
            min_interval_seconds=min_request_interval,
            max_retries=max_retries,
        )
    except Exception as exc:
        LOGGER.debug("ROR request failed for %s: %s", org_name, exc)
        return None

    items = payload.get("items", [])
    if not items:
        return None

    target = normalize_name_for_match(org_name)
    best = None
    best_score = -1.0
    for item in items:
        name = item.get("name") or ""
        country = (item.get("country") or {}).get("country_code")
        if not country_match(country, country_code):
            continue
        locations = item.get("locations") or []
        lat = None
        lon = None
        if locations:
            geo = locations[0].get("geonames_details", {})
            lat = geo.get("lat")
            lon = geo.get("lng")
        if lat is None or lon is None:
            continue
        score = difflib.SequenceMatcher(
            None, target, normalize_name_for_match(name)
        ).ratio()
        if score > best_score:
            best_score = score
            best = {
                "lat": float(lat),
                "lon": float(lon),
                "display_name": name,
                "source": "ror",
            }

    if best and best_score >= 0.72:
        return best
    return None


def source_alias_redirect(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 数据源前置别名：处理少量高价值历史名 / 译名 / 内部机构名。
    alias_info = ORG_ALIAS_HINTS.get(org_name)
    if not alias_info:
        return None

    alias_name, alias_country = alias_info
    for source_func in (
        source_ror,
        source_openalex,
        source_wikipedia,
        source_wikidata_search,
        source_osm_overpass,
        source_nominatim,
    ):
        result = source_func(
            alias_name,
            alias_country or country_code,
            user_agent,
            request_timeout,
            min_request_interval,
            max_retries,
        )
        if result:
            result["display_name"] = result.get("display_name") or alias_name
            result["source"] = f"alias->{result.get('source', source_func.__name__)}"
            return result
    return None


def source_manual_resolution(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 最后兜底：对已核实的历史名、部门名、母机构挂靠关系使用显式覆盖。
    hint = ORG_MANUAL_RESOLUTION_HINTS.get(org_name)
    if not hint:
        return None

    mode = hint.get("mode")
    if mode == "copy_existing":
        target = hint.get("target")
        if not target:
            return None
        existing = load_existing_coordinate_index().get(target)
        if not existing:
            return None
        return {
            "lat": existing["lat"],
            "lon": existing["lon"],
            "display_name": target,
            "source": f"manual_copy:{target}",
        }

    if mode == "geocode_query":
        query = hint.get("query")
        if not query:
            return None
        result = geocode_place_query(
            query,
            hint.get("country_code") or country_code,
            user_agent,
            request_timeout,
            min_request_interval,
            max_retries,
        )
        if result:
            result["source"] = f"manual_geocode:{query}"
        return result

    return None


def source_openalex(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 数据源1：OpenAlex 机构检索，适合学术机构名称。
    country_code = effective_country_code(org_name, country_code)
    query = urllib.parse.urlencode({"search": org_name, "per-page": 10})
    url = f"https://api.openalex.org/institutions?{query}"
    if country_code:
        url += f"&filter=country_code:{urllib.parse.quote(country_code)}"

    try:
        payload = http_get_json(
            url,
            user_agent=user_agent,
            timeout=request_timeout,
            min_interval_seconds=min_request_interval,
            max_retries=max_retries,
        )
    except Exception as exc:
        LOGGER.debug("OpenAlex request failed for %s: %s", org_name, exc)
        return None

    results = payload.get("results", [])
    if not results:
        return None

    target = normalize_name_for_match(org_name)
    best = None
    best_score = -1.0
    for item in results:
        display_name = item.get("display_name") or ""
        geo = item.get("geo") or {}
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        if lat is None or lon is None:
            continue
        cand = normalize_name_for_match(display_name)
        score = difflib.SequenceMatcher(None, target, cand).ratio()
        if score > best_score:
            best_score = score
            best = {
                "lat": float(lat),
                "lon": float(lon),
                "display_name": display_name,
                "source": "openalex",
            }

    if not best or best_score < 0.72:
        return None
    return best


def source_wikipedia(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 数据源2：Wikipedia + Wikidata，取实体坐标(P625)。
    country_code = effective_country_code(org_name, country_code)
    search_params = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": strip_country_hint(org_name),
            "srlimit": 5,
            "format": "json",
            "utf8": 1,
        }
    )
    search_url = f"https://en.wikipedia.org/w/api.php?{search_params}"
    try:
        search_payload = http_get_json(
            search_url,
            user_agent=user_agent,
            timeout=request_timeout,
            min_interval_seconds=min_request_interval,
            max_retries=max_retries,
        )
    except Exception as exc:
        LOGGER.debug("Wikipedia search failed for %s: %s", org_name, exc)
        return None

    results = (search_payload.get("query") or {}).get("search") or []
    if not results:
        return None

    target = normalize_name_for_match(org_name)
    best = None
    best_score = -1.0
    for item in results:
        title = item.get("title")
        if not title:
            continue

        props_params = urllib.parse.urlencode(
            {
                "action": "query",
                "prop": "pageprops",
                "titles": title,
                "format": "json",
                "utf8": 1,
            }
        )
        props_url = f"https://en.wikipedia.org/w/api.php?{props_params}"
        try:
            props_payload = http_get_json(
                props_url,
                user_agent=user_agent,
                timeout=request_timeout,
                min_interval_seconds=min_request_interval,
                max_retries=max_retries,
            )
        except Exception:
            continue

        pages = ((props_payload.get("query") or {}).get("pages") or {}).values()
        wikidata_id = None
        for page in pages:
            wikidata_id = (page.get("pageprops") or {}).get("wikibase_item")
            if wikidata_id:
                break
        if not wikidata_id:
            continue

        entity_params = urllib.parse.urlencode(
            {
                "action": "wbgetentities",
                "ids": wikidata_id,
                "props": "claims",
                "format": "json",
            }
        )
        entity_url = f"https://www.wikidata.org/w/api.php?{entity_params}"
        try:
            entity_payload = http_get_json(
                entity_url,
                user_agent=user_agent,
                timeout=request_timeout,
                min_interval_seconds=min_request_interval,
                max_retries=max_retries,
            )
        except Exception:
            continue

        entity = (entity_payload.get("entities") or {}).get(wikidata_id) or {}
        claims = entity.get("claims") or {}
        coords_claims = claims.get("P625") or []
        if not coords_claims:
            continue
        try:
            value = coords_claims[0]["mainsnak"]["datavalue"]["value"]
            lat = float(value["latitude"])
            lon = float(value["longitude"])
        except Exception:
            continue

        score = difflib.SequenceMatcher(
            None, target, normalize_name_for_match(title)
        ).ratio()
        if score > best_score:
            best_score = score
            best = {
                "lat": lat,
                "lon": lon,
                "display_name": title,
                "source": "wikipedia_wikidata",
            }

    if best and best_score >= 0.68:
        return best
    return None


def source_wikidata_search(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 数据源3：直接搜索 Wikidata 实体，覆盖机构别名、医院、基金会、公司等更广泛组织。
    country_code = effective_country_code(org_name, country_code)
    stripped_name = strip_country_hint(org_name) or org_name
    params = urllib.parse.urlencode(
        {
            "action": "wbsearchentities",
            "search": stripped_name,
            "language": "en",
            "limit": 8,
            "format": "json",
        }
    )
    search_url = f"https://www.wikidata.org/w/api.php?{params}"
    try:
        search_payload = http_get_json(
            search_url,
            user_agent=user_agent,
            timeout=request_timeout,
            min_interval_seconds=min_request_interval,
            max_retries=max_retries,
        )
    except Exception as exc:
        LOGGER.debug("Wikidata search failed for %s: %s", org_name, exc)
        return None

    results = search_payload.get("search") or []
    if not results:
        return None

    target = normalize_name_for_match(stripped_name)
    best = None
    best_score = -1.0

    for item in results:
        entity_id = item.get("id")
        label = item.get("label") or ""
        description = item.get("description") or ""
        if not entity_id:
            continue

        entity_params = urllib.parse.urlencode(
            {
                "action": "wbgetentities",
                "ids": entity_id,
                "props": "claims|labels",
                "languages": "en",
                "format": "json",
            }
        )
        entity_url = f"https://www.wikidata.org/w/api.php?{entity_params}"
        try:
            entity_payload = http_get_json(
                entity_url,
                user_agent=user_agent,
                timeout=request_timeout,
                min_interval_seconds=min_request_interval,
                max_retries=max_retries,
            )
        except Exception:
            continue

        entity = (entity_payload.get("entities") or {}).get(entity_id) or {}
        coords = extract_wikidata_coords(entity)
        if isinstance(coords, tuple) and coords and coords[0] == "entity":
            target_id = coords[1]
            hq_params = urllib.parse.urlencode(
                {
                    "action": "wbgetentities",
                    "ids": target_id,
                    "props": "claims|labels",
                    "languages": "en",
                    "format": "json",
                }
            )
            hq_url = f"https://www.wikidata.org/w/api.php?{hq_params}"
            try:
                hq_payload = http_get_json(
                    hq_url,
                    user_agent=user_agent,
                    timeout=request_timeout,
                    min_interval_seconds=min_request_interval,
                    max_retries=max_retries,
                )
            except Exception:
                coords = None
            else:
                hq_entity = (hq_payload.get("entities") or {}).get(target_id) or {}
                coords = extract_wikidata_coords(hq_entity)
                if isinstance(coords, tuple) and coords and coords[0] == "entity":
                    coords = None

        place_fallback = None
        if coords is None:
            place_query = extract_place_from_description(description)
            if place_query:
                try:
                    place_fallback = geocode_place_query(
                        place_query,
                        country_code,
                        user_agent,
                        request_timeout,
                        min_request_interval,
                        max_retries,
                    )
                except Exception:
                    place_fallback = None
                if place_fallback:
                    coords = (place_fallback["lat"], place_fallback["lon"])
        if coords is None:
            continue

        score = max(
            difflib.SequenceMatcher(None, target, normalize_name_for_match(label)).ratio(),
            difflib.SequenceMatcher(
                None, target, normalize_name_for_match(description)
            ).ratio(),
        )
        if country_code and f" {country_code.lower()} " in f" {description.lower()} ":
            score += 0.05
        if score > best_score:
            best_score = score
            best = {
                "lat": float(coords[0]),
                "lon": float(coords[1]),
                "display_name": (
                    place_fallback.get("display_name")
                    if place_fallback
                    else (label or stripped_name)
                ),
                "source": (
                    "wikidata_search_description_place"
                    if place_fallback
                    else "wikidata_search"
                ),
            }

    if best and best_score >= 0.72:
        return best
    return None


def source_osm_overpass(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 数据源4：Overpass 查询 OSM 里的 university/college/research_institute 要素。
    country_code = effective_country_code(org_name, country_code)
    pattern = re.sub(r"[\"\\\\]", " ", org_name)
    pattern = re.sub(r"\s+", " ", pattern).strip()
    if not pattern:
        return None

    filters = [
        f'node["amenity"~"university|college"]["name"~"{pattern}",i];',
        f'way["amenity"~"university|college"]["name"~"{pattern}",i];',
        f'relation["amenity"~"university|college"]["name"~"{pattern}",i];',
        f'node["office"="research"]["name"~"{pattern}",i];',
        f'way["office"="research"]["name"~"{pattern}",i];',
        f'relation["office"="research"]["name"~"{pattern}",i];',
    ]
    query = "[out:json][timeout:25];(" + "".join(filters) + ");out center 5;"
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
    try:
        payload = http_get_json(
            url,
            user_agent=user_agent,
            timeout=request_timeout,
            min_interval_seconds=min_request_interval,
            max_retries=max_retries,
        )
    except Exception as exc:
        LOGGER.debug("Overpass request failed for %s: %s", org_name, exc)
        return None

    elements = payload.get("elements") or []
    if not elements:
        return None

    target = normalize_name_for_match(org_name)
    best = None
    best_score = -1.0
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name") or ""
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None or lon is None:
            center = el.get("center") or {}
            lat = center.get("lat")
            lon = center.get("lon")
        if lat is None or lon is None:
            continue
        score = difflib.SequenceMatcher(
            None, target, normalize_name_for_match(name or org_name)
        ).ratio()
        if score > best_score:
            best_score = score
            best = {
                "lat": float(lat),
                "lon": float(lon),
                "display_name": name or org_name,
                "source": "osm_overpass",
            }

    if best and best_score >= 0.68:
        return best
    return None


def source_nominatim(
    org_name,
    country_code,
    user_agent,
    request_timeout,
    min_request_interval,
    max_retries,
):
    # 数据源5：Nominatim 地理编码，作为通用兜底检索。
    country_code = effective_country_code(org_name, country_code)
    country_name = COUNTRY_CODE_TO_NAME.get((country_code or "").upper(), "")
    queries = []
    for variant in name_variants(org_name):
        if country_code:
            queries.append((f"{variant}, {country_code}", country_code.lower()))
        if country_name:
            queries.append((f"{variant}, {country_name}", None))
        queries.append((variant, country_code.lower() if country_code else None))

    seen = set()
    for query, countrycodes in queries:
        if query in seen:
            continue
        seen.add(query)

        params = {"q": query, "format": "jsonv2", "limit": 1}
        if countrycodes:
            params["countrycodes"] = countrycodes
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            params
        )

        try:
            payload = http_get_json(
                url,
                user_agent=user_agent,
                timeout=request_timeout,
                min_interval_seconds=min_request_interval,
                max_retries=max_retries,
            )
        except Exception as exc:
            LOGGER.debug("Nominatim request failed for %s: %s", query, exc)
            continue

        if not payload:
            continue

        item = payload[0]
        try:
            return {
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "display_name": item.get("display_name", ""),
                "source": "nominatim",
            }
        except (KeyError, ValueError, TypeError):
            continue

    return None


def get_geocode_sources():
    # Extension point:
    # Register additional source functions here, in preferred order.
    return [
        source_manual_resolution,
        source_alias_redirect,
        source_ror,
        source_openalex,
        source_wikipedia,
        source_wikidata_search,
        source_osm_overpass,
        source_nominatim,
    ]


def iter_records(input_path: Path):
    # 统一支持 .json / .jsonl 两种输入格式。
    if input_path.suffix.lower() == ".json":
        LOGGER.info("Loading JSON input: %s", input_path)
        with input_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, list):
            total = len(payload)
            for idx, item in enumerate(payload, start=1):
                if should_log_progress(idx, total, 1000):
                    LOGGER.info("Read JSON records: %d/%d", idx, total)
                if isinstance(item, dict):
                    yield item
        elif isinstance(payload, dict):
            yield payload
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


def extract_organizations(input_path: Path, progress_every: int):
    LOGGER.info("Step 1/6: extracting organizations from %s", input_path)
    stats = defaultdict(lambda: {"count": 0, "countries": Counter()})
    record_count = 0

    for record in iter_records(input_path):
        record_count += 1
        if record_count % progress_every == 0:
            LOGGER.info("Processed records: %d", record_count)

        authorships = record.get("authorships", [])
        if not isinstance(authorships, list):
            continue

        for entry in authorships:
            org_name = None
            country_code = None
            if isinstance(entry, list):
                if len(entry) >= 3:
                    org_name = normalize_text(entry[2])
                if len(entry) >= 2 and entry[1]:
                    cc = normalize_text(entry[1])
                    country_code = cc.upper() if cc else None
            elif isinstance(entry, dict):
                org_name = normalize_text(
                    entry.get("institution_name")
                    or entry.get("institution")
                    or entry.get("organization")
                    or entry.get("org")
                )
                cc = normalize_text(entry.get("country_code") or entry.get("country"))
                country_code = cc.upper() if cc else None

            if not org_name:
                continue

            # 机构名去重统计，同时保留最常见国家码，供后续地理编码时辅助约束。
            stats[org_name]["count"] += 1
            if country_code:
                stats[org_name]["countries"][country_code] += 1

    LOGGER.info(
        "Finished extraction: records=%d unique_organizations=%d",
        record_count,
        len(stats),
    )
    return stats


def load_csv_by_key(path: Path, key_fields):
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = {}
        for row in reader:
            key = tuple((row.get(k) or "").strip() for k in key_fields)
            if key_fields[1] == "country_code":
                key = (key[0], key[1].upper())
            rows[key] = row
        return rows


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_cache(cache_path: Path):
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        LOGGER.warning("Failed to load cache: %s", cache_path)
    return {}


def save_cache(cache_path: Path, cache):
    with cache_path.open("w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2, sort_keys=True)
    LOGGER.info("Saved geocode cache entries: %d", len(cache))


def cache_is_usable(entry, refresh_days, not_found_retry_days):
    # ok 与 not_found 采用不同缓存过期策略，避免失败结果长期固化。
    checked_at = parse_iso_datetime(entry.get("checked_at"))
    if not checked_at:
        return False

    now = datetime.now(timezone.utc)
    status = entry.get("status")
    if status == "ok":
        return checked_at >= now - timedelta(days=refresh_days)
    return checked_at >= now - timedelta(days=not_found_retry_days)


def resolve_org(
    org_name,
    country_code,
    cache,
    user_agent,
    sleep_seconds,
    refresh_days,
    not_found_retry_days,
    request_timeout,
    min_request_interval,
    max_retries,
):
    cache_key = f"{org_name}||{country_code or ''}"
    cached = cache.get(cache_key)
    if cached and cache_is_usable(cached, refresh_days, not_found_retry_days):
        # 命中有效缓存时直接返回，减少重复外部请求。
        return cached, True

    sources = get_geocode_sources()
    methods_tried = []

    for source_func in sources:
        methods_tried.append(source_func.__name__)
        result = source_func(
            org_name,
            country_code,
            user_agent,
            request_timeout,
            min_request_interval,
            max_retries,
        )
        time.sleep(sleep_seconds)
        if result:
            payload = {
                "status": "ok",
                "lat": result["lat"],
                "lon": result["lon"],
                "display_name": result.get("display_name", ""),
                "source": result.get("source", source_func.__name__),
                "checked_at": now_utc_iso(),
                "methods_tried": methods_tried,
            }
            cache[cache_key] = payload
            return payload, False

    payload = {
        "status": "not_found",
        "lat": "",
        "lon": "",
        "display_name": "",
        "source": "",
        "checked_at": now_utc_iso(),
        "methods_tried": methods_tried,
    }
    cache[cache_key] = payload
    return payload, False


def row_has_coordinates(row):
    return bool((row.get("latitude") or "").strip() and (row.get("longitude") or "").strip())


def merge_with_existing(stats, existing_rows):
    # 更新模式核心：把新抽取结果与旧 CSV 融合，保留已有可用坐标。
    merged = {}

    for org_name, meta in stats.items():
        country_counter = meta["countries"]
        extracted_country = country_counter.most_common(1)[0][0] if country_counter else ""
        key = (org_name, extracted_country)

        existing = existing_rows.get(key)
        if not existing:
            # 若国家码不一致，退化为“按机构名匹配”以兼容历史数据。
            for alt_key, alt_row in existing_rows.items():
                if alt_key[0] == org_name:
                    existing = alt_row
                    key = (org_name, (alt_row.get("country_code") or extracted_country).upper())
                    break

        row = {k: "" for k in CSV_FIELDNAMES}
        if existing:
            for k in CSV_FIELDNAMES:
                if k in existing:
                    row[k] = existing.get(k, "")

        row["organization_name"] = org_name
        row["country_code"] = (row.get("country_code") or extracted_country or "").upper()
        row["appearance_count"] = str(meta["count"])

        status = (row.get("geocode_status") or "").strip()
        if row_has_coordinates(row):
            if status != "ok":
                row["geocode_status"] = "ok"
        else:
            # 统一未定位状态语义，避免历史脚本产生多个 not found 变种。
            row["latitude"] = ""
            row["longitude"] = ""
            row["geocode_status"] = "not_found"
            if not row.get("geocode_display_name"):
                row["geocode_display_name"] = ""
            row["geocode_source"] = ""

        merged[(row["organization_name"], row["country_code"])] = row

    return merged


def row_is_stale(row, refresh_days):
    checked = parse_iso_datetime(row.get("last_checked_at"))
    if not checked:
        return True
    return checked < datetime.now(timezone.utc) - timedelta(days=refresh_days)


def update_not_found_registry(not_found_rows, row, methods_tried):
    # not_found 台账去重更新：键为(机构名, 国家码)，累计尝试次数与最后方法。
    key = ((row.get("organization_name") or "").strip(), (row.get("country_code") or "").strip().upper())
    current = not_found_rows.get(key, {})

    attempt_count = 0
    try:
        attempt_count = int(current.get("attempt_count", 0))
    except ValueError:
        attempt_count = 0

    not_found_rows[key] = {
        "organization_name": key[0],
        "country_code": key[1],
        "appearance_count": row.get("appearance_count", ""),
        "last_status": "not_found",
        "last_attempt_at": now_utc_iso(),
        "attempt_count": str(attempt_count + 1),
        "last_method": ",".join(methods_tried or []),
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Create or update gis_org.csv from paperMerge data. "
            "If gis_org.csv exists, run in update mode with retry geocoding and "
            "maintain gis_org_not_found.csv."
        )
    )
    parser.add_argument("--input", default="paperMerge.txt", help="Input JSON/JSONL")
    parser.add_argument("--output", default="gis_org.csv", help="Main output CSV")
    parser.add_argument(
        "--not-found-output",
        default="gis_org_not_found.csv",
        help="Not-found registry CSV",
    )
    parser.add_argument(
        "--cache",
        default=".org_geocode_cache.json",
        help="Geocode cache JSON",
    )
    parser.add_argument(
        "--user-agent",
        default="pre_org.py (academic GIS incremental geocoder)",
        help="HTTP User-Agent",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Sleep seconds between geocode source calls",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=20.0,
        help="HTTP request timeout seconds",
    )
    parser.add_argument(
        "--min-request-interval",
        type=float,
        default=0.7,
        help="Min interval between HTTP requests to reduce crawler-like behavior",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retries for transient HTTP errors",
    )
    parser.add_argument(
        "--refresh-days",
        type=int,
        default=90,
        help="Re-check coordinates older than N days",
    )
    parser.add_argument(
        "--not-found-retry-days",
        type=int,
        default=7,
        help="Retry cached not_found after N days",
    )
    parser.add_argument(
        "--skip-geocode",
        action="store_true",
        help="Skip geocoding and only update org list",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=200,
        help="Progress log interval",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only geocode first N candidate rows (0 means all)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.log_level)

    input_path = Path(args.input)
    output_path = Path(args.output)
    not_found_output = Path(args.not_found_output)
    cache_path = Path(args.cache)
    progress_every = max(1, args.progress_every)

    if not input_path.exists():
        LOGGER.error("Input file not found: %s", input_path)
        return 1

    mode = "update" if output_path.exists() else "create"
    LOGGER.info("Start pre_org in %s mode", mode)

    stats = extract_organizations(input_path, progress_every=progress_every)
    existing_rows = load_csv_by_key(output_path, ["organization_name", "country_code"])
    not_found_rows = load_csv_by_key(not_found_output, ["organization_name", "country_code"])
    cache = load_cache(cache_path)

    LOGGER.info("Step 2/6: merging with existing %s (%d rows)", output_path, len(existing_rows))
    merged = merge_with_existing(stats, existing_rows)

    if args.skip_geocode:
        LOGGER.info("Step 3/6: geocode skipped by flag")
        candidates = []
    else:
        candidates = []
        for key, row in merged.items():
            has_coord = row_has_coordinates(row)
            status = (row.get("geocode_status") or "").strip()
            stale = row_is_stale(row, args.refresh_days)
            # 需要处理的候选：无坐标、状态异常或坐标过期需要刷新。
            if (not has_coord) or status != "ok" or stale:
                candidates.append(key)

        if args.limit > 0:
            candidates = candidates[: args.limit]

        LOGGER.info("Step 3/6: geocode candidates=%d", len(candidates))

    resolved = 0
    unresolved = 0
    from_cache = 0

    for idx, key in enumerate(candidates, start=1):
        row = merged[key]
        org_name = row["organization_name"]
        country_code = (row.get("country_code") or "").upper()
        had_previous_coords = row_has_coordinates(row)
        prev_lat = row.get("latitude", "")
        prev_lon = row.get("longitude", "")
        prev_status = row.get("geocode_status", "")
        prev_display_name = row.get("geocode_display_name", "")
        prev_source = row.get("geocode_source", "")

        result, used_cache = resolve_org(
            org_name=org_name,
            country_code=country_code,
            cache=cache,
            user_agent=args.user_agent,
            sleep_seconds=args.sleep,
            refresh_days=args.refresh_days,
            not_found_retry_days=args.not_found_retry_days,
            request_timeout=args.request_timeout,
            min_request_interval=args.min_request_interval,
            max_retries=max(1, args.max_retries),
        )

        if used_cache:
            from_cache += 1

        row["last_checked_at"] = result.get("checked_at", now_utc_iso())
        row["geocode_source"] = result.get("source", "")
        row["geocode_display_name"] = result.get("display_name", "")

        if result.get("status") == "ok":
            row["latitude"] = str(result.get("lat", ""))
            row["longitude"] = str(result.get("lon", ""))
            row["geocode_status"] = "ok"
            resolved += 1
            not_found_rows.pop(key, None)
        else:
            if had_previous_coords:
                # 若刷新失败但历史坐标可用，保留旧坐标，避免数据回退成 not_found。
                row["latitude"] = prev_lat
                row["longitude"] = prev_lon
                row["geocode_status"] = prev_status or "ok"
                row["geocode_display_name"] = prev_display_name
                row["geocode_source"] = prev_source
                LOGGER.warning(
                    "Refresh failed, keeping previous coordinates: %s (%s)",
                    org_name,
                    country_code,
                )
            else:
                # 无历史坐标且重试失败，登记到 not_found 台账便于后续专项修复。
                row["latitude"] = ""
                row["longitude"] = ""
                row["geocode_status"] = "not_found"
                unresolved += 1
                update_not_found_registry(
                    not_found_rows, row, result.get("methods_tried", [])
                )

        if should_log_progress(idx, len(candidates), progress_every):
            pct = (idx / len(candidates) * 100) if candidates else 100.0
            LOGGER.info(
                "Geocode progress: %d/%d (%.1f%%) | resolved=%d unresolved=%d cache_hits=%d",
                idx,
                len(candidates),
                pct,
                resolved,
                unresolved,
                from_cache,
            )

    LOGGER.info("Step 4/6: writing %s", output_path)
    rows_out = [merged[k] for k in sorted(merged.keys(), key=lambda x: (x[0], x[1]))]
    write_csv(output_path, CSV_FIELDNAMES, rows_out)

    active_not_found_keys = {
        k for k, row in merged.items() if (row.get("geocode_status") or "") == "not_found"
    }
    # 台账与主表对齐：只保留当前仍是 not_found 的机构，清理已恢复的历史记录。
    aligned_not_found_rows = {}
    for key in active_not_found_keys:
        if key in not_found_rows:
            aligned_not_found_rows[key] = not_found_rows[key]
            continue
        row = merged[key]
        aligned_not_found_rows[key] = {
            "organization_name": key[0],
            "country_code": key[1],
            "appearance_count": row.get("appearance_count", ""),
            "last_status": "not_found",
            "last_attempt_at": row.get("last_checked_at", "") or "",
            "attempt_count": "0",
            "last_method": "",
        }
    not_found_rows = aligned_not_found_rows

    LOGGER.info("Step 5/6: writing %s", not_found_output)
    not_found_out = [
        not_found_rows[k]
        for k in sorted(not_found_rows.keys(), key=lambda x: (x[0], x[1]))
    ]
    write_csv(not_found_output, NOT_FOUND_FIELDNAMES, not_found_out)

    LOGGER.info("Step 6/6: saving cache")
    save_cache(cache_path, cache)

    LOGGER.info(
        "Done: organizations=%d, geocode_candidates=%d, resolved=%d, unresolved=%d, not_found_registry=%d",
        len(rows_out),
        len(candidates),
        resolved,
        unresolved,
        len(not_found_out),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
