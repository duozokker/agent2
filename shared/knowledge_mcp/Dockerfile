FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    "fastmcp>=2.0" \
    "httpx>=0.27" \
    "starlette>=0.40" \
    "uvicorn[standard]>=0.30"

# Copy server code
COPY shared/knowledge_mcp/server.py ./server.py

EXPOSE 9090

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9090"]
