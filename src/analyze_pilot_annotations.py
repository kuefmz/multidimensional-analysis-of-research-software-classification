#!/usr/bin/env python3
"""Summarize RQ1 pilot annotation files and prepare paired agreement data."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


SPECIAL = {"", "Unclear", "Other"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def summarize(rows: list[dict[str, str]]) -> dict[str, object]:
    facets = Counter((row.get("primary_facet") or "").strip() for row in rows)
    proposed = Counter(
        (row.get("proposed_facet") or "").strip()
        for row in rows
        if (row.get("proposed_facet") or "").strip()
    )
    confidences = []
    for row in rows:
        value = (row.get("confidence") or "").strip()
        if value:
            try:
                confidences.append(float(value))
            except ValueError:
                pass

    annotated = sum(1 for row in rows if (row.get("primary_facet") or "").strip())
    unclear = facets.get("Unclear", 0)
    other = facets.get("Other", 0)

    return {
        "rows": len(rows),
        "annotated": annotated,
        "unannotated": len(rows) - annotated,
        "facet_counts": dict(sorted(facets.items())),
        "other_count": other,
        "unclear_count": unclear,
        "proposed_facet_counts": dict(proposed.most_common()),
        "mean_confidence": (
            sum(confidences) / len(confidences) if confidences else None
        ),
    }


def join_annotators(
    first: list[dict[str, str]],
    second: list[dict[str, str]],
) -> list[dict[str, str]]:
    a = {row["pilot_id"]: row for row in first if row.get("pilot_id")}
    b = {row["pilot_id"]: row for row in second if row.get("pilot_id")}
    shared = sorted(set(a) & set(b))
    return [
        {
            "pilot_id": pilot_id,
            "label": (
                a[pilot_id].get("normalized_label")
                or b[pilot_id].get("normalized_label")
                or ""
            ),
            "annotator_1_facet": a[pilot_id].get("primary_facet", ""),
            "annotator_2_facet": b[pilot_id].get("primary_facet", ""),
            "agreement": str(
                a[pilot_id].get("primary_facet", "")
                == b[pilot_id].get("primary_facet", "")
            ).lower(),
        }
        for pilot_id in shared
    ]


def observed_agreement(rows: list[dict[str, str]]) -> float | None:
    if not rows:
        return None
    return sum(row["agreement"] == "true" for row in rows) / len(rows)


def cohen_kappa(rows: list[dict[str, str]]) -> float | None:
    """Cohen's kappa over primary facet labels, including Other/Unclear as categories."""
    if not rows:
        return None

    pairs = [
        (row["annotator_1_facet"], row["annotator_2_facet"])
        for row in rows
        if row["annotator_1_facet"] and row["annotator_2_facet"]
    ]
    if not pairs:
        return None

    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    counts_a = Counter(a for a, _ in pairs)
    counts_b = Counter(b for _, b in pairs)
    categories = set(counts_a) | set(counts_b)
    expected = sum(
        (counts_a[category] / n) * (counts_b[category] / n)
        for category in categories
    )
    if expected == 1:
        return 1.0 if observed == 1 else None
    return (observed - expected) / (1 - expected)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "pilot_id",
        "label",
        "annotator_1_facet",
        "annotator_2_facet",
        "agreement",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(paths: list[Path], paired_output: Path | None = None) -> None:
    if not paths:
        raise ValueError("Provide at least one annotation CSV.")

    annotations = [read_rows(path) for path in paths]
    report = {
        str(path): summarize(rows)
        for path, rows in zip(paths, annotations)
    }

    if len(annotations) == 2:
        paired = join_annotators(annotations[0], annotations[1])
        report["agreement"] = {
            "shared_items": len(paired),
            "observed_agreement": observed_agreement(paired),
            "cohen_kappa": cohen_kappa(paired),
        }
        if paired_output is not None:
            write_csv(paired_output, paired)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("annotations", nargs="+", type=Path)
    parser.add_argument("--paired-output", type=Path, default=None)
    args = parser.parse_args()
    main(args.annotations, paired_output=args.paired_output)
