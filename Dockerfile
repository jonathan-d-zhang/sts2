FROM debian:bookworm-slim@sha256:13cb01d584d2c23f475c088c168a48f9a08f033a10460572fbfd10912ec5ba7c AS builder

COPY --from=ghcr.io/astral-sh/uv:latest@sha256:2bcc007f3a8713f54533bd61259966ed0f59846bd2b3d3bac9a7d9790c510599 /uv /usr/local/bin/

WORKDIR /app

# Install deps before source for layer caching
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ ./src/
RUN uv sync --frozen --no-dev


FROM debian:bookworm-slim@sha256:13cb01d584d2c23f475c088c168a48f9a08f033a10460572fbfd10912ec5ba7c

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy uv-managed Python runtime and the populated venv
COPY --from=builder /root/.local/share/uv/python /root/.local/share/uv/python
COPY --from=builder /app/.venv /app/.venv

COPY src/ ./src/
COPY site/ ./site/

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "sts2.main:app", "--host", "0.0.0.0", "--port", "8000"]
