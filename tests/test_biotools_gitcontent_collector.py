import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "biotools_gitcontent_collector.py"
spec = importlib.util.spec_from_file_location("biotools_gitcontent_collector", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_iter_concepts_extracts_topic_and_operation():
    tool = {
        "topic": [
            {"term": "Genomics", "uri": "http://edamontology.org/topic_0622"}
        ],
        "function": [
            {
                "operation": [
                    {
                        "term": "Sequence analysis",
                        "uri": "http://edamontology.org/operation_2403",
                    }
                ]
            }
        ],
    }
    assert module.iter_concepts(tool) == {
        ("edam_topic", "Genomics", "http://edamontology.org/topic_0622"),
        ("edam_operation", "Sequence analysis", "http://edamontology.org/operation_2403"),
    }


def test_collect_deduplicates_per_tool(tmp_path):
    data_dir = tmp_path / "data" / "example"
    data_dir.mkdir(parents=True)
    tool = {
        "biotoolsID": "example",
        "name": "Example",
        "homepage": "https://example.org",
        "topic": [
            {"term": "Genomics", "uri": "http://edamontology.org/topic_0622"},
            {"term": "Genomics", "uri": "http://edamontology.org/topic_0622"},
        ],
        "function": [
            {
                "operation": [
                    {"term": "Sequence analysis", "uri": "http://edamontology.org/operation_2403"}
                ]
            }
        ],
    }
    (data_dir / "example.biotools.json").write_text(
        json.dumps(tool), encoding="utf-8"
    )

    rows, stats = module.collect(tmp_path)
    assert stats["current_json_files_parsed"] == 1
    assert stats["tools_with_edam_topic"] == 1
    assert stats["tools_with_edam_operation"] == 1
    assert len(rows) == 2
    assert all(row["frequency"] == 1 for row in rows)
