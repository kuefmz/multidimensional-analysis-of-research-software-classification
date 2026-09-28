#!/usr/bin/env python3
"""Write provenance metadata for a generated cross-ecosystem annotation pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def summarize_pilot(path: Path) -> dict[str, object]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    by_source: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_bucket: dict[str, int] = {}
    for row in rows:
        source = row.get("source", "")
        label_type = row.get("raw_label_type", "")
        bucket = row.get("frequency_bucket", "")
        by_source[source] = by_source.get(source, 0) + 1
        by_type[label_type] = by_type.get(label_type, 0) + 1
        by_bucket[bucket] = by_bucket.get(bucket, 0) + 1

    return {
        "rows": len(rows),
        "by_source": dict(sorted(by_source.items())),
        "by_native_label_type": dict(sorted(by_type.items())),
        "by_frequency_bucket": dict(sorted(by_bucket.items())),
    }


def main(
    pilot: Path,
    output: Path,
    source_inputs: list[Path],
    notes: str,
) -> None:
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pilot_file": str(pilot),
        "pilot_sha256": sha256_file(pilot),
        "pilot_summary": summarize_pilot(pilot),
        "source_inputs": [
            {
                "path": str(path),
                "sha256": sha256_file(path),
            }
            for path in source_inputs
        ],
        "notes": notes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-input", type=Path, action="append", default=[])
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    main(args.pilot, args.output, args.source_input, args.notes)
