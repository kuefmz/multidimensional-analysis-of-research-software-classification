#!/usr/bin/env python3
"""Extract bio.tools EDAM Topic/Operation labels from the merged Bioschemas dump.

Inputs:
- research-software-ecosystem/content datasets/bioschemas-dump.ttl
- EDAM ontology OWL for canonical rdfs:label values

A software node is considered bio.tools-linked when schema:identifier contains an
IRI under https://bio.tools/. From those nodes only:
- schema:applicationSubCategory EDAM topic_* IRIs -> edam_topic
- schema:featureList EDAM operation_* IRIs -> edam_operation

The merged dump contains records from several ecosystems, so the bio.tools identifier
filter is essential.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "interim"
RAW_META_DIR = ROOT / "data" / "raw" / "biotools"

SCHEMA_HTTP = Namespace("http://schema.org/")
SCHEMA_HTTPS = Namespace("https://schema.org/")
BIOTOOLS_PREFIX = "https://bio.tools/"
EDAM_PREFIX = "http://edamontology.org/"


def normalize_surface(label: str) -> str:
    text = unicodedata.normalize("NFKC", label or "")
    text = text.strip().lower()
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def build_edam_labels(edam_path: Path) -> dict[str, str]:
    graph = Graph()
    graph.parse(edam_path)
    labels: dict[str, str] = {}
    for subject, _, value in graph.triples((None, RDFS.label, None)):
        uri = str(subject)
        if uri.startswith(EDAM_PREFIX):
            labels[uri] = str(value)
    return labels


def fallback_edam_label(uri: str) -> str:
    local = uri.rsplit("/", 1)[-1]
    local = re.sub(r"^(topic|operation)_", "", local)
    return local.replace("_", " ")


def collect(dump_path: Path, edam_path: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    graph = Graph()
    graph.parse(dump_path, format="turtle")
    edam_labels = build_edam_labels(edam_path)

    biotools_subjects: dict[URIRef, str] = {}
    identifier_predicates = (SCHEMA_HTTP.identifier, SCHEMA_HTTPS.identifier)
    identifier_triples_seen = 0
    for predicate in identifier_predicates:
        for subject, _, identifier in graph.triples((None, predicate, None)):
            identifier_triples_seen += 1
            value = str(identifier)
            if value.startswith(BIOTOOLS_PREFIX):
                biotools_subjects[subject] = value

    assignments: dict[tuple[str, str], set[str]] = defaultdict(set)
    example_subject: dict[tuple[str, str], str] = {}
    software_with_topic: set[str] = set()
    software_with_operation: set[str] = set()

    for subject, biotools_id in biotools_subjects.items():
        for predicate in (
            SCHEMA_HTTP.applicationSubCategory,
            SCHEMA_HTTPS.applicationSubCategory,
        ):
            for obj in graph.objects(subject, predicate):
                uri = str(obj)
                if uri.startswith(EDAM_PREFIX + "topic_"):
                    assignments[("edam_topic", uri)].add(biotools_id)
                    example_subject.setdefault(("edam_topic", uri), str(subject))
                    software_with_topic.add(biotools_id)

        for predicate in (SCHEMA_HTTP.featureList, SCHEMA_HTTPS.featureList):
            for obj in graph.objects(subject, predicate):
                uri = str(obj)
                if uri.startswith(EDAM_PREFIX + "operation_"):
                    assignments[("edam_operation", uri)].add(biotools_id)
                    example_subject.setdefault(("edam_operation", uri), str(subject))
                    software_with_operation.add(biotools_id)

    rows: list[dict[str, object]] = []
    unresolved_labels = 0
    for (label_type, uri), software_ids in assignments.items():
        raw_label = edam_labels.get(uri)
        if not raw_label:
            raw_label = fallback_edam_label(uri)
            unresolved_labels += 1
        rows.append(
            {
                "source": "biotools",
                "raw_label": raw_label,
                "raw_label_uri": uri,
                "raw_label_type": label_type,
                "normalized_label": normalize_surface(raw_label),
                "frequency": len(software_ids),
                "example_software_id": sorted(software_ids)[0],
                "example_subject": example_subject[(label_type, uri)],
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
        "dump_triples": len(graph),
        "schema_identifier_triples_seen": identifier_triples_seen,
        "biotools_linked_software_subjects": len(biotools_subjects),
        "software_with_edam_topic": len(software_with_topic),
        "software_with_edam_operation": len(software_with_operation),
        "distinct_typed_labels": len(rows),
        "unresolved_edam_labels": unresolved_labels,
        "by_type": {},
    }
    for label_type in ("edam_topic", "edam_operation"):
        typed = [row for row in rows if row["raw_label_type"] == label_type]
        stats["by_type"][label_type] = {
            "distinct_labels": len(typed),
            "software_label_assignments": sum(int(row["frequency"]) for row in typed),
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
        "example_software_id",
        "example_subject",
        "normalization_method",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(
    dump_path: Path,
    edam_path: Path,
    content_revision: str = "",
    edam_revision: str = "",
) -> None:
    rows, stats = collect(dump_path, edam_path)
    if stats["biotools_linked_software_subjects"] == 0:
        raise ValueError(
            "No bio.tools-linked software subjects found in the Bioschemas dump. "
            "Treat this as a schema/namespace mismatch rather than a valid empty result."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_META_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / "biotools_full_label_frequencies.csv"
    write_csv(output, rows)

    provenance = {
        "source": "bio.tools-linked records in Bioschemas merged dump",
        "content_repository": "https://github.com/research-software-ecosystem/content",
        "content_revision": content_revision or None,
        "dump_file": "datasets/bioschemas-dump.ttl",
        "edam_repository": "https://github.com/edamontology/edamontology",
        "edam_revision": edam_revision or None,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_mode": "bioschemas_dump_filtered_by_biotools_identifier",
        "classification_fields": ["edam_topic", "edam_operation"],
        "stats": stats,
    }
    (RAW_META_DIR / "bioschemas_dump_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(provenance, indent=2))
    print(f"Wrote {len(rows):,} typed labels to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", type=Path, required=True)
    parser.add_argument("--edam", type=Path, required=True)
    parser.add_argument("--content-revision", default="")
    parser.add_argument("--edam-revision", default="")
    args = parser.parse_args()
    main(args.dump, args.edam, args.content_revision, args.edam_revision)
