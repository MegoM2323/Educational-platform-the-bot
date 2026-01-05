# Backend Docker Image - Production Optimized Multi-Stage Build
# Targets:
#  - builder: compile Python dependencies
#  - runtime: minimal production image with app code only
# Optimization:
#  - Use Debian slim instead of Alpine (faster deps compilation)
#  - Multi-stage to exclude build dependencies
#  - Pinned base image versions for reproducibility

# =============================================================================
# STAGE 1: BUILDER
# =============================================================================
FROM python:3.12-slim-bookworm AS builder

# Install build dependencies (system level)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    postgresql-client \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for layer caching
COPY backend/requirements.txt .

# Create a virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
    --prefer-binary \
    -r requirements.txt

# Clean up pip cache to reduce builder image size
RUN rm -rf /root/.cache/pip

# =============================================================================
# STAGE 2: RUNTIME
# =============================================================================
FROM python:3.12-slim-bookworm AS runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings \
    ENVIRONMENT=production

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    libssl3 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && update-ca-certificates

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directories
RUN mkdir -p /app /app/static /app/media /app/logs && \
    chown -R appuser:appuser /app

WORKDIR /app

# Copy Python virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy Django application files (excluding node_modules, .venv, etc.)
# Note: build context is project root, so we need backend/ prefix
COPY --chown=appuser:appuser backend/manage.py /app/
COPY --chown=appuser:appuser backend/config/ /app/config/
COPY --chown=appuser:appuser backend/accounts/ /app/accounts/
COPY --chown=appuser:appuser backend/applications/ /app/applications/
COPY --chown=appuser:appuser backend/assignments/ /app/assignments/
COPY --chown=appuser:appuser backend/chat/ /app/chat/
COPY --chown=appuser:appuser backend/core/ /app/core/
COPY --chown=appuser:appuser backend/invoices/ /app/invoices/
COPY --chown=appuser:appuser backend/knowledge_graph/ /app/knowledge_graph/
COPY --chown=appuser:appuser backend/materials/ /app/materials/
COPY --chown=appuser:appuser backend/notifications/ /app/notifications/
COPY --chown=appuser:appuser backend/payments/ /app/payments/
COPY --chown=appuser:appuser backend/reports/ /app/reports/
COPY --chown=appuser:appuser backend/scheduling/ /app/scheduling/
COPY --chown=appuser:appuser backend/templates/ /app/templates/
COPY --chown=appuser:appuser backend/docker-entrypoint.sh /app/

# Ensure entrypoint script is executable (must be done as root before USER switch)
RUN chmod +x /app/docker-entrypoint.sh

# Health check to monitor application readiness
# Increased start_period to 120s for DB migrations
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/api/system/health/live/ || exit 1

# Expose port
EXPOSE 8000

# Metadata labels
LABEL org.opencontainers.image.title="THE_BOT Backend" \
      org.opencontainers.image.description="Educational platform backend API" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="THE_BOT Team" \
      org.opencontainers.image.source="https://github.com/mego/THE_BOT_platform"

# Switch to non-root user AFTER all setup (including making entrypoint executable)
USER appuser

# Run with entrypoint for initialization
ENTRYPOINT ["/app/docker-entrypoint.sh"]
