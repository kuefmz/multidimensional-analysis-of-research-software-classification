#!/usr/bin/env python3
"""Collect SemRepo classification-like labels through its public SPARQL endpoint.

This collector intentionally starts with two explicit repository dimensions:
- GitHub repository topics;
- programming languages.

Dependencies/packages are not included in the first RQ1 extraction because they are
implementation dependencies rather than an explicit classification field. They can be
added later as a separate metadata dimension if the study definition is broadened.

The default mode uses grouped SPARQL queries and therefore retrieves label frequencies
without downloading hundreds of thousands of repository-label edges.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, unquote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "interim"
RAW_META_DIR = ROOT / "data" / "raw" / "semrepo"
ENDPOINT = "https://semrepo.org/sparql"

QUERIES = {
    "repository_topic": """
SELECT ?label (COUNT(DISTINCT ?repository) AS ?frequency)
WHERE {
  GRAPH <https://semrepo.org> {
    ?repository
      <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>
        <https://semrepo.org/class/repository> ;
      <http://xmlns.com/foaf/0.1/topic> ?label .
  }
}
GROUP BY ?label
ORDER BY DESC(?frequency)
""",
    "programming_language": """
SELECT ?label (COUNT(DISTINCT ?repository) AS ?frequency)
WHERE {
  GRAPH <https://semrepo.org> {
    ?repository
      <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>
        <https://semrepo.org/class/repository> ;
      <https://semrepo.org/property/hasLanguageReference> ?languageRef .
    ?languageRef
      <https://semrepo.org/property/hasLanguageName> ?label .
  }
}
GROUP BY ?label
ORDER BY DESC(?frequency)
""",
}

COUNT_QUERIES = {
    "repository_total": """
SELECT (COUNT(DISTINCT ?repository) AS ?count)
WHERE {
  GRAPH <https://semrepo.org> {
    ?repository
      <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>
        <https://semrepo.org/class/repository> .
  }
}
""",
    "repositories_with_topic": """
SELECT (COUNT(DISTINCT ?repository) AS ?count)
WHERE {
  GRAPH <https://semrepo.org> {
    ?repository
      <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>
        <https://semrepo.org/class/repository> ;
      <http://xmlns.com/foaf/0.1/topic> ?topic .
  }
}
""",
    "repositories_with_language": """
SELECT (COUNT(DISTINCT ?repository) AS ?count)
WHERE {
  GRAPH <https://semrepo.org> {
    ?repository
      <http://www.w3.org/1999/02/22-rdf-syntax-ns#type>
        <https://semrepo.org/class/repository> ;
      <https://semrepo.org/property/hasLanguageReference> ?languageRef .
  }
}
""",
}


def sparql_json(query: str, endpoint: str = ENDPOINT, timeout: int = 120) -> dict:
    body = urlencode({"query": query}).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            "User-Agent": "research-software-classification-analysis/0.1",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def uri_to_source_label(value: str) -> str:
    """Convert a SemRepo entity URI to a readable source label without synonym mapping."""
    parsed = urlparse(value)
    if parsed.scheme and parsed.netloc:
        local = unquote(parsed.path.rstrip("/").split("/")[-1])
    else:
        local = value
    # SemRepo URI construction replaces whitespace with URI-safe separators.
    # Keep hyphens because they may be semantically meaningful in GitHub topics.
    return local.strip()


def normalize_surface(label: str) -> str:
    text = unicodedata.normalize("NFKC", label)
    text = text.strip().lower()
    text = re.sub(r"[_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def parse_results(payload: dict, label_type: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for binding in payload.get("results", {}).get("bindings", []):
        raw_value = binding["label"]["value"]
        raw_label = uri_to_source_label(raw_value)
        if not raw_label:
            continue
        frequency = int(binding.get("frequency", {}).get("value", "0"))
        rows.append(
            {
                "source": "semrepo",
                "raw_label": raw_label,
                "raw_label_uri": raw_value if raw_value.startswith(("http://", "https://")) else "",
                "raw_label_type": label_type,
                "normalized_label": normalize_surface(raw_label),
                "frequency": frequency,
                "normalization_method": "surface_v1",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source",
        "raw_label",
        "raw_label_uri",
        "raw_label_type",
        "normalized_label",
        "frequency",
        "normalization_method",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(endpoint: str = ENDPOINT) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_META_DIR.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, object]] = []
    query_stats: dict[str, object] = {}

    for label_type, query in QUERIES.items():
        payload = sparql_json(query, endpoint=endpoint)
        rows = parse_results(payload, label_type)
        all_rows.extend(rows)
        query_stats[label_type] = {
            "distinct_labels": len(rows),
            "repository_label_assignments": sum(int(row["frequency"]) for row in rows),
        }

    all_rows.sort(
        key=lambda row: (
            str(row["raw_label_type"]),
            -int(row["frequency"]),
            str(row["normalized_label"]),
        )
    )

    endpoint_counts: dict[str, int] = {}
    for count_name, count_query in COUNT_QUERIES.items():
        payload = sparql_json(count_query, endpoint=endpoint)
        bindings = payload.get("results", {}).get("bindings", [])
        endpoint_counts[count_name] = (
            int(bindings[0]["count"]["value"]) if bindings else 0
        )

    write_csv(OUT_DIR / "semrepo_label_frequencies.csv", all_rows)

    provenance = {
        "source": "SemRepo",
        "endpoint": endpoint,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "query_mode": "grouped_frequency",
        "named_graph": "https://semrepo.org",
        "classification_fields": ["repository_topic", "programming_language"],
        "excluded_from_initial_rq1": {
            "package": (
                "Packages are implementation dependencies rather than explicit "
                "classification labels; reconsider separately if the study scope expands."
            )
        },
        "query_stats": query_stats,
        "endpoint_counts": endpoint_counts,
        "coverage": {
            "topic_repository_fraction": (
                endpoint_counts["repositories_with_topic"] / endpoint_counts["repository_total"]
                if endpoint_counts["repository_total"] else None
            ),
            "language_repository_fraction": (
                endpoint_counts["repositories_with_language"] / endpoint_counts["repository_total"]
                if endpoint_counts["repository_total"] else None
            ),
        },
    }
    (RAW_META_DIR / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(query_stats, indent=2))
    print(f"Total distinct typed labels: {len(all_rows):,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default=ENDPOINT)
    args = parser.parse_args()
    main(endpoint=args.endpoint)
