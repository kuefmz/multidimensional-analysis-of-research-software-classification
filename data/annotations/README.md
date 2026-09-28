# Annotation data

Files in this directory are tracked research artifacts rather than disposable generated
intermediates.

## `joss_pilot_50.csv`

Deterministic 50-label RQ1 pilot generated from Andrew's frozen JOSS/GitHub corpus using
seed 42.

Sampling is balanced by label provenance:

- 25 JOSS tags
- 25 repository topics

Within each provenance group the sample deliberately includes common, medium-frequency,
repeated, and singleton labels. Context columns provide one example software/repository
for disambiguation, but the annotation target remains the classification label.

The semantic annotation columns are initially blank. The seed facet codebook is in
`../../configs/facets.yaml` and the procedure is documented in
`../../annotations/annotation_guidelines.md`.

The frozen input contains 3,278 data records (3,279 CSV lines including its header),
7,338 distinct normalized JOSS tags, and 5,757 distinct normalized repository topics.
