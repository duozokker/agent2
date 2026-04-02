"""Domain tools for the invoice extraction agent."""
from __future__ import annotations


# Simulated vendor database
_VENDORS = {
    "acme": {"name": "Acme Corporation", "tax_id": "US-123456789", "default_currency": "USD"},
    "globaltech": {"name": "GlobalTech Solutions", "tax_id": "DE-987654321", "default_currency": "EUR"},
    "cloudserv": {"name": "CloudServ Inc.", "tax_id": "US-555666777", "default_currency": "USD"},
}


def lookup_vendor(name: str) -> dict:
    """Look up a vendor in the known vendor database."""
    key = name.lower().replace(" ", "").replace(".", "").replace(",", "")
    for vendor_key, vendor_data in _VENDORS.items():
        if vendor_key in key or key in vendor_data["name"].lower().replace(" ", ""):
            return vendor_data
    return {"known": False, "message": f"Vendor '{name}' not found in database"}


def validate_tax_calculation(subtotal: float, tax_rate: float, stated_tax: float) -> dict:
    """Validate that the tax calculation on the invoice is correct."""
    expected_tax = round(subtotal * tax_rate, 2)
    diff = abs(expected_tax - stated_tax)
    return {
        "expected_tax": expected_tax,
        "stated_tax": stated_tax,
        "difference": diff,
        "valid": diff <= 0.02,
    }


def extract_dates(text: str) -> list[str]:
    """Extract date-like patterns from invoice text."""
    import re
    patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{2}/\d{2}/\d{4}",
        r"\d{2}\.\d{2}\.\d{4}",
    ]
    dates = []
    for p in patterns:
        dates.extend(re.findall(p, text))
    return dates
