# Promptfoo Eval Suites

[Promptfoo](https://www.promptfoo.dev/) is a CLI tool for evaluating LLM outputs
before deploying. It tests agent prompts against datasets and asserts quality.

## Installation

```bash
npm install -g promptfoo
```

## Running Evals

```bash
# Start the agent first
docker compose up -d example-agent

# Run eval for example agent
npx promptfoo eval -c tests/promptfoo/example-agent/eval.yaml

# Run eval for the full Brain Clone flagship agent
npx promptfoo eval -c tests/promptfoo/procurement-compliance-officer/eval.yaml

# View results
npx promptfoo view

# Run all evals
for dir in tests/promptfoo/*/; do
  npx promptfoo eval -c "$dir/eval.yaml"
done
```

## Directory Structure

```
tests/promptfoo/
  example-agent/
    eval.yaml        # Eval config for the example summarisation agent
    dataset.json     # Reusable test inputs
  procurement-compliance-officer/
    eval.yaml        # Eval config for the full Brain Clone flagship agent
    dataset.json     # Reusable purchase-request inputs
```

## Writing New Evals

1. Create a new directory under `tests/promptfoo/` named after your agent.
2. Add an `eval.yaml` with providers, prompts, and test assertions.
3. Optionally add a `dataset.json` for reusable test inputs.
4. Run with `npx promptfoo eval -c tests/promptfoo/<agent>/eval.yaml`.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_TOKEN` | Bearer token for agent API | `dev-token-change-me` |
| `AGENT_HOST` | Base URL of the agent | `http://localhost` |

Override them inline:

```bash
AGENT_TOKEN=my-secret npx promptfoo eval -c tests/promptfoo/example-agent/eval.yaml
```
