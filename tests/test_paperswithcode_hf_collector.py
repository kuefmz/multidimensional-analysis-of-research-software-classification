import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "paperswithcode_hf_collector.py"
spec = importlib.util.spec_from_file_location("paperswithcode_hf_collector", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_extracts_all_pwc_semantic_levels():
    record = {
        "tasks": ["Image Classification"],
        "methods": [
            {
                "name": "ResNet",
                "full_name": "Residual Network",
                "main_collection": {
                    "name": "Residual Networks",
                    "area": "Computer Vision",
                    "parent": "Convolutional Neural Networks",
                },
            }
        ],
    }
    assert module.extract_typed_labels(record) == {
        ("pwc_task", "Image Classification"),
        ("pwc_method", "ResNet"),
        ("pwc_method_collection", "Residual Networks"),
        ("pwc_area", "Computer Vision"),
        ("pwc_collection_parent", "Convolutional Neural Networks"),
    }


def test_deduplicates_same_label_within_one_paper():
    rows, stats = module.aggregate_records(
        [
            {
                "title": "A",
                "paper_url": "a",
                "tasks": ["Classification", "Classification"],
                "methods": [],
            },
            {
                "title": "B",
                "paper_url": "b",
                "tasks": ["Classification"],
                "methods": [],
            },
        ]
    )
    assert len(rows) == 1
    assert rows[0]["frequency"] == 2
    assert stats["papers_processed"] == 2
    assert stats["papers_with_at_least_one_extracted_label"] == 2


def test_surface_normalization_is_conservative():
    assert module.normalize_surface(" Neural_Network ") == "neural network"
