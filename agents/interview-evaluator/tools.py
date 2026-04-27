"""Interview evaluator tools.

The first version intentionally performs all evaluation in-model. This module
exists so future versions can add rubric libraries, Anki export, or analytics
lookups without changing the agent contract.
"""

from __future__ import annotations


def clamp_score(value: int) -> int:
    """Clamp a rubric score to 0..100."""
    return max(0, min(100, int(value)))
