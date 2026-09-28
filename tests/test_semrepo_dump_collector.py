import gzip
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "semrepo_dump_collector.py"
spec = importlib.util.spec_from_file_location("semrepo_dump_collector", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_parse_uri_triple():
    line = (
        "<https://semrepo.org/repository/a> "
        "<http://xmlns.com/foaf/0.1/topic> "
        "<https://semrepo.org/topic/machine-learning> .\n"
    )
    assert module.parse_uri_triple(line) == (
        "https://semrepo.org/repository/a",
        "http://xmlns.com/foaf/0.1/topic",
        "https://semrepo.org/topic/machine-learning",
    )


def test_streaming_dump_extraction(tmp_path):
    dump = tmp_path / "tiny.nt.gz"
    triples = [
        "<https://semrepo.org/repository/a> "
        "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> "
        "<https://semrepo.org/class/repository> .\n",
        "<https://semrepo.org/repository/a> "
        "<http://xmlns.com/foaf/0.1/topic> "
        "<https://semrepo.org/topic/machine-learning> .\n",
        "<https://semrepo.org/repository/a> "
        "<https://semrepo.org/property/hasLanguageReference> "
        "<https://semrepo.org/languageReference/a-1> .\n",
        "<https://semrepo.org/languageReference/a-1> "
        "<https://semrepo.org/property/hasLanguageName> "
        "<https://semrepo.org/programmingLanguage/Python> .\n",
    ]
    with gzip.open(dump, "wt", encoding="utf-8") as handle:
        handle.writelines(triples)

    rows, stats = module.extract_dump(dump, tmp_path / "join.sqlite")
    assert stats["repository_type_triples"] == 1
    assert stats["distinct_topic_labels"] == 1
    assert stats["distinct_language_labels"] == 1
    assert any(
        row["raw_label_type"] == "repository_topic"
        and row["raw_label"] == "machine-learning"
        for row in rows
    )
    assert any(
        row["raw_label_type"] == "programming_language"
        and row["raw_label"] == "Python"
        for row in rows
    )
