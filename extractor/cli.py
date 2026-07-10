"""CLI: extract structured data from invoice PDFs.

    python -m extractor.cli samples/ --engine text --out out/
    python -m extractor.cli scan.pdf --engine llm --out out/   # needs ANTHROPIC_API_KEY
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import text_engine
from .output import write_excel, write_json
from .schema import Invoice


def collect_pdfs(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(target.glob("*.pdf"))
    if target.suffix.lower() == ".pdf":
        return [target]
    raise SystemExit(f"not a PDF or directory: {target}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Extract structured data from invoice PDFs")
    ap.add_argument("input", type=Path, help="a PDF file or a directory of PDFs")
    ap.add_argument("--engine", choices=["text", "llm"], default="text")
    ap.add_argument("--out", type=Path, default=Path("out"))
    args = ap.parse_args(argv)

    if args.engine == "llm":
        from . import llm_engine as engine  # imported lazily: needs anthropic + key
    else:
        engine = text_engine

    args.out.mkdir(parents=True, exist_ok=True)
    results: dict[str, Invoice] = {}
    failures = 0

    for pdf in collect_pdfs(args.input):
        try:
            inv = engine.extract(str(pdf))
        except Exception as e:  # noqa: BLE001 — report and continue the batch
            print(f"FAIL  {pdf.name}: {e}", file=sys.stderr)
            failures += 1
            continue
        results[pdf.name] = inv
        write_json(inv, args.out / f"{pdf.stem}.json")
        flag = f"  ({len(inv.warnings)} warning(s))" if inv.warnings else ""
        print(f"ok    {pdf.name}: {inv.vendor_name}, {len(inv.line_items)} lines, total {inv.total}{flag}")

    if results:
        xlsx = args.out / "invoices.xlsx"
        write_excel(results, xlsx)
        print(f"\n{len(results)} invoice(s) -> {args.out}/*.json + {xlsx}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
