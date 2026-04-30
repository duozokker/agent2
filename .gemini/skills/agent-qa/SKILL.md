---
name: agent-qa
description: End-to-end QA testing for Agent2 agents. Starts the agent service, sends real API requests from eval datasets, validates responses against the output schema, and generates a health report with confidence stats. Use when asked to "test this agent", "QA the agent", "does this agent work", or "run agent health check".
---

# Agent QA

End-to-end testing for a deployed or locally running Agent2 agent.

## When to Use

- After generating a new agent with `/brain-clone` or `/creating-agents`
- After changing an agent's prompt, tools, or schema
- Before shipping an agent to production
- When debugging unexpected agent behavior

## Workflow

### Step 1: Identify the agent

Ask which agent to test if not obvious from context:

```bash
ls agents/*/config.yaml 2>/dev/null | sed 's|agents/||;s|/config.yaml||'
```

### Step 2: Load test cases

Check for existing eval datasets:

```bash
AGENT_NAME="<agent-name>"
EVAL_FILE="tests/promptfoo/$AGENT_NAME/dataset.json"
if [ -f "$EVAL_FILE" ]; then
  echo "EVAL_FOUND: $EVAL_FILE"
  cat "$EVAL_FILE"
else
  echo "NO_EVAL_DATASET"
fi
```

If `NO_EVAL_DATASET`: generate test cases from the agent's example cases in
config.yaml and the prompt in agent.py. Create at least 3 cases:
1. A case that should return the primary complete outcome
2. An empty/incomplete case that should trigger needs_clarification
3. A case with a defect that should trigger rejected (if applicable)

### Step 3: Start the agent

```bash
# Check if already running
AGENT_PORT=$(grep "port:" "agents/$AGENT_NAME/config.yaml" | awk '{print $2}')
curl -s "http://localhost:$AGENT_PORT/health" 2>/dev/null && echo "ALREADY_RUNNING" || echo "NEEDS_START"
```

If `NEEDS_START`:
```bash
uv run agent2 serve "$AGENT_NAME" &
AGENT_PID=$!
sleep 3
curl -s "http://localhost:$AGENT_PORT/health"
```

### Step 4: Run test cases

For each test case, send a real POST /tasks request:

```bash
curl -s -X POST "http://localhost:$AGENT_PORT/tasks?mode=sync" \
  -H "Authorization: Bearer dev-token-change-me" \
  -H "Content-Type: application/json" \
  -d '{"input": <test-case-input>}'
```

For each response, validate:
1. HTTP status is 200
2. Response contains `"status": "completed"`
3. `result` is present and contains the expected schema fields
4. `result.status` matches expected outcome (if specified in test case)
5. `result.confidence` is a number between 0 and 1
6. `result.reasoning` is non-empty
7. `result.review_steps` is a non-empty list
8. Schema consistency: no contradictory fields (e.g., complete + rejection_reason)

### Step 5: Generate health report

```
AGENT QA REPORT: {agent-name}
═══════════════════════════════════════

Tests run:     {total}
Passed:        {passed}
Failed:        {failed}

| # | Case | Expected | Got | Confidence | Pass |
|---|------|----------|-----|------------|------|
| 1 | ... | complete | complete | 0.87 | ✓ |
| 2 | ... | clarification | clarification | 0.65 | ✓ |
| 3 | ... | rejected | complete | 0.45 | ✗ |

Confidence stats:
  Mean:   {mean}
  Min:    {min}
  Max:    {max}
  <0.85:  {count} ({pct}%)

Issues found:
  - {issue description}

Recommendation: {SHIP / FIX_BEFORE_SHIP / NEEDS_WORK}
```

### Step 6: Check learnings

If the agent has operational learnings, show them:

```bash
LEARN_FILE="$HOME/.agent2/learnings/$AGENT_NAME.jsonl"
if [ -f "$LEARN_FILE" ]; then
  echo "LEARNINGS:"
  tail -10 "$LEARN_FILE"
else
  echo "No learnings yet (agent hasn't processed real cases)"
fi
```

### Step 7: Cleanup

If we started the agent in Step 3:
```bash
kill $AGENT_PID 2>/dev/null
```

## Completion Status

Report status as:
- **PASS** — all tests passed, confidence healthy
- **PASS_WITH_CONCERNS** — tests passed but confidence is low or edge cases untested
- **FAIL** — test failures found, list what's broken
- **BLOCKED** — agent couldn't start or API unreachable
