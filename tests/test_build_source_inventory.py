import csv
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "build_source_inventory.py"
spec = importlib.util.spec_from_file_location("build_source_inventory", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_table(path, source, labels):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "raw_label_type", "normalized_label", "frequency"],
        )
        writer.writeheader()
        for label, frequency in labels:
            writer.writerow(
                {
                    "source": source,
                    "raw_label_type": "topic",
                    "normalized_label": label,
                    "frequency": frequency,
                }
            )


def test_inventory_and_exact_overlap(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    write_table(a, "a", [("python", 10), ("visualization", 2)])
    write_table(b, "b", [("python", 4), ("classification", 1)])

    inventory, overlap, summary = module.build_inventory([a, b])
    assert len(inventory) == 2
    assert overlap[0]["exact_shared_labels"] == 1
    assert overlap[0]["shared_examples"] == "python"
    assert summary["union_normalized_surface_labels"] == 3
    assert summary["labels_seen_in_multiple_sources"] == 1
