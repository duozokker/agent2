# Observability

## Langfuse

Langfuse is optional in Agent2.

Use it for:

- traces
- prompt registry
- token and cost tracking
- prompt and model comparisons

## Code-first by default

The framework does not require Langfuse prompts. `instructions=` in code is the default path.

Use `prompt_name=` only when you want runtime-managed prompt variants.

## What the framework emits

When Langfuse is configured, the runtime can instrument:

- agent runs
- model calls
- retries
- tool calls

## Prompt strategy

Recommended approach:

1. build the prompt in code first
2. stabilize the runtime contract
3. move to Langfuse prompt management only when iteration speed or observability needs it

## Evaluation

Promptfoo remains the recommended pre-deploy evaluation layer for agent behavior regression testing.
