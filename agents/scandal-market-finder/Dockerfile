FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    pydantic \
    pydantic-ai \
    httpx \
    redis \
    langfuse \
    python-multipart \
    pyyaml

COPY shared/ ./shared/
COPY agents/scandal-market-finder/ ./agent/
RUN mkdir -p agents/scandal-market-finder && \
    cp agent/config.yaml agents/scandal-market-finder/config.yaml
COPY knowledge/ ./knowledge/

ENV PYTHONPATH=/app
ENV AGENT_NAME=scandal-market-finder

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
