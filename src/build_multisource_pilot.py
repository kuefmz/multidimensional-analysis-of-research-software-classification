#!/usr/bin/env python3
"""Build a balanced multi-source RQ1 annotation pilot from typed frequency tables.

The sampler operates on source-specific frequency CSVs rather than raw records. It:
1. preserves source and raw label type;
2. samples across common/medium/repeated/singleton frequency buckets;
3. limits domination by any one ecosystem;
4. keeps semantic annotation columns blank.

This is intended for the post-JOSS cross-ecosystem pilot.
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


SEED = 42

BUCKET_ORDER = ("common", "medium", "repeated", "singleton")
BUCKET_PROPORTIONS = {
    "common": 0.30,
    "medium": 0.30,
    "repeated": 0.20,
    "singleton": 0.20,
}


def frequency_bucket(value: int) -> str:
    if value >= 10:
        return "common"
    if value >= 3:
        return "medium"
    if value == 2:
        return "repeated"
    return "singleton"


def read_frequency_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"raw_label_type", "normalized_label", "frequency"}
    if rows and not required.issubset(rows[0]):
        missing = sorted(required - set(rows[0]))
        raise ValueError(f"{path} is missing required columns: {missing}")
    return rows


def source_name(row: dict[str, str], fallback: str) -> str:
    return (row.get("source") or fallback).strip()


def sample_rows(
    rows: list[dict[str, str]],
    target: int,
    rng: random.Random,
) -> list[dict[str, str]]:
    if len(rows) <= target:
        return list(rows)

    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        buckets[frequency_bucket(int(row["frequency"]))].append(row)

    quotas = {
        name: int(target * BUCKET_PROPORTIONS[name])
        for name in BUCKET_ORDER
    }
    while sum(quotas.values()) < target:
        for name in BUCKET_ORDER:
            if sum(quotas.values()) >= target:
                break
            quotas[name] += 1

    selected: list[dict[str, str]] = []
    chosen_keys: set[tuple[str, str]] = set()

    for name in BUCKET_ORDER:
        candidates = buckets.get(name, [])
        take = min(quotas[name], len(candidates))
        for row in rng.sample(candidates, take):
            key = (row["raw_label_type"], row["normalized_label"])
            if key not in chosen_keys:
                selected.append(row)
                chosen_keys.add(key)

    if len(selected) < target:
        remaining = [
            row for row in rows
            if (row["raw_label_type"], row["normalized_label"]) not in chosen_keys
        ]
        selected.extend(rng.sample(remaining, min(target - len(selected), len(remaining))))

    return selected[:target]


def sample_source_by_label_type(
    rows: list[dict[str, str]],
    target: int,
    rng: random.Random,
) -> list[dict[str, str]]:
    """Balance native label types within one ecosystem, then frequency-stratify."""
    by_type: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_type[row["raw_label_type"]].append(row)

    label_types = sorted(by_type)
    if not label_types:
        return []

    base = target // len(label_types)
    remainder = target % len(label_types)
    allocations = {
        label_type: min(
            len(by_type[label_type]),
            base + (1 if index < remainder else 0),
        )
        for index, label_type in enumerate(label_types)
    }

    # Redistribute quota from small native label types to types with remaining capacity.
    unfilled = target - sum(allocations.values())
    while unfilled > 0:
        progressed = False
        for label_type in label_types:
            if allocations[label_type] < len(by_type[label_type]):
                allocations[label_type] += 1
                unfilled -= 1
                progressed = True
                if unfilled == 0:
                    break
        if not progressed:
            break

    selected: list[dict[str, str]] = []
    for label_type in label_types:
        selected.extend(
            sample_rows(by_type[label_type], allocations[label_type], rng)
        )
    return selected


def balanced_sample(
    source_rows: dict[str, list[dict[str, str]]],
    total_size: int,
    seed: int = SEED,
) -> list[dict[str, str]]:
    if not source_rows:
        return []

    rng = random.Random(seed)
    sources = sorted(source_rows)
    base = total_size // len(sources)
    remainder = total_size % len(sources)

    selected: list[dict[str, str]] = []
    for index, source in enumerate(sources):
        target = base + (1 if index < remainder else 0)
        sampled = sample_source_by_label_type(source_rows[source], target, rng)
        for row in sampled:
            row = dict(row)
            row["_sample_source"] = source
            selected.append(row)

    return selected


def write_pilot(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "pilot_id",
        "source",
        "raw_label_type",
        "normalized_label",
        "example_raw_label",
        "frequency",
        "frequency_bucket",
        "example_context",
        "example_url",
        "primary_facet",
        "proposed_facet",
        "confidence",
        "annotation_note",
    ]

    context_fields = (
        "example_software",
        "example_paper_title",
        "example_raw_label",
    )
    url_fields = (
        "example_repository_url",
        "example_paper_url",
        "example_url",
        "raw_label_uri",
    )

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows, start=1):
            context = next((row.get(field, "") for field in context_fields if row.get(field)), "")
            url = next((row.get(field, "") for field in url_fields if row.get(field)), "")
            writer.writerow(
                {
                    "pilot_id": f"MULTI-{index:03d}",
                    "source": row.get("_sample_source") or row.get("source", ""),
                    "raw_label_type": row["raw_label_type"],
                    "normalized_label": row["normalized_label"],
                    "example_raw_label": row.get("example_raw_label") or row.get("raw_label", ""),
                    "frequency": row["frequency"],
                    "frequency_bucket": frequency_bucket(int(row["frequency"])),
                    "example_context": context,
                    "example_url": url,
                    "primary_facet": "",
                    "proposed_facet": "",
                    "confidence": "",
                    "annotation_note": "",
                }
            )


def main(inputs: list[Path], output: Path, size: int, seed: int) -> None:
    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for path in inputs:
        fallback = path.stem.replace("_label_frequencies", "")
        for row in read_frequency_csv(path):
            eligibility = (row.get("pilot_eligible") or "true").strip().lower()
            if eligibility == "false":
                continue
            by_source[source_name(row, fallback)].append(row)

    sampled = balanced_sample(dict(by_source), total_size=size, seed=seed)
    write_pilot(output, sampled)

    print(f"Sources: {', '.join(sorted(by_source))}")
    for source in sorted(by_source):
        n = sum(1 for row in sampled if row["_sample_source"] == source)
        print(f"  {source}: {n} sampled labels from {len(by_source[source])} candidates")
    print(f"Wrote {len(sampled)} labels to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    main(args.inputs, args.output, args.size, args.seed)
