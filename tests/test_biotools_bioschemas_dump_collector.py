import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "biotools_bioschemas_dump_collector.py"
spec = importlib.util.spec_from_file_location("biotools_bioschemas_dump_collector", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_collect_filters_non_biotools_and_edam_families(tmp_path):
    dump = tmp_path / "dump.ttl"
    dump.write_text(
        """@prefix schema: <http://schema.org/> .
@prefix edam: <http://edamontology.org/> .
@prefix bt: <https://bio.tools/> .
@prefix ex: <https://example.org/> .

ex:a a schema:SoftwareApplication ;
  schema:identifier bt:alpha ;
  schema:applicationSubCategory edam:topic_0001, edam:data_0002 ;
  schema:featureList edam:operation_0003, edam:topic_0004 .

ex:b a schema:SoftwareApplication ;
  schema:identifier ex:other ;
  schema:applicationSubCategory edam:topic_0001 ;
  schema:featureList edam:operation_0003 .
""",
        encoding="utf-8",
    )
    edam = tmp_path / "edam.ttl"
    edam.write_text(
        """@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://edamontology.org/topic_0001> rdfs:label "Example topic" .
<http://edamontology.org/operation_0003> rdfs:label "Example operation" .
""",
        encoding="utf-8",
    )

    rows, stats = module.collect(dump, edam)
    assert stats["biotools_linked_software_subjects"] == 1
    assert stats["distinct_typed_labels"] == 2
    assert {(r["raw_label_type"], r["raw_label"]) for r in rows} == {
        ("edam_topic", "Example topic"),
        ("edam_operation", "Example operation"),
    }
    assert all(r["frequency"] == 1 for r in rows)


def test_collect_accepts_https_schema_namespace(tmp_path):
    dump = tmp_path / "dump.ttl"
    dump.write_text(
        """@prefix schema: <https://schema.org/> .
@prefix edam: <http://edamontology.org/> .
@prefix bt: <https://bio.tools/> .
@prefix ex: <https://example.org/> .
ex:a a schema:SoftwareApplication ;
  schema:identifier bt:alpha ;
  schema:applicationSubCategory edam:topic_0001 ;
  schema:featureList edam:operation_0003 .
""",
        encoding="utf-8",
    )
    edam = tmp_path / "edam.ttl"
    edam.write_text(
        """@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://edamontology.org/topic_0001> rdfs:label "Example topic" .
<http://edamontology.org/operation_0003> rdfs:label "Example operation" .
""",
        encoding="utf-8",
    )
    rows, stats = module.collect(dump, edam)
    assert stats["biotools_linked_software_subjects"] == 1
    assert len(rows) == 2


def test_collect_accepts_literal_biotools_identifier(tmp_path):
    dump = tmp_path / "dump.ttl"
    dump.write_text(
        """@prefix schema: <http://schema.org/> .
@prefix edam: <http://edamontology.org/> .
@prefix ex: <https://example.org/> .
ex:a a schema:SoftwareApplication ;
  schema:identifier "biotools:alpha" ;
  schema:applicationSubCategory edam:topic_0001 ;
  schema:featureList edam:operation_0003 .
""",
        encoding="utf-8",
    )
    edam = tmp_path / "edam.ttl"
    edam.write_text(
        """@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://edamontology.org/topic_0001> rdfs:label "Example topic" .
<http://edamontology.org/operation_0003> rdfs:label "Example operation" .
""",
        encoding="utf-8",
    )
    rows, stats = module.collect(dump, edam)
    assert stats["biotools_linked_software_subjects"] == 1
    assert len(rows) == 2


def test_collect_matches_schema_predicates_by_local_name(tmp_path):
    dump = tmp_path / "dump.ttl"
    dump.write_text(
        """@prefix custom: <https://example.org/schema/> .
@prefix edam: <http://edamontology.org/> .
@prefix ex: <https://example.org/tool/> .
ex:a custom:identifier "biotools:alpha" ;
  custom:applicationSubCategory edam:topic_0001 ;
  custom:featureList edam:operation_0003 .
""",
        encoding="utf-8",
    )
    edam = tmp_path / "edam.ttl"
    edam.write_text(
        """@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
<http://edamontology.org/topic_0001> rdfs:label "Example topic" .
<http://edamontology.org/operation_0003> rdfs:label "Example operation" .
""",
        encoding="utf-8",
    )
    rows, stats = module.collect(dump, edam)
    assert stats["biotools_linked_software_subjects"] == 1
    assert len(rows) == 2
