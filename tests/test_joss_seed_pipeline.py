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


def test_pilot_is_deterministic():
    rows = [
        {"normalized_label": f"label-{i}", "example_raw_label": f"Label {i}", "frequency": 100 - i}
        for i in range(100)
    ]
    first = module.stratified_pilot(rows, size=50, seed=42)
    second = module.stratified_pilot(rows, size=50, seed=42)
    assert first == second
    assert len(first) == 50
