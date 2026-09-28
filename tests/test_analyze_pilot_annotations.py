import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "analyze_pilot_annotations.py"
spec = importlib.util.spec_from_file_location("analyze_pilot_annotations", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_summary_counts_other_unclear_and_proposals():
    rows = [
        {"primary_facet": "Method / Algorithm", "proposed_facet": "", "confidence": "0.9"},
        {"primary_facet": "Other", "proposed_facet": "Organization", "confidence": "0.8"},
        {"primary_facet": "Unclear", "proposed_facet": "", "confidence": "0.3"},
        {"primary_facet": "", "proposed_facet": "", "confidence": ""},
    ]
    summary = module.summarize(rows)
    assert summary["annotated"] == 3
    assert summary["other_count"] == 1
    assert summary["unclear_count"] == 1
    assert summary["proposed_facet_counts"] == {"Organization": 1}


def test_cohen_kappa_perfect_agreement():
    rows = [
        {
            "annotator_1_facet": "Domain",
            "annotator_2_facet": "Domain",
            "agreement": "true",
        },
        {
            "annotator_1_facet": "Method",
            "annotator_2_facet": "Method",
            "agreement": "true",
        },
    ]
    assert module.cohen_kappa(rows) == 1.0


def test_join_annotators_uses_shared_pilot_ids():
    first = [
        {"pilot_id": "A", "normalized_label": "python", "primary_facet": "Language"},
        {"pilot_id": "B", "normalized_label": "classification", "primary_facet": "Function"},
    ]
    second = [
        {"pilot_id": "A", "normalized_label": "python", "primary_facet": "Language"},
        {"pilot_id": "C", "normalized_label": "other", "primary_facet": "Other"},
    ]
    paired = module.join_annotators(first, second)
    assert len(paired) == 1
    assert paired[0]["pilot_id"] == "A"
    assert paired[0]["agreement"] == "true"
