FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies (no uv needed -- plain pip)
RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.30" \
    "pydantic>=2.0" \
    "pydantic-ai>=0.1" \
    "pydantic-settings>=2.4" \
    "httpx>=0.27" \
    "redis>=5.0" \
    "pyyaml>=6.0" \
    "langfuse>=2.0"

# Copy shared framework
COPY shared/ ./shared/

# Copy agent code as the "agent" Python package
COPY agents/example-agent/ ./agent/

# Make config.yaml discoverable by shared.config.load_agent_config()
# which looks for agents/<name>/config.yaml relative to project root
RUN mkdir -p agents/example-agent && \
    cp agent/config.yaml agents/example-agent/config.yaml

# Copy knowledge collection metadata
COPY knowledge/ ./knowledge/

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
