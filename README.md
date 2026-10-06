# ai-document-extractor

Extracts structured data from invoice PDFs and outputs validated JSON and Excel.

Two extraction engines produce the same schema:

| engine | method | intended input |
|---|---|---|
| `text` | regex patterns over the PDF's embedded text layer; deterministic, no API calls | digital PDFs in a known layout |
| `llm` | renders pages to images and extracts fields with a vision model | scans, photos, and unfamiliar layouts |

Both engines populate a pydantic model that validates the arithmetic: quantity
times unit price equals the line amount, line amounts sum to the subtotal, and
subtotal plus tax equals the total. A line-level mismatch raises an error. A
total-level mismatch adds a warning, since invoices can include charges not
listed as lines, such as freight or tariffs.

The arithmetic check exists because extraction errors are often well-formed. A
model that reads `1,240.00` as `124.00` still returns a valid object.

## Run it

```bash
pip install -r requirements.txt
python scripts/generate_samples.py            # synthetic invoices -> samples/
python -m extractor.cli samples/ --out out/   # text engine (default)
python -m pytest
```

LLM engine:

```bash
export ANTHROPIC_API_KEY=...
python -m extractor.cli samples/invoice_01.pdf --engine llm --out out/
```

Output is one JSON per invoice plus a combined `invoices.xlsx` with a summary
sheet, a line-item sheet, and a warnings column.

Samples are generated with known values, so `tests/test_extractor.py` compares
extracted output against the ground-truth JSON generated with each PDF.

## Known limitations of the text engine

- **Whitespace in identifiers.** A pattern such as `PO\d{6}` does not match
  `PO 123456`. On real invoices, one group of suppliers printed PO numbers this
  way, so their invoices consistently returned no PO while the remaining fields
  parsed correctly.
- **Vendor-specific fields.** Some distributors omit line descriptions entirely.
  A field should be confirmed present before a pattern is written for it.
- **Column detection.** `LINE_RE` assumes columns are separated by two or more
  spaces. Single-space layouts and wrapped descriptions are not supported.

In each case the engine raises an error rather than returning a partial invoice.
That error is the condition for routing the document to the LLM engine.

## Background

This is a simplified rebuild of extraction tooling I developed during an
internship, where it fed an accounts-payable matching pipeline. The repository
contains no production code or real invoices; all samples are synthetic.

Python 3.11+, pydantic v2, pypdf, pypdfium2, Anthropic API, openpyxl, fpdf2,
pytest. MIT.
