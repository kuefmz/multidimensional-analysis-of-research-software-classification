# Source audit

This document records source-specific decisions made during implementation so that RQ1
does not silently mix different notions of "classification".

## JOSS / linked GitHub metadata

Frozen source: Andrew's `joss_keywords.csv`.

Observed schema:

- `joss_tags`
- `repository_topics`
- `combined_keywords`

Decision: keep JOSS tags and repository topics as separate provenance types. Ignore
`combined_keywords` during extraction because it combines the two and would double
count labels.

The frozen CSV has 3,278 data rows (3,279 lines including the header). It yielded:

- 7,338 distinct normalized JOSS tags;
- 5,757 distinct normalized repository topics;
- 14,124 JOSS-tag assignments;
- 11,133 repository-topic assignments.

A deterministic 50-label pilot is tracked in `data/annotations/`.

## SemRepo

The 2026-09-28 public endpoint audit returned only 952 repository entities, of which 166
had a topic and 907 had a programming-language reference. This is far smaller than the
released SemRepo corpus and therefore the endpoint must not be treated as the primary
study snapshot.

Decision: use the versioned Zenodo N-Triples dump (record 20084784) for the full RQ1
analysis. The repository contains a streaming collector using SQLite only for the
language-reference join, so the graph does not need to fit in memory.

Initial RQ1 fields:

- repository topic;
- programming language.

Packages are excluded initially because dependencies are implementation metadata rather
than explicit classification labels.

## bio.tools

Initial semantic fields:

- EDAM Topic;
- EDAM Operation.

EDAM Data, Format, tool type, language, and operating system are deliberately excluded
from the first pass. They may be added later if RQ1 is explicitly broadened to include
all structured software descriptors.

The collector's unit tests pass. A GitHub-hosted connectivity test on 2026-09-28 received
HTTP 521 from the production API. For that reason the Actions smoke test is manual-only;
the collector remains runnable from a local/permitted environment and the failure is not
treated as a schema/parsing failure.

## Papers with Code

Do not re-scrape by default. The earlier research-software-classification project already
created a frozen merged snapshot,
`data/pwc_merged/pwc_merged_relevant_attributes.jsonl`.

That snapshot preserves four useful classification-like layers:

- tasks;
- methods;
- method collections;
- main collection areas.

`src/paperswithcode_snapshot_adapter.py` converts that frozen snapshot into the same
typed frequency-table form used by this project.

## Important distinction from previous "semantic dimension coverage"

The earlier project includes `scripts/compute_semantic_dimension_coverage.py`. That
script measures whether broad **metadata fields** such as software name, description,
publication metadata, documentation and labels are populated.

The present RQ1 instead studies the **semantic meaning of classification labels** (e.g.,
domain vs function vs method vs technology). The old coverage table is therefore useful
background but is not evidence for the new semantic-dimension results.


## 2026-09-28 full Papers with Code execution

The complete frozen Hugging Face archive was streamed successfully:

- 576,261 papers processed;
- 469,717 papers with at least one extracted classification label;
- 19,963 distinct typed label rows;
- 4,795 tasks;
- 14,827 methods;
- 313 method collections;
- 21 collection-parent labels;
- 7 areas.

A subsequent structural quality audit found substantial archive pollution in the PwC
method vocabulary. The raw frequency table is preserved; flagged rows are excluded only
from annotation-pilot sampling. See `docs/pwc_label_quality_audit.md`.

## bio.tools static-source validation

The `research-software-ecosystem/content` repository provides original
`*.biotools.biotools.json.backup` files that preserve canonical EDAM terms and URIs.
A complete pass over the available backups found 2,473 files, all parseable. This is a
useful validation subset, but it is too small to stand in for the full bio.tools
ecosystem.

The repository also publishes a merged `datasets/bioschemas-dump.ttl`. The RQ1
pipeline therefore has a second collector that filters the merged graph to software
records linked to a bio.tools identifier and extracts only EDAM Topic and Operation.
The first graph-level run exposed representation/namespace differences in the merged
dump; zero-record output is explicitly treated as an error rather than accepted as a
valid empty source.
