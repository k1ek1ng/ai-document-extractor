import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from extractor import text_engine  # noqa: E402
from extractor.schema import Invoice, LineItem  # noqa: E402


@pytest.fixture(scope="session")
def samples(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("samples")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_samples.py"),
         "--count", "4", "--out", str(out)],
        check=True,
    )
    return out


def test_schema_rejects_bad_line_math():
    with pytest.raises(ValueError):
        LineItem(description="x", quantity=2, unit_price=10.0, amount=99.0)


def test_schema_warns_on_total_mismatch():
    inv = Invoice(
        vendor_name="V", invoice_number="I-1", invoice_date="2026-01-01",
        line_items=[LineItem(description="x", quantity=1, unit_price=10.0, amount=10.0)],
        subtotal=10.0, tax=0.55, total=99.0,
    )
    assert any("total" in w for w in inv.warnings)


def test_text_engine_matches_ground_truth(samples: Path):
    for pdf in sorted(samples.glob("*.pdf")):
        truth = json.loads(pdf.with_suffix("").with_suffix(".truth.json").read_text())
        inv = text_engine.extract(str(pdf))
        assert inv.vendor_name == truth["vendor_name"]
        assert inv.invoice_number == truth["invoice_number"]
        assert inv.invoice_date == truth["invoice_date"]
        assert inv.po_number == truth["po_number"]
        assert inv.total == truth["total"]
        assert len(inv.line_items) == len(truth["line_items"])
        assert inv.warnings == []


def test_cli_end_to_end(samples: Path, tmp_path: Path):
    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "-m", "extractor.cli", str(samples), "--out", str(out)],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert len(list(out.glob("*.json"))) == 4
    assert (out / "invoices.xlsx").exists()
