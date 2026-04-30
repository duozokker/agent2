"""Operational learnings system for Agent2 agents.

Logs performance insights after each agent run and loads the most relevant
learnings into the next run's context. Inspired by gstack's /learn skill.

Learnings are stored per agent in ~/.agent2/learnings/{agent-name}.jsonl.
Each line is a JSON object with timestamp, insight type, and detail.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

LEARNINGS_DIR = Path(os.environ.get("AGENT2_LEARNINGS_DIR", "")) or Path.home() / ".agent2" / "learnings"
MAX_LEARNINGS_PER_AGENT = 500


def _learnings_path(agent_name: str) -> Path:
    return LEARNINGS_DIR / f"{agent_name}.jsonl"


def log_learning(
    agent_name: str,
    *,
    insight_type: str,
    key: str,
    detail: str,
    confidence: float = 0.0,
    status: str = "",
    collections: list[str] | None = None,
) -> None:
    """Append an operational learning to the agent's JSONL file."""
    path = _learnings_path(agent_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": insight_type,
        "key": key,
        "detail": detail,
        "confidence": confidence,
        "status": status,
        "collections": collections or [],
    }
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as exc:
        logger.warning("Failed to log learning for %s: %s", agent_name, exc)


def load_recent_learnings(agent_name: str, *, limit: int = 5) -> list[dict]:
    """Load the most recent learnings for an agent."""
    path = _learnings_path(agent_name)
    if not path.exists():
        return []

    entries: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        for line in reversed(lines[-MAX_LEARNINGS_PER_AGENT:]):
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(entries) >= limit:
                break
    except OSError as exc:
        logger.warning("Failed to load learnings for %s: %s", agent_name, exc)
    return entries


def format_learnings_for_prompt(learnings: list[dict]) -> str:
    """Format learnings as a prompt section for injection into _instructions."""
    if not learnings:
        return ""

    lines = ["## Operational Learnings (from previous runs)", ""]
    for entry in learnings:
        key = entry.get("key", "")
        detail = entry.get("detail", "")
        confidence = entry.get("confidence", 0)
        ts = entry.get("ts", "")[:10]
        lines.append(f"- [{ts}] **{key}** (confidence {confidence:.0%}): {detail}")
    lines.append("")
    return "\n".join(lines)


def log_after_run_insights(
    agent_name: str,
    input_data: dict,
    output: dict,
) -> None:
    """Auto-extract and log operational insights from a completed run.

    Called by the API runtime after after_run() completes. Logs insights
    about low confidence, clarification patterns, and rejection patterns.
    """
    status = output.get("status", "")
    confidence = output.get("confidence", 1.0)
    collections = []
    for ctx_key in ("mandant_kontext", "request_context", "context"):
        ctx = input_data.get(ctx_key)
        if isinstance(ctx, dict):
            raw = ctx.get("knowledge_collections", [])
            if isinstance(raw, list):
                collections = [str(c) for c in raw]
                break

    if isinstance(confidence, (int, float)) and confidence < 0.85:
        reasoning = str(output.get("reasoning", ""))[:200]
        log_learning(
            agent_name,
            insight_type="low_confidence",
            key=f"low-confidence-{status}",
            detail=f"Confidence {confidence:.2f} on status={status}. Reasoning: {reasoning}",
            confidence=confidence,
            status=status,
            collections=collections,
        )

    if status == "needs_clarification":
        clarification = output.get("clarification") or output.get("vorgeschlagene_nachricht")
        missing = ""
        if isinstance(clarification, dict):
            missing = ", ".join(clarification.get("missing_fields", clarification.get("fehlende_felder", [])))
        log_learning(
            agent_name,
            insight_type="clarification_pattern",
            key=f"clarification-{missing[:50] or 'unspecified'}",
            detail=f"Asked for clarification. Missing: {missing or 'unspecified'}",
            confidence=confidence if isinstance(confidence, (int, float)) else 0.0,
            status=status,
            collections=collections,
        )

    if status in ("rejected", "abgelehnt"):
        reason = str(output.get("rejection_reason") or output.get("ablehnungsgrund") or "")[:200]
        log_learning(
            agent_name,
            insight_type="rejection_pattern",
            key=f"rejected-{reason[:50] or 'unknown'}",
            detail=f"Rejected input. Reason: {reason or 'not specified'}",
            confidence=confidence if isinstance(confidence, (int, float)) else 0.0,
            status=status,
            collections=collections,
        )
