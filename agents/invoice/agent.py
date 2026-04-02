"""
Invoice Extraction Agent — extracts structured data from invoice text.

Demonstrates: typed output with decimal precision, nested models, tool use.
"""
from shared.runtime import create_agent
from .schemas import InvoiceExtraction
from . import tools

agent = create_agent(
    name="invoice",
    output_type=InvoiceExtraction,
    instructions=(
        "You are an expert invoice processor. Given invoice text, extract all "
        "structured data: vendor info, line items, totals, dates, and tax. "
        "Use lookup_vendor to check if the vendor is already known. "
        "Use validate_tax_calculation to verify tax math. "
        "Use extract_dates to find all dates in the text. "
        "Be precise with amounts — use exact numbers from the invoice. "
        "Set confidence lower if the invoice is ambiguous or incomplete."
    ),
)


@agent.tool_plain
def lookup_vendor(name: str) -> dict:
    """Check if this vendor exists in the known vendor database."""
    return tools.lookup_vendor(name)


@agent.tool_plain
def validate_tax_calculation(subtotal: float, tax_rate: float, stated_tax: float) -> dict:
    """Verify that the tax amount on the invoice is mathematically correct."""
    return tools.validate_tax_calculation(subtotal, tax_rate, stated_tax)


@agent.tool_plain
def extract_dates(text: str) -> list[str]:
    """Extract all date patterns from the invoice text."""
    return tools.extract_dates(text)
