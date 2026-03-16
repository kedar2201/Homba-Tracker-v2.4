# Multi-stage build for smaller production image
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Add non-root user for security
RUN groupadd -r app && useradd -r -g app app

# Copy only necessary files from builder
COPY --from=builder /root/.local /home/app/.local
COPY . .

# Ensure app user has access to necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R app:app /app

# Set path for user-installed packages
ENV PATH=/home/app/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

USER app

# Default environment variables
ENV ENVIRONMENT=production
ENV PORT=8001

EXPOSE 8001

# Run with Gunicorn for production
CMD ["gunicorn", "-c", "gunicorn_conf.py", "main:app"]

