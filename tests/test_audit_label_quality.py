import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "audit_label_quality.py"
spec = importlib.util.spec_from_file_location("audit_label_quality", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_normal_scientific_labels_remain_eligible():
    for label in [
        "finite element method",
        "natural language processing",
        "molecular-dynamics",
        "standardisation and normalisation",
    ]:
        assert module.quality_reasons(label) == []


def test_flags_contact_like_and_long_free_text():
    assert "phone_like" in module.quality_reasons(
        "support line +1 (800) 555-1234"
    )
    assert "contains_url" in module.quality_reasons(
        "see https://example.org for support"
    )
    reasons = module.quality_reasons(
        "proven ways to talk to someone at a service via phone email or chat options step by step guide"
    )
    assert "long_free_text" in reasons


def test_audit_preserves_rows_and_adds_flags():
    rows = [
        {"normalized_label": "classification", "frequency": "5"},
        {"normalized_label": "https://spam.example/support", "frequency": "1"},
    ]
    out = module.audit_rows(rows)
    assert len(out) == 2
    assert out[0]["pilot_eligible"] == "true"
    assert out[1]["pilot_eligible"] == "false"
