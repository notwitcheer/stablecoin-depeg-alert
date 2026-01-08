# Multi-stage Dockerfile for production deployment
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY . .
CMD ["python", "-m", "bot.main"]

# Production stage
FROM base as production

# Create non-root user for security
RUN groupadd -r depeguser && useradd -r -g depeguser depeguser

# Set production environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONOPTIMIZE=2

# Copy application code
COPY --chown=depeguser:depeguser . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data && \
    chown -R depeguser:depeguser /app

# Install additional production utilities
RUN pip install --no-cache-dir uvloop

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health/live')" || exit 1

# Switch to non-root user
USER depeguser

# Expose monitoring port
EXPOSE 8080

# Production startup script
COPY --chown=depeguser:depeguser docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Use entrypoint for production startup
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["bot"]

# Monitoring-only stage
FROM production as monitoring
CMD ["monitoring"]