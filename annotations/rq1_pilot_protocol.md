# RQ1 annotation and facet-revision protocol

## Goal

RQ1 asks which semantic dimensions are actually used to classify research software
across ecosystems. The facet codebook is therefore an **empirical output**, not a fixed
ontology imposed before annotation.

The seed facets in `configs/facets.yaml` are working hypotheses used to make the first
annotation round operational.

## Pilot stages

### Stage A — JOSS development pilot

Artifact: `data/annotations/joss_pilot_50.csv`

- 50 labels total;
- 25 JOSS tags;
- 25 GitHub repository topics;
- sampled across common, medium-frequency, repeated, and singleton labels;
- used to test annotation instructions and expose missing dimensions.

This pilot is **development evidence**, not the final cross-ecosystem sample.

### Stage B — cross-ecosystem pilot

Target: 100 labels initially.

Sampling order:

1. balance ecosystems;
2. within each ecosystem, balance native label types as far as the vocabulary permits;
3. within each native label type, sample across frequency buckets;
4. retain one source context example where available.

For example, Papers with Code should not be represented almost entirely by tasks simply
because its task vocabulary is much larger than its area vocabulary.

## What annotators see

Each row should retain:

- source ecosystem;
- native label type;
- normalized label;
- raw/example label;
- source frequency;
- one contextual software/paper/repository example where available.

The **native label type is provenance, not the answer**. For example, a PwC "task" may
still require semantic interpretation under the study codebook; annotators must not
mechanically map native field names to RQ1 facets.

## Annotation output

Each annotator independently assigns exactly one:

- one seed facet;
- `Other`;
- `Unclear`.

For `Other`, the annotator proposes a concise candidate facet.
For `Unclear`, the annotator records why the available label/context is insufficient.

Confidence is recorded as a numeric value between 0 and 1 when possible.

## Facet-revision decisions

A proposed facet is not added merely because one unusual label exists. During
adjudication, evaluate candidate facets using all of the following:

1. **Recurrence** — Does the semantic distinction appear in more than an isolated label?
2. **Coherence** — Can the candidate be defined consistently with clear positive
   examples?
3. **Separability** — Is it meaningfully distinct from the current facets rather than a
   synonym or a narrower lexical variant?
4. **Cross-source relevance** — Does it occur in multiple ecosystems, or is there a
   strong reason to retain a source-specific dimension?
5. **Annotation reliability** — Can annotators apply the distinction consistently?
6. **Research relevance** — Does the distinction answer how software is classified,
   rather than merely describe incidental metadata?

A facet can also be **merged or removed** when disagreements show that annotators cannot
reliably separate it from another facet.

No automatic frequency threshold determines promotion. Counts are evidence for
recurrence, not a substitute for semantic adjudication.

## Agreement analysis

For a shared pilot:

- report raw/observed agreement;
- report Cohen's kappa for the primary facet;
- inspect the disagreement matrix rather than relying on one scalar score;
- separately report `Other`, `Unclear`, and low-confidence cases.

Agreement is diagnostic. A low value is not repaired by forcing labels into existing
facets; it triggers review of definitions, context, or facet boundaries.

The analysis helper is `src/analyze_pilot_annotations.py`.

## Preserving evidence

Never overwrite independent annotations after adjudication.

Keep separate files for:

1. clean pilot input;
2. annotator 1;
3. annotator 2;
4. paired agreement table;
5. adjudicated labels;
6. codebook revision notes.

The assistant exploratory JOSS coding file is explicitly non-human exploratory evidence
and must not be used as an annotator in the final agreement calculation.

## Scaling beyond the pilot

Only after adjudication should the revised codebook be frozen for larger annotation.

The scaled sample should preserve ecosystem and native-label-type provenance. If later
sources introduce genuinely new semantic dimensions, reopen the codebook with a recorded
version change rather than silently extending it.
