#!/usr/bin/env python3
"""Collect controlled bio.tools classification labels for RQ1.

The first extraction is intentionally limited to the two controlled EDAM annotation
families that most directly behave as classification dimensions in bio.tools:

- EDAM Topic: general scientific domain / category;
- EDAM Operation: function or operation performed by the software.

Other metadata (data types, formats, tool type, language, operating system) are kept out
of this first pass so RQ1 does not silently broaden from "classification labels" to all
software metadata. They can be added later as an explicitly separate analysis.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
import unicodedata
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "interim"
RAW_META_DIR = ROOT / "data" / "raw" / "biotools"
API_URL = "https://bio.tools/api/tool/"


def normalize_surface(label: str) -> str:
    text = unicodedata.normalize("NFKC", label or "")
    text = text.strip().lower()
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def fetch_page(page: int, per_page: int = 100, timeout: int = 120, retries: int = 3) -> dict:
    params = urlencode(
        {
            "page": page,
            "per_page": per_page,
            "format": "json",
            "sort": "name",
            "ord": "asc",
        }
    )
    request = Request(
        f"{API_URL}?{params}",
        headers={
            "Accept": "application/json",
            "User-Agent": "research-software-classification-analysis/0.1",
        },
    )

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except Exception as exc:  # network/API failures are retried, then surfaced
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
    assert last_error is not None
    raise last_error


def iter_concepts(tool: dict) -> list[tuple[str, str, str]]:
    """Return (label_type, term, uri) tuples, deduplicated within a tool."""
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

    return sorted(concepts)


def aggregate_tools(tools: list[dict]) -> dict[tuple[str, str, str], set[str]]:
    assignments: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for index, tool in enumerate(tools, start=1):
        tool_id = str(tool.get("biotoolsID") or tool.get("name") or f"row-{index}")
        for concept in iter_concepts(tool):
            assignments[concept].add(tool_id)
    return assignments


def merge_assignments(
    target: dict[tuple[str, str, str], set[str]],
    incoming: dict[tuple[str, str, str], set[str]],
) -> None:
    for key, tool_ids in incoming.items():
        target[key].update(tool_ids)


def write_rows(assignments: dict[tuple[str, str, str], set[str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (label_type, term, uri), tool_ids in assignments.items():
        rows.append(
            {
                "source": "biotools",
                "raw_label": term,
                "raw_label_uri": uri,
                "raw_label_type": label_type,
                "normalized_label": normalize_surface(term),
                "frequency": len(tool_ids),
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


def main(per_page: int = 100, max_pages: int | None = None) -> None:
    first = fetch_page(1, per_page=per_page)
    total_tools = int(first.get("count", len(first.get("list", []))))
    total_pages = max(1, math.ceil(total_tools / per_page))
    pages_to_fetch = total_pages if max_pages is None else min(total_pages, max_pages)

    assignments: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    merge_assignments(assignments, aggregate_tools(first.get("list") or []))

    for page in range(2, pages_to_fetch + 1):
        payload = fetch_page(page, per_page=per_page)
        merge_assignments(assignments, aggregate_tools(payload.get("list") or []))

    rows = write_rows(assignments)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_META_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUT_DIR / "biotools_label_frequencies.csv", rows)

    stats = {}
    for label_type in ("edam_topic", "edam_operation"):
        typed = [row for row in rows if row["raw_label_type"] == label_type]
        stats[label_type] = {
            "distinct_labels": len(typed),
            "tool_label_assignments_in_fetched_pages": sum(int(row["frequency"]) for row in typed),
        }

    provenance = {
        "source": "bio.tools",
        "api": API_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "reported_tool_count": total_tools,
        "per_page": per_page,
        "reported_total_pages": total_pages,
        "pages_fetched": pages_to_fetch,
        "complete_snapshot": pages_to_fetch == total_pages,
        "classification_fields": ["edam_topic", "edam_operation"],
        "excluded_from_initial_rq1": [
            "EDAM Data",
            "EDAM Format",
            "toolType",
            "programming language",
            "operating system",
        ],
        "stats": stats,
    }
    (RAW_META_DIR / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()
    main(per_page=args.per_page, max_pages=args.max_pages)
