#!/usr/bin/env python3
"""Prepare Andrew's frozen JOSS keyword/topic corpus for the RQ1 pilot.

The CSV contains two semantically distinct annotation sources:
- `joss_tags`: keywords/tags supplied through JOSS;
- `repository_topics`: GitHub repository topics.

The file also contains `combined_keywords`. We deliberately do NOT treat that column as
a third label source because it combines the other two and would double-count labels.
If the frozen schema changes, the script falls back to a single keyword-like column.

No semantic facet is assigned automatically here. Lexical normalization and semantic
annotation remain separate research steps.
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

PREFERRED_LABEL_COLUMNS = (
    ("joss_tags", "joss_tag"),
    ("repository_topics", "repository_topic"),
)
FALLBACK_LABEL_COLUMNS = (
    ("combined_keywords", "combined_keyword"),
    ("keywords", "keyword"),
    ("keyword", "keyword"),
    ("tags", "tag"),
    ("topics", "topic"),
)
REPOSITORY_COLUMN_CANDIDATES = (
    "url",
    "repository",
    "repo",
    "repository_url",
    "repo_url",
    "github",
    "github_url",
)


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "research-software-classification-analysis/0.1"})
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


def choose_label_columns(fieldnames: list[str]) -> list[tuple[str, str]]:
    lookup = {name.strip().lower(): name for name in fieldnames}
    preferred = [
        (lookup[column], label_type)
        for column, label_type in PREFERRED_LABEL_COLUMNS
        if column in lookup
    ]
    if preferred:
        return preferred

    for column, label_type in FALLBACK_LABEL_COLUMNS:
        if column in lookup:
            return [(lookup[column], label_type)]

    return []


def parse_keywords(value: str) -> list[str]:
    """Parse common exported keyword/list encodings without semantic rewriting."""
    value = (value or "").strip()
    if not value:
        return []

    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value.replace("'", '"'))
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            value = value[1:-1]

    for separator in ("|", ";"):
        if separator in value:
            return [
                part.strip(" \t\r\n\"'")
                for part in value.split(separator)
                if part.strip()
            ]

    if "," in value:
        return [
            part.strip(" \t\r\n\"'")
            for part in value.split(",")
            if part.strip()
        ]

    return [value.strip(" \t\r\n\"'")]


def normalize_surface(label: str) -> str:
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


def sample_frequency_strata(
    rows: list[dict[str, object]],
    size: int,
    rng: random.Random,
) -> list[dict[str, object]]:
    if len(rows) <= size:
        return list(rows)

    ranked = sorted(
        rows,
        key=lambda row: (-int(row["frequency"]), str(row["normalized_label"])),
    )
    strata_count = min(5, size)
    selected: list[dict[str, object]] = []

    base_take = size // strata_count
    remainder = size % strata_count
    for stratum in range(strata_count):
        start = round(stratum * len(ranked) / strata_count)
        end = round((stratum + 1) * len(ranked) / strata_count)
        bucket = ranked[start:end]
        take = base_take + (1 if stratum < remainder else 0)
        selected.extend(rng.sample(bucket, min(take, len(bucket))))

    if len(selected) < size:
        chosen = {
            (str(row["raw_label_type"]), str(row["normalized_label"]))
            for row in selected
        }
        remaining = [
            row
            for row in ranked
            if (str(row["raw_label_type"]), str(row["normalized_label"])) not in chosen
        ]
        selected.extend(rng.sample(remaining, min(size - len(selected), len(remaining))))

    return selected[:size]


def stratified_pilot(
    frequency_rows: list[dict[str, object]],
    size: int = PILOT_SIZE,
    seed: int = SEED,
) -> list[dict[str, object]]:
    """Balance label sources, then sample across the frequency range within each source."""
    if len(frequency_rows) <= size:
        selected = list(frequency_rows)
    else:
        by_type: dict[str, list[dict[str, object]]] = {}
        for row in frequency_rows:
            by_type.setdefault(str(row["raw_label_type"]), []).append(row)

        rng = random.Random(seed)
        types = sorted(by_type)
        selected: list[dict[str, object]] = []

        base = size // len(types)
        remainder = size % len(types)
        for index, label_type in enumerate(types):
            target = base + (1 if index < remainder else 0)
            selected.extend(
                sample_frequency_strata(by_type[label_type], target, rng)
            )

    return sorted(
        selected,
        key=lambda row: (
            str(row["raw_label_type"]),
            -int(row["frequency"]),
            str(row["normalized_label"]),
        ),
    )


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

        label_columns = choose_label_columns(reader.fieldnames)
        if not label_columns:
            raise ValueError(
                "Could not identify classification columns. "
                f"Available columns: {reader.fieldnames}"
            )
        repository_column = choose_column(reader.fieldnames, REPOSITORY_COLUMN_CANDIDATES)
        records = list(reader)

    provenance = {
        "source": "JOSS + linked GitHub repository metadata",
        "source_role": "development_seed",
        "url": JOSS_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": checksum,
        "records": len(records),
        "expected_records": EXPECTED_RECORDS,
        "label_columns": [
            {"column": column, "raw_label_type": label_type}
            for column, label_type in label_columns
        ],
        "ignored_columns": (
            ["combined_keywords"]
            if {c.lower() for c in reader.fieldnames or []}.issuperset(
                {"joss_tags", "repository_topics", "combined_keywords"}
            )
            else []
        ),
        "repository_column": repository_column,
        "raw_file": str(raw_path.relative_to(ROOT)),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    extracted_rows: list[dict[str, object]] = []
    counts: Counter[tuple[str, str]] = Counter()
    example_raw: dict[tuple[str, str], str] = {}

    for index, row in enumerate(records, start=1):
        repository = row.get(repository_column, "") if repository_column else ""
        for column, label_type in label_columns:
            for raw_label in parse_keywords(row.get(column, "")):
                normalized = normalize_surface(raw_label)
                if not normalized:
                    continue
                key = (label_type, normalized)
                counts[key] += 1
                example_raw.setdefault(key, raw_label)
                extracted_rows.append(
                    {
                        "source": "joss",
                        "source_record_id": index,
                        "software_id": repository,
                        "repository_url": repository,
                        "raw_label": raw_label,
                        "raw_label_type": label_type,
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
            "raw_label_type": label_type,
            "normalized_label": normalized,
            "example_raw_label": example_raw[(label_type, normalized)],
            "frequency": frequency,
        }
        for (label_type, normalized), frequency in counts.items()
    ]
    frequencies.sort(
        key=lambda row: (
            str(row["raw_label_type"]),
            -int(row["frequency"]),
            str(row["normalized_label"]),
        )
    )

    write_csv(
        INTERIM_DIR / "joss_label_frequencies.csv",
        ["raw_label_type", "normalized_label", "example_raw_label", "frequency"],
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
            "raw_label_type",
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
    print(f"Unique typed normalized labels: {len(frequencies):,}")
    for label_type in sorted({str(row['raw_label_type']) for row in frequencies}):
        count = sum(1 for row in frequencies if row["raw_label_type"] == label_type)
        print(f"  {label_type}: {count:,} distinct labels")
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
