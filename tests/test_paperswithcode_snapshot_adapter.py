import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "paperswithcode_snapshot_adapter.py"
spec = importlib.util.spec_from_file_location("paperswithcode_snapshot_adapter", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_labels_from_record_preserves_pwc_category_types():
    record = {
        "papers with code categories": {
            "tasks": ["Image Classification"],
            "methods": [{"method": "ResNet"}],
            "collections": ["Convolutional Neural Networks"],
            "main_collection_areas": ["Computer Vision"],
        }
    }
    assert module.labels_from_record(record) == {
        ("pwc_task", "Image Classification"),
        ("pwc_method", "ResNet"),
        ("pwc_method_collection", "Convolutional Neural Networks"),
        ("pwc_area", "Computer Vision"),
    }


def test_aggregate_counts_unique_papers(tmp_path):
    path = tmp_path / "pwc.jsonl"
    records = [
        {
            "paper_title": "Paper A",
            "paper_url": "a",
            "github_repo": "https://github.com/x/a",
            "papers with code categories": {"tasks": ["Classification"]},
        },
        {
            "paper_title": "Paper B",
            "paper_url": "b",
            "github_repo": "https://github.com/x/b",
            "papers with code categories": {"tasks": ["Classification"]},
        },
    ]
    path.write_text("\n".join(json.dumps(x) for x in records) + "\n", encoding="utf-8")
    rows = module.aggregate(path)
    assert len(rows) == 1
    assert rows[0]["raw_label_type"] == "pwc_task"
    assert rows[0]["frequency"] == 2
