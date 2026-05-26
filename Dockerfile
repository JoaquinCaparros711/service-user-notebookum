FROM python:3.12-slim

# Install system-level dependencies as root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create a non-root system user with a home directory
RUN useradd -m -u 1000 appuser

# Set up working directory with correct ownership
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy dependency specifications with correct ownership
COPY --chown=appuser:appuser pyproject.toml uv.lock* ./

# Install project dependencies using uv (creates /app/.venv)
RUN uv sync --frozen --no-cache

# Copy project source files with correct ownership
COPY --chown=appuser:appuser . .

# Expose microservice port
EXPOSE 5000

# Execute server using the non-root virtual environment
CMD ["uv", "run", "granian", "--interface", "wsgi", "main:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]
