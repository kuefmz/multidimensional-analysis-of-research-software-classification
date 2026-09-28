# Multidimensional Analysis of Research Software Classification

This repository implements the empirical pipeline for studying the semantic dimensions used to classify research software across existing ecosystems.

## Research workflow

The implementation follows three stages:

1. **RQ1 — semantic-dimension discovery:** collect classification labels from multiple ecosystems, preserve source provenance, normalize surface forms, and manually identify the semantic dimensions represented by the labels.
2. **RQ2 — facet framework:** align normalized concepts and organize them into an explicit multidimensional/faceted representation.
3. **RQ3 — validation:** evaluate held-out coverage, inter-annotator agreement, cross-source alignment, and raw-vs-normalized-vs-faceted ablations.

The current implementation on `dev` starts with the JOSS seed corpus before adding additional ecosystems.

## Current status

Implemented on `dev`:

- source registry and explicit source roles;
- provisional RQ1 facet codebook with `Other` and `Unclear`;
- immutable raw-data/provenance policy;
- frozen JOSS seed pipeline with separate JOSS-tag and repository-topic provenance;
- deterministic 50-label pilot balanced by source and frequency bucket;
- tracked clean pilot plus a separate assistant exploratory coding pass;
- annotation guidelines, agreement preparation, observed agreement and Cohen's kappa code;
- SemRepo SPARQL diagnostic collector and full streaming Zenodo N-Triples collector;
- bio.tools EDAM Topic/Operation collector (local/permitted execution; hosted runner currently receives HTTP 521);
- Papers with Code adapter that reuses the frozen merged snapshot from the previous project;
- canonical record JSON Schema;
- source audit, unit tests and CI.

### JOSS seed snapshot

The frozen Andrew CSV contains **3,278 data records** (3,279 CSV lines including the
header). The current extraction contains:

- **7,338** distinct normalized JOSS tags from **14,124** assignments;
- **5,757** distinct normalized repository topics from **11,133** assignments.

The 50-label pilot contains 25 JOSS tags and 25 repository topics and includes source
context for ambiguous labels.

### SemRepo source decision

The 2026-09-28 endpoint audit exposed only **952** repository entities, so the live
endpoint is not used as the primary study snapshot. The full versioned Zenodo N-Triples
release is the primary SemRepo path; `src/semrepo_dump_collector.py` processes it as a
stream and uses SQLite only for the language-reference join.

### Pilot facet stress test

The exploratory coding pass suggests that the seed facets may be missing recurring
dimensions such as **Object / Phenomenon of Study**, **Organization / Institution**,
**Data Format**, and **Publication / Curation Status**. These remain candidate facets
until human pilot adjudication.

See `docs/source_audit.md` for source-specific decisions and limitations.

## Run the JOSS seed pipeline

Requires Python 3.10+ and uses only the Python standard library for the data preparation step.

```bash
python src/joss_seed_pipeline.py
```

This creates local, reproducible research artifacts:

```text
data/raw/joss/joss_keywords.csv
data/raw/joss/provenance.json
data/interim/joss_extracted_labels.csv
data/interim/joss_label_frequencies.csv
data/annotations/joss_pilot_50.csv
```

Raw and generated data are intentionally excluded from Git. The frozen source URL and expected record count are tracked in `configs/sources.yaml`.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

## Important methodological rule

The seed facets in `configs/facets.yaml` are **not the final taxonomy**. They are a pilot annotation codebook. Annotators may select `Other` and propose a new facet, or select `Unclear`. RQ1 is allowed to add, merge, split or remove facets based on empirical annotation evidence.

Similarly, lexical normalization does not merge semantic synonyms. For example, `NLP` and `natural language processing` remain distinct until a separate concept-alignment step provides evidence that they should be mapped to one canonical concept.
