"""Central repository of sample natural language questions for the demo.

Add / remove questions here to update both the Streamlit sidebar and CLI script.
"""
from __future__ import annotations

from typing import List

# Ordered list of showcase questions (keep concise, business-oriented)
QUESTIONS: List[str] = [
    "Total revenue by city over the last month?",
    "Which loyalty tier has the most open support tickets?",
    "Top 3 products by total quantity sold?",
    "Average order value per loyalty tier?",
    "Open vs resolved support tickets by city?",
    "Customers with no orders yet?",
    "Revenue by product category?",
    "Daily revenue trend for the last 7 days?",
    "Support tickets per loyalty tier?",
    "Highest spending customer overall?",
]


def get_questions(limit: int | None = None) -> List[str]:
    """Return list of sample questions (optionally truncated)."""
    return QUESTIONS if limit is None else QUESTIONS[:limit]

__all__ = ["get_questions", "QUESTIONS"]
