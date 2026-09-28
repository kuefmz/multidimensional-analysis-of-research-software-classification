#!/usr/bin/env python3
"""Extract RQ1 labels from the full versioned SemRepo N-Triples dump.

The public SemRepo SPARQL endpoint is useful for diagnostics but may expose only a
subset of the released graph. This script is the reproducible primary path for the
study: it streams the compressed N-Triples dump and never loads the KG into memory.

Usage:
    python src/semrepo_dump_collector.py \
        --input data/raw/semrepo/SemRepo_2025-05-11.nt.gz

The released dump can be obtained from Zenodo record 20084784.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "interim"
RAW_META_DIR = ROOT / "data" / "raw" / "semrepo"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
REPOSITORY_CLASS = "https://semrepo.org/class/repository"
FOAF_TOPIC = "http://xmlns.com/foaf/0.1/topic"
HAS_LANGUAGE_REFERENCE = "https://semrepo.org/property/hasLanguageReference"
HAS_LANGUAGE_NAME = "https://semrepo.org/property/hasLanguageName"

URI_TRIPLE = re.compile(
    r"^<(?P<subject>[^>]+)>\s+<(?P<predicate>[^>]+)>\s+<(?P<object>[^>]+)>\s*\.\s*$"
)


def parse_uri_triple(line: str) -> tuple[str, str, str] | None:
    match = URI_TRIPLE.match(line)
    if not match:
        return None
    return (
        match.group("subject"),
        match.group("predicate"),
        match.group("object"),
    )


def uri_to_label(uri: str) -> str:
    parsed = urlparse(uri)
    local = unquote(parsed.path.rstrip("/").split("/")[-1]) if parsed.path else uri
    return local.strip()


def normalize_surface(label: str) -> str:
    text = unicodedata.normalize("NFKC", label)
    text = text.strip().lower()
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def prepare_db(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS repo_lang (ref TEXT PRIMARY KEY, repo TEXT NOT NULL)"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS lang_name (ref TEXT PRIMARY KEY, lang_uri TEXT NOT NULL)"
    )
    return connection


def extract_dump(input_path: Path, db_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    topic_counts: Counter[str] = Counter()
    repository_count = 0
    repository_topic_edges = 0
    repository_language_edges = 0
    language_name_edges = 0

    connection = prepare_db(db_path)
    cursor = connection.cursor()

    with gzip.open(input_path, "rt", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            triple = parse_uri_triple(line)
            if triple is None:
                continue
            subject, predicate, obj = triple

            if predicate == RDF_TYPE and obj == REPOSITORY_CLASS:
                repository_count += 1
            elif predicate == FOAF_TOPIC:
                topic_counts[obj] += 1
                repository_topic_edges += 1
            elif predicate == HAS_LANGUAGE_REFERENCE:
                cursor.execute(
                    "INSERT OR IGNORE INTO repo_lang(ref, repo) VALUES (?, ?)",
                    (obj, subject),
                )
                repository_language_edges += 1
            elif predicate == HAS_LANGUAGE_NAME:
                cursor.execute(
                    "INSERT OR IGNORE INTO lang_name(ref, lang_uri) VALUES (?, ?)",
                    (subject, obj),
                )
                language_name_edges += 1

            if line_number % 1_000_000 == 0:
                connection.commit()
                print(f"Processed {line_number:,} triples...")

    connection.commit()

    language_rows = connection.execute(
        """
        SELECT lang_name.lang_uri, COUNT(DISTINCT repo_lang.repo)
        FROM repo_lang
        JOIN lang_name ON repo_lang.ref = lang_name.ref
        GROUP BY lang_name.lang_uri
        ORDER BY COUNT(DISTINCT repo_lang.repo) DESC
        """
    ).fetchall()

    repositories_with_language = connection.execute(
        """
        SELECT COUNT(DISTINCT repo_lang.repo)
        FROM repo_lang
        JOIN lang_name ON repo_lang.ref = lang_name.ref
        """
    ).fetchone()[0]

    connection.close()

    rows: list[dict[str, object]] = []
    for topic_uri, frequency in topic_counts.items():
        raw_label = uri_to_label(topic_uri)
        rows.append(
            {
                "source": "semrepo",
                "raw_label": raw_label,
                "raw_label_uri": topic_uri,
                "raw_label_type": "repository_topic",
                "normalized_label": normalize_surface(raw_label),
                "frequency": frequency,
                "normalization_method": "surface_v1",
            }
        )

    for language_uri, frequency in language_rows:
        raw_label = uri_to_label(language_uri)
        rows.append(
            {
                "source": "semrepo",
                "raw_label": raw_label,
                "raw_label_uri": language_uri,
                "raw_label_type": "programming_language",
                "normalized_label": normalize_surface(raw_label),
                "frequency": frequency,
                "normalization_method": "surface_v1",
            }
        )

    rows.sort(
        key=lambda row: (
            str(row["raw_label_type"]),
            -int(row["frequency"]),
            str(row["normalized_label"]),
        )
    )

    stats = {
        "repository_type_triples": repository_count,
        "repository_topic_edges": repository_topic_edges,
        "distinct_topic_labels": len(topic_counts),
        "repository_language_reference_edges": repository_language_edges,
        "language_name_edges": language_name_edges,
        "distinct_language_labels": len(language_rows),
        "repositories_with_language": repositories_with_language,
    }
    return rows, stats


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "source",
        "raw_label",
        "raw_label_uri",
        "raw_label_type",
        "normalized_label",
        "frequency",
        "normalization_method",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(input_path: Path, sqlite_path: Path | None = None) -> None:
    if not input_path.exists():
        raise FileNotFoundError(
            f"SemRepo dump not found: {input_path}. Download the versioned N-Triples "
            "dump from Zenodo record 20084784 and pass it with --input."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_META_DIR.mkdir(parents=True, exist_ok=True)

    delete_temp = False
    if sqlite_path is None:
        temp = tempfile.NamedTemporaryFile(prefix="semrepo_join_", suffix=".sqlite", delete=False)
        temp.close()
        sqlite_path = Path(temp.name)
        delete_temp = True

    try:
        rows, stats = extract_dump(input_path, sqlite_path)
    finally:
        if delete_temp and sqlite_path.exists():
            sqlite_path.unlink()
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(sqlite_path) + suffix)
                if sidecar.exists():
                    sidecar.unlink()

    output_path = OUT_DIR / "semrepo_dump_label_frequencies.csv"
    write_csv(output_path, rows)

    provenance = {
        "source": "SemRepo",
        "source_mode": "versioned_zenodo_ntriples_dump",
        "zenodo_record": "20084784",
        "input_file": input_path.name,
        "retrieved_or_processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification_fields": ["repository_topic", "programming_language"],
        "excluded_from_initial_rq1": {
            "package": (
                "Packages are implementation dependencies rather than explicit "
                "classification labels; reconsider separately if study scope expands."
            )
        },
        "stats": stats,
    }
    (RAW_META_DIR / "dump_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(provenance, indent=2))
    print(f"Wrote {len(rows):,} typed label rows to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=None,
        help="Optional persistent SQLite path for the language-reference join.",
    )
    args = parser.parse_args()
    main(input_path=args.input, sqlite_path=args.sqlite_path)
