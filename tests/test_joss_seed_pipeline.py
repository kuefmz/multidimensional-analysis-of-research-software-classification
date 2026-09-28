import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "joss_seed_pipeline.py"
spec = importlib.util.spec_from_file_location("joss_seed_pipeline", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_surface_normalization_is_conservative():
    assert module.normalize_surface("  Machine_Learning ") == "machine learning"
    assert module.normalize_surface("Natural-Language Processing") == "natural-language processing"


def test_parse_keywords_common_formats():
    assert module.parse_keywords("NLP; Python; PyTorch") == ["NLP", "Python", "PyTorch"]
    assert module.parse_keywords('["NLP", "Python"]') == ["NLP", "Python"]
    assert module.parse_keywords("") == []


def test_prefers_distinct_joss_and_repository_columns():
    columns = ["url", "joss_tags", "repository_topics", "combined_keywords"]
    assert module.choose_label_columns(columns) == [
        ("joss_tags", "joss_tag"),
        ("repository_topics", "repository_topic"),
    ]


def test_pilot_is_deterministic_and_balanced_by_label_type():
    rows = []
    for label_type in ("joss_tag", "repository_topic"):
        rows.extend(
            {
                "raw_label_type": label_type,
                "normalized_label": f"{label_type}-{i}",
                "example_raw_label": f"Label {i}",
                "frequency": 100 - i,
            }
            for i in range(100)
        )

    first = module.stratified_pilot(rows, size=50, seed=42)
    second = module.stratified_pilot(rows, size=50, seed=42)
    assert first == second
    assert len(first) == 50
    assert sum(row["raw_label_type"] == "joss_tag" for row in first) == 25
    assert sum(row["raw_label_type"] == "repository_topic" for row in first) == 25
