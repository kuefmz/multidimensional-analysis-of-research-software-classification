#!/usr/bin/env python3
"""Adapt the frozen Papers with Code corpus from the earlier project into RQ1 labels.

Primary input (already produced by the existing research-software pipeline):
    data/pwc_merged/pwc_merged_relevant_attributes.jsonl

Expected nested field:
    "papers with code categories": {
        "tasks": [...],
        "methods": [{ "method": ..., ... }],
        "collections": [...],
        "main_collection_areas": [...]
    }

This avoids re-scraping Papers with Code and preserves the previously frozen snapshot.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "interim"


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


def labels_from_record(record: dict) -> set[tuple[str, str]]:
    categories = record.get("papers with code categories") or {}
    if not isinstance(categories, dict):
        return set()

    labels: set[tuple[str, str]] = set()

    for task in categories.get("tasks") or []:
        term = clean(task)
        if term:
            labels.add(("pwc_task", term))

    for method in categories.get("methods") or []:
        if isinstance(method, dict):
            term = clean(method.get("method") or method.get("method_full_name"))
        else:
            term = clean(method)
        if term:
            labels.add(("pwc_method", term))

    for collection in categories.get("collections") or []:
        term = clean(collection)
        if term:
            labels.add(("pwc_method_collection", term))

    for area in categories.get("main_collection_areas") or []:
        term = clean(area)
        if term:
            labels.add(("pwc_area", term))

    return labels


def aggregate(path: Path) -> list[dict[str, object]]:
    assignments: dict[tuple[str, str], set[str]] = defaultdict(set)
    examples: dict[tuple[str, str], tuple[str, str]] = {}

    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            paper_id = clean(
                record.get("paper_url")
                or record.get("arxiv_id")
                or record.get("paper_title")
                or index
            )
            title = clean(record.get("paper_title"))
            repo = clean(record.get("github_repo"))
            for label_type, raw_label in labels_from_record(record):
                key = (label_type, raw_label)
                assignments[key].add(paper_id)
                examples.setdefault(key, (title, repo))

    rows: list[dict[str, object]] = []
    for (label_type, raw_label), paper_ids in assignments.items():
        title, repo = examples[(label_type, raw_label)]
        rows.append(
            {
                "source": "papers_with_code",
                "raw_label": raw_label,
                "raw_label_type": label_type,
                "normalized_label": normalize_surface(raw_label),
                "frequency": len(paper_ids),
                "example_paper_title": title,
                "example_repository_url": repo,
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
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "source",
        "raw_label",
        "raw_label_type",
        "normalized_label",
        "frequency",
        "example_paper_title",
        "example_repository_url",
        "normalization_method",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(input_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Frozen PwC merged JSONL not found: {input_path}. Copy or link the existing "
            "pwc_merged_relevant_attributes.jsonl snapshot from the previous project."
        )
    rows = aggregate(input_path)
    output = OUT_DIR / "paperswithcode_label_frequencies.csv"
    write_csv(output, rows)

    by_type = {}
    for label_type in sorted({str(row["raw_label_type"]) for row in rows}):
        typed = [row for row in rows if row["raw_label_type"] == label_type]
        by_type[label_type] = {
            "distinct_labels": len(typed),
            "paper_label_assignments": sum(int(row["frequency"]) for row in typed),
        }

    print(json.dumps({"input": str(input_path), "by_type": by_type}, indent=2))
    print(f"Wrote {len(rows):,} typed labels to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    main(args.input)
