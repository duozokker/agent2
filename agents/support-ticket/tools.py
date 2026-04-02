"""Domain tools for the support ticket agent."""
from __future__ import annotations


# Simulated customer database
_CUSTOMERS = {
    "C-1001": {"name": "Acme Corp", "plan": "enterprise", "mrr": 2500, "tickets_30d": 3},
    "C-1002": {"name": "Startup Inc", "plan": "free", "mrr": 0, "tickets_30d": 12},
    "C-1003": {"name": "MegaTech GmbH", "plan": "pro", "mrr": 500, "tickets_30d": 1},
}


def lookup_customer(customer_id: str) -> dict:
    """Look up customer details by ID."""
    return _CUSTOMERS.get(customer_id, {"error": f"Customer {customer_id} not found"})


def count_words(text: str) -> int:
    """Count words in the ticket text."""
    return len(text.split())


def check_known_issues(keywords: str) -> list[dict]:
    """Check if this matches any known issues in the system."""
    known = [
        {"id": "KI-42", "title": "Login timeout on Safari 18", "status": "investigating"},
        {"id": "KI-43", "title": "CSV export missing headers", "status": "fix_deployed"},
        {"id": "KI-44", "title": "Billing webhook double-charge", "status": "resolved"},
    ]
    kw = keywords.lower()
    return [i for i in known if any(w in i["title"].lower() for w in kw.split())]
