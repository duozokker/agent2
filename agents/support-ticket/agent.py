"""
Support Ticket Agent — classifies tickets, extracts action items, drafts responses.

Demonstrates: structured output, custom tools, real-world business use case.
"""
from shared.runtime import create_agent
from .schemas import TicketAnalysis
from . import tools

agent = create_agent(
    name="support-ticket",
    output_type=TicketAnalysis,
    instructions=(
        "You are a senior customer support analyst. Given a support ticket, "
        "analyze the issue, classify it, assess urgency and sentiment, "
        "identify action items, and draft a professional response. "
        "Use lookup_customer to check the customer's plan and history. "
        "Use check_known_issues to see if this matches existing problems. "
        "Be empathetic in responses. Prioritize enterprise customers."
    ),
)


@agent.tool_plain
def lookup_customer(customer_id: str) -> dict:
    """Look up customer details including plan, MRR, and recent ticket count."""
    return tools.lookup_customer(customer_id)


@agent.tool_plain
def count_words(text: str) -> int:
    """Count the number of words in the ticket text."""
    return tools.count_words(text)


@agent.tool_plain
def check_known_issues(keywords: str) -> list[dict]:
    """Check if the reported issue matches any known problems."""
    return tools.check_known_issues(keywords)
