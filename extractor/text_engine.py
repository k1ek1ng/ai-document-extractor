"""Text-layer extraction engine.

Parses digitally-generated invoice PDFs by reading the embedded text layer
(no OCR, no LLM, no network). Fast and deterministic, but only works when
the PDF has real text and a layout the patterns understand — which is
exactly its role: handle the easy majority cheaply, leave scans and weird
layouts to the LLM engine.
"""
from __future__ import annotations

import re

from pypdf import PdfReader

from .schema import Invoice, LineItem

# matches: "<description>  <qty>  <unit_price>  <amount>" rows
LINE_RE = re.compile(
    r"^(?P<desc>[A-Za-z][A-Za-z0-9 ,.&/()-]*?)\s{2,}"
    r"(?P<qty>\d+(?:\.\d+)?)\s{2,}"
    r"(?P<price>[\d,]+\.\d{2})\s{2,}"
    r"(?P<amount>[\d,]+\.\d{2})\s*$",
    re.MULTILINE,
)

FIELD_PATTERNS = {
    "invoice_number": re.compile(r"Invoice\s*(?:#|No\.?|Number)[:\s]+([A-Z0-9-]+)", re.I),
    "invoice_date": re.compile(r"(?:Invoice\s+)?Date[:\s]+(\d{4}-\d{2}-\d{2})", re.I),
    "po_number": re.compile(r"P\.?O\.?\s*(?:#|No\.?|Number)?[:\s]+([A-Z0-9-]+)", re.I),
    "subtotal": re.compile(r"Subtotal[:\s]+\$?([\d,]+\.\d{2})", re.I),
    "tax": re.compile(r"Tax(?:\s*\([\d.]+%\))?[:\s]+\$?([\d,]+\.\d{2})", re.I),
    # (?<!Sub) so "Subtotal" can't satisfy the Total alternative
    "total": re.compile(r"(?:Amount\s+Due|(?<!Sub)Total)[:\s]+\$?([\d,]+\.\d{2})", re.I),
}


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def pdf_text(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract(path: str) -> Invoice:
    text = pdf_text(path)
    if not text.strip():
        raise ValueError(
            f"{path}: no text layer found (scanned document?) — use the llm engine"
        )

    fields: dict = {}
    for name, pattern in FIELD_PATTERNS.items():
        m = pattern.search(text)
        if m:
            fields[name] = m.group(1)

    # vendor: first non-empty line that isn't the word "INVOICE"
    for line in text.splitlines():
        line = line.strip()
        if line and line.upper() != "INVOICE":
            fields["vendor_name"] = line
            break

    items = [
        LineItem(
            description=m["desc"].strip(),
            quantity=_num(m["qty"]),
            unit_price=_num(m["price"]),
            amount=_num(m["amount"]),
        )
        for m in LINE_RE.finditer(text)
    ]
    if not items:
        raise ValueError(f"{path}: no line items matched — use the llm engine")

    return Invoice(
        vendor_name=fields.get("vendor_name", "UNKNOWN"),
        invoice_number=fields.get("invoice_number", "UNKNOWN"),
        invoice_date=fields.get("invoice_date", "1970-01-01"),
        po_number=fields.get("po_number"),
        line_items=items,
        subtotal=_num(fields.get("subtotal", "0")),
        tax=_num(fields.get("tax", "0")),
        total=_num(fields.get("total", "0")),
    )
