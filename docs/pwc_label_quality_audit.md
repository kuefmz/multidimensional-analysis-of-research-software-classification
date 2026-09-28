# Papers with Code label-quality audit

The full frozen Papers with Code archive was processed before constructing the
cross-ecosystem annotation pilot.

## Full snapshot

The extraction processed **576,261 papers**. Of these, **469,717** had at least one
classification-like PwC label. The resulting typed vocabularies contain:

| Native type | Distinct labels | Paper-label assignments |
| --- | ---: | ---: |
| Area | 7 | 237,008 |
| Collection parent | 21 | 129,107 |
| Method | 14,827 | 735,031 |
| Method collection | 313 | 572,856 |
| Task | 4,795 | 1,148,338 |
| **Total typed rows** | **19,963** | |

## Archive pollution discovered

A structural quality audit flags **3,420 / 19,963** typed label rows as poor annotation
units. Of these, **3,418 are PwC methods** and 2 are tasks.

The problem is not restricted to singletons. Some polluted method strings have hundreds
or thousands of paper assignments. Examples include customer-service phone-number and
travel-support phrases. This means a simple minimum-frequency threshold would retain
substantial pollution.

The audit does **not delete these rows from the source extraction**. It adds an explicit
pilot-eligibility flag so the raw archive evidence remains inspectable.

## Structural exclusion rules

`src/audit_label_quality.py` flags labels for pilot exclusion when they contain one or
more of the following structural signals:

- URL-like text;
- email-like text;
- phone-number-like text;
- more than 14 word-like tokens;
- more than 140 characters;
- unusually high punctuation density;
- effectively empty labels.

These rules are deliberately content-agnostic: they do not blacklist specific companies,
travel providers, cryptocurrencies, or topical words.

On the full PwC label table the flags were distributed approximately as follows
(a row may trigger multiple reasons):

- long free text: 2,852;
- phone-like text: 687;
- very long label: 29;
- high punctuation density: 15;
- URL-like text: 5;
- email-like text: 1.

## Interpretation

This is a **source data-quality issue**, not a semantic facet. Polluted labels must not be
forced into `Other` or `Unclear`, because doing so would distort the empirical facet
distribution.

For annotation-pilot construction:

1. preserve all raw PwC typed labels in the source frequency table;
2. run the structural audit;
3. exclude rows with `pilot_eligible=false` from sampling;
4. preserve the exclusion reason for reproducibility;
5. report the number of excluded source labels separately.

The semantic analysis should therefore distinguish **classification vocabulary coverage**
from **source-vocabulary quality**.
