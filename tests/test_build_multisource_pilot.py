import csv
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "build_multisource_pilot.py"
spec = importlib.util.spec_from_file_location("build_multisource_pilot", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_frequency_buckets():
    assert module.frequency_bucket(20) == "common"
    assert module.frequency_bucket(3) == "medium"
    assert module.frequency_bucket(2) == "repeated"
    assert module.frequency_bucket(1) == "singleton"


def test_balanced_across_sources():
    sources = {}
    for source in ("a", "b", "c", "d"):
        sources[source] = [
            {
                "source": source,
                "raw_label_type": "topic",
                "normalized_label": f"{source}-{i}",
                "frequency": str(30 - i),
            }
            for i in range(30)
        ]
    sampled = module.balanced_sample(sources, total_size=40, seed=42)
    assert len(sampled) == 40
    assert {
        source: sum(row["_sample_source"] == source for row in sampled)
        for source in sources
    } == {"a": 10, "b": 10, "c": 10, "d": 10}


def test_output_annotation_columns_are_blank(tmp_path):
    path = tmp_path / "pilot.csv"
    rows = [{
        "_sample_source": "joss",
        "source": "joss",
        "raw_label_type": "joss_tag",
        "normalized_label": "visualization",
        "raw_label": "Visualization",
        "frequency": "12",
        "example_software": "Example",
        "example_repository_url": "https://example.org",
    }]
    module.write_pilot(path, rows)
    with path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    assert row["primary_facet"] == ""
    assert row["proposed_facet"] == ""
    assert row["frequency_bucket"] == "common"
