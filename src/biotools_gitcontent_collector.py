#!/usr/bin/env python3
"""Collect bio.tools EDAM labels from the static Git content snapshot.

Primary snapshot source:
    https://github.com/research-software-ecosystem/content

The repository preserves current native bio.tools JSON records under:
    data/*/*.biotools.json

This path is preferred over the live bio.tools API for reproducibility and because
hosted runners observed HTTP 521 from the production API on 2026-09-28. Backup files
are deliberately ignored so each current tool is counted once.

Extracted native classification dimensions:
- EDAM Topic
- EDAM Operation
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


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "interim"
RAW_META_DIR = ROOT / "data" / "raw" / "biotools"


def normalize_surface(label: str) -> str:
    text = unicodedata.normalize("NFKC", label or "")
    text = text.strip().lower()
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def iter_concepts(tool: dict) -> set[tuple[str, str, str]]:
    concepts: set[tuple[str, str, str]] = set()

    for topic in tool.get("topic") or []:
        if not isinstance(topic, dict):
            continue
        term = str(topic.get("term") or "").strip()
        uri = str(topic.get("uri") or "").strip()
        if term or uri:
            concepts.add(("edam_topic", term or uri.rsplit("/", 1)[-1], uri))

    for function in tool.get("function") or []:
        if not isinstance(function, dict):
            continue
        for operation in function.get("operation") or []:
            if not isinstance(operation, dict):
                continue
            term = str(operation.get("term") or "").strip()
            uri = str(operation.get("uri") or "").strip()
            if term or uri:
                concepts.add(("edam_operation", term or uri.rsplit("/", 1)[-1], uri))

    return concepts


def collect(input_root: Path) -> tuple[list[dict[str, object]], dict[str, object]]:
    paths = sorted(input_root.glob("data/*/*.biotools.json"))
    if not paths:
        raise FileNotFoundError(
            f"No current bio.tools JSON files found below {input_root}/data. "
            "Expected data/*/*.biotools.json"
        )

    assignments: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    examples: dict[tuple[str, str, str], tuple[str, str]] = {}
    parsed = 0
    invalid = 0
    tools_with_topic = 0
    tools_with_operation = 0

    for path in paths:
        try:
            tool = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            invalid += 1
            continue

        parsed += 1
        tool_id = str(tool.get("biotoolsID") or path.parent.name)
        tool_name = str(tool.get("name") or tool_id)
        homepage = str(tool.get("homepage") or "")

        concepts = iter_concepts(tool)
        if any(label_type == "edam_topic" for label_type, _, _ in concepts):
            tools_with_topic += 1
        if any(label_type == "edam_operation" for label_type, _, _ in concepts):
            tools_with_operation += 1

        for concept in concepts:
            assignments[concept].add(tool_id)
            examples.setdefault(concept, (tool_name, homepage))

    rows: list[dict[str, object]] = []
    for (label_type, raw_label, uri), tool_ids in assignments.items():
        example_name, example_url = examples[(label_type, raw_label, uri)]
        rows.append(
            {
                "source": "biotools",
                "raw_label": raw_label,
                "raw_label_uri": uri,
                "raw_label_type": label_type,
                "normalized_label": normalize_surface(raw_label),
                "frequency": len(tool_ids),
                "example_software": example_name,
                "example_url": example_url,
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
        "current_json_files_found": len(paths),
        "current_json_files_parsed": parsed,
        "invalid_json_files": invalid,
        "tools_with_edam_topic": tools_with_topic,
        "tools_with_edam_operation": tools_with_operation,
        "distinct_typed_labels": len(rows),
        "by_type": {},
    }
    for label_type in ("edam_topic", "edam_operation"):
        typed = [row for row in rows if row["raw_label_type"] == label_type]
        stats["by_type"][label_type] = {
            "distinct_labels": len(typed),
            "tool_label_assignments": sum(int(row["frequency"]) for row in typed),
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
        "example_software",
        "example_url",
        "normalization_method",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(input_root: Path, source_revision: str = "") -> None:
    rows, stats = collect(input_root)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_META_DIR.mkdir(parents=True, exist_ok=True)

    output = OUT_DIR / "biotools_label_frequencies.csv"
    write_csv(output, rows)

    provenance = {
        "source": "bio.tools via research-software-ecosystem/content",
        "source_repository": "https://github.com/research-software-ecosystem/content",
        "source_revision": source_revision or None,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_mode": "static_git_current_native_biotools_json",
        "classification_fields": ["edam_topic", "edam_operation"],
        "excluded_initial_fields": [
            "edam_data",
            "edam_format",
            "tool_type",
            "programming_language",
            "operating_system",
        ],
        "stats": stats,
    }
    (RAW_META_DIR / "gitcontent_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(provenance, indent=2))
    print(f"Wrote {len(rows):,} typed labels to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--source-revision", default="")
    args = parser.parse_args()
    main(args.input, args.source_revision)
