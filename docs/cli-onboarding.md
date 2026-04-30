# Agent2 CLI Onboarding

Agent2 provides a two-stage onboarding flow:

```bash
curl -fsSL https://getagent2.dev/install.sh | bash
agent2 onboard
```

The hosted installer is a website deployment target. In this repo, use:

```bash
scripts/install.sh
agent2 onboard
```

## Stage 1: Static Setup

`agent2 setup` prepares the local project without asking an LLM to mutate files.

It writes:

- `.env`: OpenRouter key, selected model, API bearer token, stack profile,
  telemetry flag, and generated local service secrets.
- `agent2.yaml`: global framework defaults for model, provider policy, stack
  profile, telemetry, and framework ports.

Existing `.env` and `agent2.yaml` files are backed up before replacement.

Useful commands:

```bash
uv run agent2 setup --dry-run --json
uv run agent2 setup --profile full --telemetry
uv run agent2 setup --no-docker
```

## Stage 2: Brain Clone Harness

`agent2 onboard` interviews the domain expert, optionally lets a model polish
the interview into a validated `AgentSpec`, then writes files using deterministic
templates.

The LLM never writes project files directly.

Generated agents include:

- Sachbearbeiter Chain-of-Thought prompt checkpoints
- typed Pydantic schema with three outcomes
- `model_validator` consistency checks
- sandbox-first `pending_actions`
- `before_run`, `after_run`, and `mock_result`
- local memory/context tools
- Dockerfile, config, smoke test, and Promptfoo starter

Non-interactive generation:

```bash
uv run agent2 onboard --from-spec tests/fixtures/roofing-agent-spec.json --no-llm
```

Run the generated API:

```bash
uv run agent2 serve roofing-field-advisor
```

## Doctor

`agent2 doctor` validates local readiness:

- required binaries: Git, Docker, uv
- `.env` and `agent2.yaml`
- Docker Compose syntax
- framework config loading
- duplicate agent ports
- open local health ports

```bash
uv run agent2 doctor
uv run agent2 doctor --json
```

## Config Precedence

Model resolution is:

1. explicit runtime argument
2. agent `config.yaml`
3. `agent2.yaml`
4. `DEFAULT_MODEL` env var
5. built-in Agent2 fallback

Normal agents should use `model: ""` in `config.yaml`. Only demos that teach
provider override behavior should hardcode a model.
