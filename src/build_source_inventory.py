#!/usr/bin/env python3
"""Build source-level RQ1 inventory and exact lexical-overlap tables.

This is deliberately pre-semantic: overlap is computed only on normalized surface
labels. It must not be interpreted as semantic equivalence. Later facet mapping can be
compared against this lexical baseline.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if rows and "normalized_label" not in rows[0]:
        raise ValueError(f"{path} has no normalized_label column")
    return rows


def infer_source(row: dict[str, str], path: Path) -> str:
    value = (row.get("source") or "").strip()
    return value or path.stem.replace("_label_frequencies", "")


def bucket(freq: int) -> str:
    if freq >= 10:
        return "common"
    if freq >= 3:
        return "medium"
    if freq == 2:
        return "repeated"
    return "singleton"


def build_inventory(paths: list[Path]) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in paths:
        for row in read_rows(path):
            by_source[infer_source(row, path)].append(row)

    inventory: list[dict[str, object]] = []
    label_sets: dict[str, set[str]] = {}
    for source, rows in sorted(by_source.items()):
        labels = {row["normalized_label"].strip() for row in rows if row["normalized_label"].strip()}
        label_sets[source] = labels
        bucket_counts = Counter(bucket(int(row.get("frequency") or 0)) for row in rows)
        inventory.append(
            {
                "source": source,
                "typed_label_rows": len(rows),
                "distinct_normalized_surface_labels": len(labels),
                "common_rows": bucket_counts["common"],
                "medium_rows": bucket_counts["medium"],
                "repeated_rows": bucket_counts["repeated"],
                "singleton_rows": bucket_counts["singleton"],
                "total_assignments": sum(int(row.get("frequency") or 0) for row in rows),
                "raw_label_types": "|".join(sorted({row.get("raw_label_type", "") for row in rows if row.get("raw_label_type")})),
            }
        )

    overlaps: list[dict[str, object]] = []
    for left, right in itertools.combinations(sorted(label_sets), 2):
        a = label_sets[left]
        b = label_sets[right]
        intersection = a & b
        union = a | b
        overlaps.append(
            {
                "source_a": left,
                "source_b": right,
                "source_a_labels": len(a),
                "source_b_labels": len(b),
                "exact_shared_labels": len(intersection),
                "jaccard_surface_overlap": len(intersection) / len(union) if union else 0.0,
                "shared_examples": "|".join(sorted(intersection)[:20]),
            }
        )

    all_sources_per_label: dict[str, set[str]] = defaultdict(set)
    for source, labels in label_sets.items():
        for label in labels:
            all_sources_per_label[label].add(source)

    summary = {
        "sources": sorted(by_source),
        "source_count": len(by_source),
        "union_normalized_surface_labels": len(all_sources_per_label),
        "labels_seen_in_multiple_sources": sum(len(sources) >= 2 for sources in all_sources_per_label.values()),
        "labels_seen_in_all_sources": sum(
            len(sources) == len(by_source) for sources in all_sources_per_label.values()
        ) if by_source else 0,
        "interpretation": (
            "Exact normalized-label overlap only; do not treat as semantic equivalence."
        ),
    }
    return inventory, overlaps, summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(inputs: list[Path], output_dir: Path) -> None:
    inventory, overlaps, summary = build_inventory(inputs)
    write_csv(output_dir / "source_inventory.csv", inventory)
    write_csv(output_dir / "exact_surface_overlap.csv", overlaps)
    (output_dir / "source_inventory_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("results/rq1"))
    args = parser.parse_args()
    main(args.inputs, args.output_dir)
