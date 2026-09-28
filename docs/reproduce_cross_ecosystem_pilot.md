# Reproducing the RQ1 cross-ecosystem pilot

This procedure rebuilds the annotation pilot from typed source frequency tables without
changing the underlying source extractions.

## Required source tables

- JOSS: `data/interim/joss_label_frequencies.csv`
- Papers with Code: `data/interim/paperswithcode_label_frequencies.csv`
- bio.tools: `data/interim/biotools_full_label_frequencies.csv` once the full dump
  extraction is available.

Source tables remain unchanged. Quality flags are applied in a derived copy.

## 1. Audit Papers with Code label quality

```bash
python src/audit_label_quality.py \
  data/interim/paperswithcode_label_frequencies.csv \
  --output data/interim/paperswithcode_label_frequencies_audited.csv
```

The sampler honors `pilot_eligible=false` and skips those rows. The audit does not
delete or rewrite the raw PwC frequency table.

## 2. Build the balanced cross-ecosystem pilot

```bash
python src/build_multisource_pilot.py \
  data/interim/joss_label_frequencies.csv \
  data/interim/paperswithcode_label_frequencies_audited.csv \
  data/interim/biotools_full_label_frequencies.csv \
  --size 100 \
  --seed 42 \
  --output data/annotations/multisource_pilot_100.csv
```

Balancing order is:

1. source ecosystem;
2. native label type inside each ecosystem;
3. common / medium / repeated / singleton frequency buckets.

If a native label vocabulary is too small to fill its equal share, quota is
redistributed within the same ecosystem.

## 3. Write provenance

```bash
python src/write_pilot_provenance.py \
  --pilot data/annotations/multisource_pilot_100.csv \
  --output data/annotations/multisource_pilot_100.provenance.json \
  --source-input data/interim/joss_label_frequencies.csv \
  --source-input data/interim/paperswithcode_label_frequencies_audited.csv \
  --source-input data/interim/biotools_full_label_frequencies.csv \
  --notes "Seed 42; PwC structural quality gate applied before sampling."
```

The provenance file records the pilot checksum, source-input checksums, source counts,
native-label-type counts, and frequency-bucket counts.

## 4. Human annotation

Make independent copies for each annotator rather than editing the clean pilot in place.
The clean pilot is the immutable shared input.

Use:

- `annotations/annotation_guidelines.md`
- `annotations/rq1_pilot_protocol.md`

After both annotation files exist, run:

```bash
python src/analyze_pilot_annotations.py \
  data/annotations/multisource_pilot_100_annotator1.csv \
  data/annotations/multisource_pilot_100_annotator2.csv \
  --paired-output results/rq1/multisource_pilot_100_agreement.csv
```

Facet revision happens only after adjudication.
