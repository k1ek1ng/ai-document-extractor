# ai-document-extractor

Invoice PDFs to validated JSON and Excel.

Two engines behind one schema:

| engine | how | when |
|---|---|---|
| `text` | reads the PDF's embedded text layer with patterns — no network, no cost, deterministic | digital PDFs with a known layout |
| `llm` | renders pages to images, a vision model extracts the fields | scans, photos, layouts the patterns do not know |

Both emit into the same pydantic model, which checks the arithmetic: quantity x
unit price = line amount, lines sum to subtotal, subtotal + tax = total. Line
arithmetic is a hard failure; the invoice-level checks attach warnings rather
than rejecting, because a real invoice can legitimately carry a charge that is
not on any line — and knowing that is different from silently accepting it.

That distinction is the whole point of the schema. A model that reads `1,240.00`
as `124.00` produces a perfectly well-formed object. Only the arithmetic catches
it.

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

Output is one JSON per invoice plus a combined `invoices.xlsx` — a summary sheet
and a line-item sheet, with a warnings column.

Samples are generated with known values, so extraction accuracy is a test rather
than a judgment call: `tests/test_extractor.py` compares output against the
ground-truth JSON emitted alongside each PDF.

## Where the text engine breaks

Worth being specific, because the failure modes are the interesting part and they
generalize:

- **Separators inside identifiers.** A pattern like `PO\d{6}` misses `PO 123456`.
  I hit exactly this on real invoices — a PO reference that printed with a space,
  most often from Spanish-language suppliers whose layout differed, so a whole
  vendor family silently came back with no PO. Everything else about those
  invoices parsed fine, which is what made it slow to notice.
- **Fields that exist for some vendors and not others.** Line descriptions are
  populated by some distributors and absent from others. Before adding a capture
  pattern, check whether the field is actually printed — otherwise you are
  writing a pattern for a field that is not there.
- **Column detection by whitespace runs.** `LINE_RE` assumes two or more spaces
  separate columns. A single-space layout, or a wrapped description, breaks it.
  It fails loudly (no lines matched, use the llm engine) rather than returning a
  partial invoice, which is the right failure but still a failure.

The routing rule that falls out: run the cheap deterministic engine first, and
have it tell you when to escalate. The text engine raises rather than guessing,
so escalation is a signal, not a fallback that quietly degrades.

## Origin

A generic rebuild of extraction tooling I built during an internship at Cypress
Industries, where it fed an AP invoice matcher. This repo contains none of that
code and no real documents — every sample is synthetic.

Python 3.11+, pydantic v2, pypdf, pypdfium2, Anthropic API, openpyxl, fpdf2,
pytest. MIT.
