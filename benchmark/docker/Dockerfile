# One pinned image for both arms and for scoring. Hidden tests are never baked in or copied here.
FROM python:3.12-slim
ARG CLAUDE_CODE_VERSION=2.1.322
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates nodejs npm \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
RUN pip install --no-cache-dir "fastapi==0.136.1" uvicorn pydantic httpx pytest ruff mypy
RUN useradd -m -u 1000 bench && mkdir /work && chown bench /work
USER bench
ENV HOME=/home/bench PYTHONDONTWRITEBYTECODE=1
WORKDIR /work
CMD ["sleep", "infinity"]
