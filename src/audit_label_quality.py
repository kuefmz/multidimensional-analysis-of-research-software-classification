#!/usr/bin/env python3
"""Audit typed label frequency tables for annotation-pilot eligibility.

The raw/source frequency table is never modified. This script adds transparent,
conservative quality flags for rows that are poor annotation units, especially
archive pollution in very rare free-text labels.

Flags are structural rather than topic-specific:
- empty / effectively empty label;
- URL or email-like text;
- unusually long free-text phrase;
- high punctuation density;
- likely phone-number/contact text.

The output is evidence for pilot sampling only. Flagged labels remain part of the
source audit and may be reviewed manually.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


URL_RE = re.compile(r"https?://|www\.", re.I)
EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")


def quality_reasons(label: str) -> list[str]:
    text = (label or "").strip()
    reasons: list[str] = []
    if len(text) < 2:
        reasons.append("too_short")
        return reasons

    if URL_RE.search(text):
        reasons.append("contains_url")
    if EMAIL_RE.search(text):
        reasons.append("contains_email")
    digit_count = sum(ch.isdigit() for ch in text)
    if PHONE_RE.search(text) or (len(text) >= 15 and digit_count >= 8):
        reasons.append("phone_like")

    words = WORD_RE.findall(text)
    if len(words) > 14:
        reasons.append("long_free_text")
    if len(text) > 140:
        reasons.append("very_long_label")

    non_alnum = sum(not ch.isalnum() and not ch.isspace() for ch in text)
    if len(text) >= 20 and non_alnum / len(text) > 0.22:
        reasons.append("high_punctuation_density")

    return reasons


def audit_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    audited = []
    for row in rows:
        out = dict(row)
        reasons = quality_reasons(row.get("normalized_label") or row.get("raw_label") or "")
        out["pilot_eligible"] = "false" if reasons else "true"
        out["pilot_exclusion_reasons"] = "|".join(reasons)
        audited.append(out)
    return audited


def main(input_path: Path, output_path: Path) -> None:
    with input_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    audited = audit_rows(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(audited[0]) if audited else []
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(audited)

    flagged = [row for row in audited if row["pilot_eligible"] == "false"]
    print(f"Rows: {len(audited):,}")
    print(f"Pilot eligible: {len(audited)-len(flagged):,}")
    print(f"Flagged for manual review/exclusion: {len(flagged):,}")
    for row in flagged[:20]:
        print(
            row.get("raw_label_type"),
            row.get("frequency"),
            row.get("normalized_label"),
            row["pilot_exclusion_reasons"],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.input, args.output)
