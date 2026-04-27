FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.30" \
    "pydantic>=2.0" \
    "pydantic-ai>=0.1" \
    "httpx>=0.27" \
    "redis>=5.0" \
    "pyyaml>=6.0" \
    "langfuse>=2.0"

COPY shared/ ./shared/
COPY agents/interview-evaluator/ ./agent/

RUN mkdir -p agents/interview-evaluator && \
    cp agent/config.yaml agents/interview-evaluator/config.yaml

COPY knowledge/ ./knowledge/

ENV PYTHONPATH=/app

EXPOSE 8025

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8025"]
