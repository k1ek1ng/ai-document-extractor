"""LLM (vision) extraction engine.

Renders PDF pages to images and asks Claude to extract structured fields.
Used for scanned documents and layouts the text engine can't parse.
Requires ANTHROPIC_API_KEY.

Design notes:
- The model is forced through the same pydantic schema as the text engine,
  so a hallucinated or mis-read number that breaks the arithmetic checks
  becomes a validation error or warning — never silent bad data.
- Temperature 0; the task is transcription, not creativity.
"""
from __future__ import annotations

import base64
import io
import json
import os

from .schema import Invoice

MODEL = os.environ.get("EXTRACTOR_MODEL", "claude-sonnet-5")
MAX_PAGES = 4

PROMPT = """Extract the invoice fields from these page image(s).

Return ONLY a JSON object, no other text, with exactly these keys:
vendor_name (string), invoice_number (string), invoice_date (ISO yyyy-mm-dd string),
po_number (string or null), line_items (array of {description, quantity, unit_price, amount}),
subtotal (number), tax (number), total (number).

Transcribe numbers exactly as printed. Do not compute or correct anything."""


def _render_pages(path: str) -> list[bytes]:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(path)
    images = []
    for i, page in enumerate(doc):
        if i >= MAX_PAGES:
            break
        bitmap = page.render(scale=2.0)
        pil = bitmap.to_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        images.append(buf.getvalue())
    return images


def extract(path: str) -> Invoice:
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    content: list[dict] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": base64.standard_b64encode(png).decode(),
            },
        }
        for png in _render_pages(path)
    ]
    content.append({"type": "text", "text": PROMPT})

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        temperature=0,
        messages=[{"role": "user", "content": content}],
    )
    raw = response.content[0].text.strip()
    # tolerate ```json fences
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.index("{") : raw.rindex("}") + 1]

    return Invoice(**json.loads(raw))
