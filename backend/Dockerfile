# Use a specialized uv image for dependency management
FROM astralsh/uv:python3.13-bookworm-slim AS builder

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a multi-stage build
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first for better caching
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
COPY . .

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Final stage: minimal runtime image
FROM python:3.13-slim-bookworm

WORKDIR /app

# Add non-root user for security
RUN groupadd -r app && useradd -r -g app app

# Copy the virtual environment from the builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv
# Copy application code from the builder
COPY --from=builder --chown=app:app /app /app

# Ensure data and logs directories exist and have correct permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R app:app /app/data /app/logs

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8001 \
    ENVIRONMENT=production

USER app

EXPOSE 8001

# Run with Gunicorn for production
CMD ["gunicorn", "-c", "gunicorn_conf.py", "main:app"]

