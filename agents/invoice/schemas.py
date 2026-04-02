"""Output schemas for the invoice extraction agent."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """A single line item on the invoice."""

    description: str = Field(description="Item or service description")
    quantity: float = Field(ge=0, description="Quantity")
    unit_price: Decimal = Field(description="Price per unit")
    total: Decimal = Field(description="Line total (quantity * unit_price)")
    tax_rate: float | None = Field(default=None, description="Tax rate if shown (e.g. 0.19)")


class InvoiceExtraction(BaseModel):
    """Structured data extracted from an invoice."""

    vendor_name: str = Field(description="Name of the vendor / issuer")
    vendor_address: str = Field(default="", description="Vendor address if available")
    invoice_number: str = Field(description="Invoice number")
    invoice_date: str = Field(description="Invoice date (YYYY-MM-DD)")
    due_date: str | None = Field(default=None, description="Payment due date if shown")
    currency: str = Field(default="USD", description="Currency code")
    subtotal: Decimal = Field(description="Subtotal before tax")
    tax_amount: Decimal = Field(description="Total tax amount")
    total: Decimal = Field(description="Grand total including tax")
    line_items: list[LineItem] = Field(description="Extracted line items")
    payment_terms: str | None = Field(default=None, description="Payment terms if mentioned")
    document_type: Literal["invoice", "credit_note", "receipt", "quote", "other"] = Field(
        description="Type of document"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the extraction")
