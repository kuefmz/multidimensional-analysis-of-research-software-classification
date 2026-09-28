#!/usr/bin/env python3
"""Prepare the frozen JOSS keyword seed corpus for the RQ1 pilot.

The script:
1. downloads the exact frozen CSV configured for the study;
2. preserves it unchanged under data/raw/joss/;
3. writes provenance including SHA256;
4. extracts labels without discarding raw forms;
5. performs conservative surface normalization;
6. writes unique-label frequencies;
7. creates a deterministic frequency-stratified 50-label annotation pilot.

No semantic facet is assigned automatically here. Facet assignment is a research
annotation decision and is kept separate from lexical normalization.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


JOSS_URL = (
    "https://gist.githubusercontent.com/andrew/"
    "627fd9cfe97eaf7f779e3c755c4fffa8/raw/"
    "0290a0dcbf3d867c75051662808ef07e0470170e/joss_keywords.csv"
)
EXPECTED_RECORDS = 3279
SEED = 42
PILOT_SIZE = 50

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "joss"
INTERIM_DIR = ROOT / "data" / "interim"
ANNOTATION_DIR = ROOT / "data" / "annotations"

KEYWORD_COLUMN_CANDIDATES = (
    "keywords",
    "keyword",
    "tags",
    "topics",
    "software_keywords",
    "joss_keywords",
)
REPOSITORY_COLUMN_CANDIDATES = (
    "repository",
    "repo",
    "repository_url",
    "repo_url",
    "github",
    "github_url",
    "url",
)


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "research-software-facets/0.1"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def choose_column(fieldnames: list[str], candidates: tuple[str, ...]) -> str | None:
    lookup = {name.strip().lower(): name for name in fieldnames}
    for candidate in candidates:
        if candidate in lookup:
            return lookup[candidate]
    return None


def parse_keywords(value: str) -> list[str]:
    """Parse common CSV keyword encodings without semantic rewriting."""
    value = (value or "").strip()
    if not value:
        return []

    # JSON/Python-looking lists are common in exported metadata.
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value.replace("'", '"'))
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            value = value[1:-1]

    # Prefer explicit multi-value separators. Comma is used last because labels
    # can occasionally contain commas.
    for separator in ("|", ";"):
        if separator in value:
            return [part.strip(" \t\r\n\"'") for part in value.split(separator) if part.strip()]

    if "," in value:
        return [part.strip(" \t\r\n\"'") for part in value.split(",") if part.strip()]

    return [value.strip(" \t\r\n\"'")]


def normalize_surface(label: str) -> str:
    """Conservative lexical normalization; does not merge semantic synonyms."""
    text = unicodedata.normalize("NFKC", label)
    text = text.strip().lower()
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stratified_pilot(
    frequency_rows: list[dict[str, object]],
    size: int = PILOT_SIZE,
    seed: int = SEED,
) -> list[dict[str, object]]:
    """Sample across the frequency range so the pilot is not dominated by head labels."""
    if len(frequency_rows) <= size:
        selected = list(frequency_rows)
    else:
        ranked = sorted(
            frequency_rows,
            key=lambda row: (-int(row["frequency"]), str(row["normalized_label"])),
        )
        strata_count = 5
        rng = random.Random(seed)
        selected: list[dict[str, object]] = []

        for stratum in range(strata_count):
            start = round(stratum * len(ranked) / strata_count)
            end = round((stratum + 1) * len(ranked) / strata_count)
            bucket = ranked[start:end]
            take = size // strata_count
            selected.extend(rng.sample(bucket, min(take, len(bucket))))

        if len(selected) < size:
            chosen = {str(row["normalized_label"]) for row in selected}
            remaining = [row for row in ranked if str(row["normalized_label"]) not in chosen]
            selected.extend(rng.sample(remaining, min(size - len(selected), len(remaining))))

    return sorted(selected, key=lambda row: (-int(row["frequency"]), str(row["normalized_label"])))


def main(force_download: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATION_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = RAW_DIR / "joss_keywords.csv"
    provenance_path = RAW_DIR / "provenance.json"

    if force_download or not raw_path.exists():
        raw_bytes = download(JOSS_URL)
        raw_path.write_bytes(raw_bytes)
    else:
        raw_bytes = raw_path.read_bytes()

    checksum = sha256_bytes(raw_bytes)

    with raw_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("JOSS CSV has no header.")

        keyword_column = choose_column(reader.fieldnames, KEYWORD_COLUMN_CANDIDATES)
        if not keyword_column:
            raise ValueError(
                "Could not identify the keyword column. "
                f"Available columns: {reader.fieldnames}"
            )
        repository_column = choose_column(reader.fieldnames, REPOSITORY_COLUMN_CANDIDATES)
        records = list(reader)

    provenance = {
        "source": "Journal of Open Source Software",
        "source_role": "development_seed",
        "url": JOSS_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": checksum,
        "records": len(records),
        "expected_records": EXPECTED_RECORDS,
        "keyword_column": keyword_column,
        "repository_column": repository_column,
        "raw_file": str(raw_path.relative_to(ROOT)),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    extracted_rows: list[dict[str, object]] = []
    normalized_to_raw = {}
    counts: Counter[str] = Counter()

    for index, row in enumerate(records, start=1):
        repository = row.get(repository_column, "") if repository_column else ""
        for raw_label in parse_keywords(row.get(keyword_column, "")):
            normalized = normalize_surface(raw_label)
            if not normalized:
                continue
            counts[normalized] += 1
            normalized_to_raw.setdefault(normalized, raw_label)
            extracted_rows.append(
                {
                    "source": "joss",
                    "source_record_id": index,
                    "software_id": repository,
                    "repository_url": repository,
                    "raw_label": raw_label,
                    "raw_label_type": "keyword",
                    "normalized_label": normalized,
                    "normalization_method": "surface_v1",
                }
            )

    write_csv(
        INTERIM_DIR / "joss_extracted_labels.csv",
        [
            "source",
            "source_record_id",
            "software_id",
            "repository_url",
            "raw_label",
            "raw_label_type",
            "normalized_label",
            "normalization_method",
        ],
        extracted_rows,
    )

    frequencies = [
        {
            "normalized_label": label,
            "example_raw_label": normalized_to_raw[label],
            "frequency": frequency,
        }
        for label, frequency in counts.items()
    ]
    frequencies.sort(key=lambda row: (-int(row["frequency"]), str(row["normalized_label"])))

    write_csv(
        INTERIM_DIR / "joss_label_frequencies.csv",
        ["normalized_label", "example_raw_label", "frequency"],
        frequencies,
    )

    pilot = stratified_pilot(frequencies)
    pilot_rows = [
        {
            "pilot_id": f"JOSS-{i:03d}",
            **row,
            "primary_facet": "",
            "proposed_facet": "",
            "confidence": "",
            "annotation_note": "",
        }
        for i, row in enumerate(pilot, start=1)
    ]

    write_csv(
        ANNOTATION_DIR / "joss_pilot_50.csv",
        [
            "pilot_id",
            "normalized_label",
            "example_raw_label",
            "frequency",
            "primary_facet",
            "proposed_facet",
            "confidence",
            "annotation_note",
        ],
        pilot_rows,
    )

    print(f"Rows in source CSV: {len(records):,}")
    print(f"Extracted label occurrences: {len(extracted_rows):,}")
    print(f"Unique normalized labels: {len(frequencies):,}")
    print(f"Pilot labels: {len(pilot_rows):,}")
    if len(records) != EXPECTED_RECORDS:
        print(
            "WARNING: source record count differs from the documented 3,279 rows. "
            "Check provenance.json before using the snapshot."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Replace the local raw snapshot with a fresh download from the frozen URL.",
    )
    args = parser.parse_args()
    main(force_download=args.force_download)
