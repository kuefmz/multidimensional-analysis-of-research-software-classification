# Data workflow

This directory separates immutable source snapshots from derived research data.

## Layout

- `raw/`: exact downloaded source snapshots. Raw data are not committed.
- `interim/`: extracted and normalized labels. Generated, not committed.
- `annotations/`: human annotation inputs/outputs that form part of the research record.
- `processed/`: canonical concept and facet mappings. Generated, not committed.

## Provenance rule

Every collector must preserve:

1. source name,
2. source record identifier,
3. raw label,
4. raw label type,
5. retrieval timestamp or snapshot identifier,
6. source URL when available.

Normalization must never overwrite the raw label.

## JOSS seed

Run:

```bash
python src/joss_seed_pipeline.py
```

The script downloads the frozen JOSS keyword CSV, stores the unchanged snapshot under
`data/raw/joss/`, records its SHA256 checksum, extracts unique labels and frequencies,
and creates a deterministic 50-label pilot for the first annotation round.
