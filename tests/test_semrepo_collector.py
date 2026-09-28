import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "semrepo_collector.py"
spec = importlib.util.spec_from_file_location("semrepo_collector", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_uri_to_source_label():
    assert module.uri_to_source_label("https://semrepo.org/topic/machine-learning") == "machine-learning"
    assert module.uri_to_source_label("https://semrepo.org/programmingLanguage/C%2B%2B") == "C++"
    assert module.uri_to_source_label("Python") == "Python"


def test_parse_topic_results():
    payload = {
        "results": {
            "bindings": [
                {
                    "label": {"type": "uri", "value": "https://semrepo.org/topic/machine-learning"},
                    "frequency": {"type": "literal", "value": "25"},
                }
            ]
        }
    }
    rows = module.parse_results(payload, "repository_topic")
    assert rows == [
        {
            "source": "semrepo",
            "raw_label": "machine-learning",
            "raw_label_uri": "https://semrepo.org/topic/machine-learning",
            "raw_label_type": "repository_topic",
            "normalized_label": "machine-learning",
            "frequency": 25,
            "normalization_method": "surface_v1",
        }
    ]


def test_semrepo_queries_are_grouped():
    for query in module.QUERIES.values():
        assert "COUNT(DISTINCT ?repository)" in query
        assert "GROUP BY ?label" in query
