# Pilot annotation guidelines

## Purpose

The first annotation round tests whether the proposed semantic facets are understandable,
sufficient, and mutually distinguishable. The seed facets are hypotheses rather than the
final answer to RQ1.

## Unit of annotation

Annotate a **normalized classification label**, while retaining the raw source label and
source provenance. Use only the meaning supported by the label itself unless additional
source context is explicitly included in the annotation file.

## Decisions

Assign exactly one primary facet for the pilot:

- Scientific / Subject Domain
- Application Area
- Function / Task
- Method / Algorithm
- Data / Input Modality
- Technology / Framework
- Programming Language
- Programming Paradigm
- Design / Architectural Pattern
- Software / Artifact Type
- Other
- Unclear

If `Other` is selected, propose a concise new facet name in `proposed_facet`.
If `Unclear` is selected, explain the ambiguity in `annotation_note`.

## Difficult distinctions

### Domain vs application area

Use **Scientific / Subject Domain** for a discipline or knowledge field.
Use **Application Area** for a concrete setting/problem context.

Examples:
- genomics -> Scientific / Subject Domain
- healthcare -> Application Area

This distinction is deliberately provisional. Repeated disagreement is evidence that the
facets may need to be merged or redefined.

### Function vs method

Use **Function / Task** for what the software does.
Use **Method / Algorithm** for how it performs that function.

Examples:
- classification -> Function / Task
- random forest -> Method / Algorithm
- visualization -> Function / Task
- finite element method -> Method / Algorithm

### Technology vs programming language

Use **Technology / Framework** for frameworks/platforms/runtimes.
Use **Programming Language** for programming languages.

Examples:
- PyTorch -> Technology / Framework
- Python -> Programming Language

## Pilot procedure

1. Annotate 50 labels independently.
2. Record uncertainty rather than forcing a facet.
3. Review all disagreements.
4. Revise facet definitions before scaling annotation.
5. Preserve the original pilot annotations even after adjudication.
