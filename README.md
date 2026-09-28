# Multidimensional Analysis of Research Software Classification

This repository implements the empirical pipeline for studying the semantic dimensions used to classify research software across existing ecosystems.

## Research workflow

The implementation follows three stages:

1. **RQ1 — semantic-dimension discovery:** collect classification labels from multiple ecosystems, preserve source provenance, normalize surface forms, and manually identify the semantic dimensions represented by the labels.
2. **RQ2 — facet framework:** align normalized concepts and organize them into an explicit multidimensional/faceted representation.
3. **RQ3 — validation:** evaluate held-out coverage, inter-annotator agreement, cross-source alignment, and raw-vs-normalized-vs-faceted ablations.

The current implementation on `dev` starts with the JOSS seed corpus before adding additional ecosystems.

## Current status

Implemented:

- source registry and explicit source roles;
- provisional RQ1 facet codebook with `Other` and `Unclear`;
- immutable raw-data/provenance policy;
- frozen JOSS seed downloader;
- conservative lexical normalization;
- canonical extracted-label table;
- label-frequency table;
- deterministic frequency-stratified 50-label annotation pilot;
- pilot annotation guidelines;
- canonical record JSON Schema;
- unit tests and CI.

Planned next:

- run and inspect the JOSS pilot;
- revise the facet codebook based on disagreements;
- add SemRepo as source #2;
- add bio.tools and Papers with Code/LPWC;
- expand to OpenAlex, OpenAIRE, GitHub and ORKG;
- keep Awesome Lists held out for RQ3 validation.

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
