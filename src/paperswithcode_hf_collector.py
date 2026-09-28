#!/usr/bin/env python3
"""Collect Papers with Code semantic labels from the frozen Hugging Face archive.

Primary public snapshot:
    pwc-archive/papers-with-abstracts

The archive is frozen and corresponds to the final public Papers with Code data.
We stream rows so the ~576k-paper dataset does not need to be loaded into memory.

Extracted classification-like layers:
- task
- method
- method collection
- method collection area

The nested method schema mirrors the original PwC export used by the earlier project.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "interim"
RAW_META_DIR = ROOT / "data" / "raw" / "papers_with_code"
DATASET_ID = "pwc-archive/papers-with-abstracts"
DATASET_REVISION = "main"


def normalize_surface(label: str) -> str:
    text = unicodedata.normalize("NFKC", label or "")
    text = text.strip().lower()
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def extract_typed_labels(record: dict[str, Any]) -> set[tuple[str, str]]:
    """Extract typed labels, deduplicated within one paper."""
    labels: set[tuple[str, str]] = set()

    for task in record.get("tasks") or []:
        if isinstance(task, dict):
            term = clean(task.get("task") or task.get("name") or task.get("title"))
        else:
            term = clean(task)
        if term:
            labels.add(("pwc_task", term))

    for method in record.get("methods") or []:
        if not isinstance(method, dict):
            term = clean(method)
            if term:
                labels.add(("pwc_method", term))
            continue

        method_name = clean(method.get("name") or method.get("full_name"))
        if method_name:
            labels.add(("pwc_method", method_name))

        collection = method.get("main_collection") or {}
        if isinstance(collection, dict):
            collection_name = clean(collection.get("name"))
            area = clean(collection.get("area"))
            parent = clean(collection.get("parent"))
            if collection_name:
                labels.add(("pwc_method_collection", collection_name))
            if area:
                labels.add(("pwc_area", area))
            # Parent is preserved as its own typed level because it may encode
            # a broader methodological grouping than the collection itself.
            if parent:
                labels.add(("pwc_collection_parent", parent))

    return labels


def aggregate_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    counts: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], tuple[str, str]] = {}
    paper_count = 0
    papers_with_labels = 0

    for index, record in enumerate(records, start=1):
        paper_count += 1
        typed = extract_typed_labels(record)
        if typed:
            papers_with_labels += 1

        title = clean(record.get("title"))
        paper_url = clean(record.get("paper_url") or record.get("url_abs") or record.get("arxiv_id"))

        for key in typed:
            counts[key] += 1
            examples.setdefault(key, (title, paper_url))

    rows: list[dict[str, object]] = []
    for (label_type, raw_label), frequency in counts.items():
        title, paper_url = examples[(label_type, raw_label)]
        rows.append(
            {
                "source": "papers_with_code",
                "raw_label": raw_label,
                "raw_label_type": label_type,
                "normalized_label": normalize_surface(raw_label),
                "frequency": frequency,
                "example_paper_title": title,
                "example_paper_url": paper_url,
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
        "papers_processed": paper_count,
        "papers_with_at_least_one_extracted_label": papers_with_labels,
        "distinct_typed_labels": len(rows),
        "by_type": {},
    }
    for label_type in sorted({str(row["raw_label_type"]) for row in rows}):
        typed = [row for row in rows if row["raw_label_type"] == label_type]
        stats["by_type"][label_type] = {
            "distinct_labels": len(typed),
            "paper_label_assignments": sum(int(row["frequency"]) for row in typed),
        }

    return rows, stats


def iter_huggingface_records(limit: int | None = None) -> Iterator[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError(
            "The Hugging Face collector requires the optional 'datasets' package. "
            "Install it with: pip install datasets"
        ) from exc

    dataset = load_dataset(
        DATASET_ID,
        split="train",
        streaming=True,
        revision=DATASET_REVISION,
    )

    for index, row in enumerate(dataset):
        if limit is not None and index >= limit:
            break
        yield row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "source",
        "raw_label",
        "raw_label_type",
        "normalized_label",
        "frequency",
        "example_paper_title",
        "example_paper_url",
        "normalization_method",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(limit: int | None = None) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_META_DIR.mkdir(parents=True, exist_ok=True)

    rows, stats = aggregate_records(iter_huggingface_records(limit=limit))
    output = OUT_DIR / "paperswithcode_label_frequencies.csv"
    write_csv(output, rows)

    provenance = {
        "source": "Papers with Code public archive",
        "dataset_id": DATASET_ID,
        "dataset_revision": DATASET_REVISION,
        "accessed_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "huggingface_streaming",
        "limit": limit,
        "complete_snapshot": limit is None,
        "classification_fields": [
            "task",
            "method",
            "method_collection",
            "collection_parent",
            "method_collection_area",
        ],
        "stats": stats,
    }
    (RAW_META_DIR / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(provenance, indent=2))
    print(f"Wrote {len(rows):,} typed labels to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row limit for smoke tests. Omit for the full frozen snapshot.",
    )
    args = parser.parse_args()
    main(limit=args.limit)
