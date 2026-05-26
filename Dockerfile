FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN useradd -m -u 1000 appuser

WORKDIR /app
RUN chown appuser:appuser /app

USER appuser

COPY --chown=appuser:appuser pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-cache

COPY --chown=appuser:appuser . .

EXPOSE 5000

CMD ["uv", "run", "granian", "--interface", "wsgi", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]
