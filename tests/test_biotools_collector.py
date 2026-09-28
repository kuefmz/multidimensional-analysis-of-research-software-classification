import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "biotools_collector.py"
spec = importlib.util.spec_from_file_location("biotools_collector", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_iter_concepts_extracts_topics_and_operations_only():
    tool = {
        "biotoolsID": "example",
        "topic": [
            {"uri": "http://edamontology.org/topic_0121", "term": "Proteomics"}
        ],
        "function": [
            {
                "operation": [
                    {
                        "uri": "http://edamontology.org/operation_0492",
                        "term": "Multiple sequence alignment",
                    }
                ],
                "input": [{"data": {"term": "Sequence"}}],
            }
        ],
        "language": ["Python"],
    }
    assert module.iter_concepts(tool) == [
        (
            "edam_operation",
            "Multiple sequence alignment",
            "http://edamontology.org/operation_0492",
        ),
        ("edam_topic", "Proteomics", "http://edamontology.org/topic_0121"),
    ]


def test_duplicate_concept_in_one_tool_counts_once():
    tool = {
        "biotoolsID": "example",
        "topic": [
            {"uri": "http://edamontology.org/topic_0121", "term": "Proteomics"},
            {"uri": "http://edamontology.org/topic_0121", "term": "Proteomics"},
        ],
    }
    assignments = module.aggregate_tools([tool])
    assert assignments[
        ("edam_topic", "Proteomics", "http://edamontology.org/topic_0121")
    ] == {"example"}


def test_write_rows_preserves_uri_and_frequency():
    assignments = {
        ("edam_topic", "Proteomics", "http://edamontology.org/topic_0121"): {"a", "b"}
    }
    rows = module.write_rows(assignments)
    assert rows[0]["normalized_label"] == "proteomics"
    assert rows[0]["frequency"] == 2
    assert rows[0]["raw_label_uri"] == "http://edamontology.org/topic_0121"
