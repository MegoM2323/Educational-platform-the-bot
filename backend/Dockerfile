# Backend Docker Image - Production Optimized Multi-Stage Build
# Targets:
#  - builder: compile Python dependencies
#  - runtime: minimal production image with app code only
# Size optimization:
#  - Alpine base for minimal footprint
#  - Multi-stage to exclude build dependencies
#  - Pinned base image versions for reproducibility

# =============================================================================
# STAGE 1: BUILDER
# =============================================================================
FROM python:3.13-alpine3.21 AS builder

# Install build dependencies (system level)
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    linux-headers \
    python3-dev \
    && apk add --no-cache \
    libpq

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Set working directory
WORKDIR /build

# Copy requirements first for layer caching
COPY --chown=appuser:appgroup requirements.txt .

# Create a virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/opt/venv/lib/python3.13/site-packages:$PYTHONPATH"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    --compile \
    -r requirements.txt

# Clean up pip cache to reduce builder image size
RUN rm -rf /root/.cache/pip

# =============================================================================
# STAGE 2: RUNTIME
# =============================================================================
FROM python:3.13-alpine3.21 AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/opt/venv/lib/python3.13/site-packages" \
    DJANGO_SETTINGS_MODULE=config.settings \
    ENVIRONMENT=production

# Install runtime dependencies only (no build tools)
RUN apk add --no-cache \
    libpq \
    libffi \
    openssl \
    ca-certificates \
    curl \
    && update-ca-certificates

# Create non-root user (same UID/GID as builder for consistency)
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

# Create application directories
RUN mkdir -p /app/backend /app/static /app/media && \
    chown -R appuser:appgroup /app

WORKDIR /app/backend

# Copy Python virtual environment from builder
COPY --from=builder --chown=appuser:appgroup /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Create required directories with proper permissions
RUN mkdir -p /app/logs && \
    chown -R appuser:appgroup /app/logs && \
    find /app/backend -type f -name "*.py" -exec chmod 644 {} \; && \
    find /app/backend -type d -exec chmod 755 {} \;

# Switch to non-root user
USER appuser

# Health check to monitor application readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/system/health/live/ || exit 1

# Run with Daphne (supports both ASGI and WebSocket)
# Alternative: Use gunicorn with uvicorn workers for WSGI
CMD ["daphne", \
     "-b", "0.0.0.0", \
     "-p", "8000", \
     "--access-log", "-", \
     "--verbosity", "1", \
     "config.asgi:application"]

# Expose port
EXPOSE 8000

# Metadata labels
LABEL org.opencontainers.image.title="THE_BOT Backend" \
      org.opencontainers.image.description="Educational platform backend API" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="THE_BOT Team" \
      org.opencontainers.image.source="https://github.com/mego/THE_BOT_platform"
