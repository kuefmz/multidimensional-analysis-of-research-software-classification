# Exploratory JOSS pilot coding

This note summarizes an **assistant exploratory coding pass** over the deterministic
50-label JOSS pilot. It is not a human gold standard and must not be used for the final
inter-annotator agreement calculation.

Its purpose is to stress-test the seed facet codebook before human annotation.

## Immediate findings

The seed facets cover many high-frequency labels well, especially:

- scientific/subject domains,
- functions/tasks,
- methods/algorithms,
- programming languages,
- technologies/frameworks.

However, the pilot contains several labels that cannot be represented cleanly without
forcing their meaning into an unrelated facet.

### Candidate dimensions exposed by the pilot

**Object / Phenomenon of Study**

Examples: `comets`, `enzyme`, `ring-current`, `tokamak`, `emissions`,
`packed-bed`.

These describe *what is being studied or modelled*, which is semantically different from
the discipline/domain in which the research sits.

**Organization / Institution**

Examples: `CERN`, `NASA`.

These are provenance/community/context labels rather than descriptions of software
functionality.

**Data Format**

Example: `nii`.

This is distinct from Data Modality. `image` may be a modality, while NIfTI/`.nii`
is a representation/format.

**Publication / Curation Status**

Example: `peer-reviewed`.

This describes curation or publication status rather than software semantics.

**Quality / Non-functional Concern**

Example: `safety`.

This may warrant a cross-cutting quality/constraint facet if similar labels recur in the
larger sample.

**Mathematical Property / Concept**

Example: `equivariance`.

It is not yet clear whether this should become a separate facet, be folded into Method,
or be treated as an Object/Concept dimension.

## Seed-facet ambiguities to test with human annotators

Several labels expose boundary problems rather than necessarily requiring new facets:

- `remote sensing`: method vs scientific field;
- `robotics`: scientific domain vs application area;
- `regression`: method vs task/function;
- `computer vision`: subject domain vs application area;
- `database`: artifact type vs technology;
- `secure-hashing`: function vs method;
- `stochastic`: too underspecified without additional context.

These should be highlighted during pilot adjudication. Repeated disagreement is evidence
that definitions need to be merged or sharpened.

## Recommendation before scaling

Do not add every candidate facet immediately. Have two human annotators code the same
50 labels with the current seed codebook plus `Other` and `Unclear`. During
adjudication, compare their proposed new facets with the candidates above. Promote a new
facet only when it recurs and has a stable definition.
