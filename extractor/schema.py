"""Pydantic models for extracted invoice data.

The schema is the contract between every engine (text or LLM) and every
output format (JSON, Excel). Engines produce dicts; this module decides
whether they're valid.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class LineItem(BaseModel):
    description: str
    quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)
    amount: float = Field(ge=0)

    @model_validator(mode="after")
    def check_amount(self) -> "LineItem":
        expected = round(self.quantity * self.unit_price, 2)
        if abs(expected - self.amount) > 0.01:
            raise ValueError(
                f"line amount {self.amount} != qty*price {expected} ({self.description!r})"
            )
        return self


class Invoice(BaseModel):
    vendor_name: str
    invoice_number: str
    invoice_date: str  # ISO yyyy-mm-dd
    po_number: str | None = None
    line_items: list[LineItem] = Field(min_length=1)
    subtotal: float = Field(ge=0)
    tax: float = Field(ge=0)
    total: float = Field(ge=0)
    # engines fill this in; not part of the document itself
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_totals(self) -> "Invoice":
        """Arithmetic is validated, not trusted — LLMs and OCR both make
        number mistakes, and a wrong total in an AP system is worse than
        a rejected extraction."""
        line_sum = round(sum(li.amount for li in self.line_items), 2)
        if abs(line_sum - self.subtotal) > 0.02:
            self.warnings.append(
                f"line items sum to {line_sum}, subtotal says {self.subtotal}"
            )
        if abs(round(self.subtotal + self.tax, 2) - self.total) > 0.02:
            self.warnings.append(
                f"subtotal+tax = {round(self.subtotal + self.tax, 2)}, total says {self.total}"
            )
        return self
