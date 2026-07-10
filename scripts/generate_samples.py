"""Generate synthetic invoice PDFs + ground-truth JSON for testing.

Every vendor, part, and number below is fake and generated here. Seeded,
so the same samples come out every time.

    python scripts/generate_samples.py --count 5 --out samples/
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from fpdf import FPDF

VENDORS = [
    "Summit Controls Inc.", "Pioneer Machining LLC", "Cascade Tooling Co.",
    "Granite Electric Corp.", "Beacon Automation Inc.", "Harbor Fabrication LLC",
]
PARTS = [
    "Steel Bracket", "Aluminum Housing", "Sealed Bearing", "Terminal Block",
    "Relay Board", "Sensor Mount", "Polymer Gasket", "Drive Coupler",
    "Wiring Harness", "Compact Enclosure",
]


def make_invoice(rng: random.Random, n: int) -> dict:
    items = []
    for _ in range(rng.randint(2, 6)):
        qty = rng.randint(1, 40)
        price = round(rng.uniform(3, 450), 2)
        items.append({
            "description": f"{rng.choice(PARTS)} {rng.choice(['A', 'B', 'C'])}-{rng.randint(100, 999)}",
            "quantity": float(qty),
            "unit_price": price,
            "amount": round(qty * price, 2),
        })
    subtotal = round(sum(i["amount"] for i in items), 2)
    tax = round(subtotal * 0.055, 2)
    return {
        "vendor_name": rng.choice(VENDORS),
        "invoice_number": f"INV-{2026}{n:04d}",
        "invoice_date": f"2026-{rng.randint(1, 6):02d}-{rng.randint(1, 28):02d}",
        "po_number": f"PO-{rng.randint(10000, 99999)}",
        "line_items": items,
        "subtotal": subtotal,
        "tax": tax,
        "total": round(subtotal + tax, 2),
    }


def render_pdf(inv: dict, path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=16)
    pdf.cell(0, 10, inv["vendor_name"], new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", size=11)
    pdf.cell(0, 6, "INVOICE", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Invoice #: {inv['invoice_number']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Date: {inv['invoice_date']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"PO #: {inv['po_number']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "", new_x="LMARGIN", new_y="NEXT")

    # two spaces minimum between columns — matches the text engine's contract
    pdf.cell(0, 6, f"{'Description':<34}{'Qty':>6}  {'Price':>10}  {'Amount':>10}",
             new_x="LMARGIN", new_y="NEXT")
    for li in inv["line_items"]:
        pdf.cell(
            0, 6,
            f"{li['description']:<34}{li['quantity']:>6.0f}  {li['unit_price']:>10,.2f}  {li['amount']:>10,.2f}",
            new_x="LMARGIN", new_y="NEXT",
        )
    pdf.cell(0, 6, "", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Subtotal:  {inv['subtotal']:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Tax (5.5%):  {inv['tax']:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Amount Due:  {inv['total']:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--out", type=Path, default=Path("samples"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    for n in range(1, args.count + 1):
        inv = make_invoice(rng, n)
        stem = args.out / f"invoice_{n:02d}"
        render_pdf(inv, stem.with_suffix(".pdf"))
        stem.with_suffix(".truth.json").write_text(json.dumps(inv, indent=2) + "\n")
        print(f"wrote {stem}.pdf")


if __name__ == "__main__":
    main()
