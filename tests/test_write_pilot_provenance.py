import csv
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "write_pilot_provenance.py"
spec = importlib.util.spec_from_file_location("write_pilot_provenance", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_summarize_pilot(tmp_path):
    path = tmp_path / "pilot.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "raw_label_type", "frequency_bucket"],
        )
        writer.writeheader()
        writer.writerow({"source": "joss", "raw_label_type": "tag", "frequency_bucket": "common"})
        writer.writerow({"source": "pwc", "raw_label_type": "task", "frequency_bucket": "singleton"})
    result = module.summarize_pilot(path)
    assert result["rows"] == 2
    assert result["by_source"] == {"joss": 1, "pwc": 1}
