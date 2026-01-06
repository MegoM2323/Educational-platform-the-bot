# Frontend Docker Image - Production Optimized Multi-Stage Build
# Targets:
#  - builder: build React application with Vite
#  - nginx: serve built application with nginx (minimal image)
# Size optimization:
#  - Multi-stage to exclude build dependencies (node_modules removed)
#  - Alpine nginx for minimal runtime
#  - Pinned base image versions for reproducibility
#  - Build optimization with layer caching

# =============================================================================
# STAGE 1: BUILDER
# =============================================================================
# Use Node.js slim image to ensure all optional dependencies are available
FROM node:22-slim AS builder

# Set working directory
WORKDIR /build

# Copy all frontend files
# Note: build context is project root, so we need frontend/ prefix
COPY frontend/ .

# Install dependencies with optimized flags
# Use --legacy-peer-deps for compatibility with all dependencies
RUN npm install --no-fund --legacy-peer-deps && \
    npm cache clean --force

# Build application with production optimizations
# Vite automatically applies tree-shaking, minification, etc.
# Use build:docker to skip build-monitor.js which fails in Docker
RUN npm run build:docker 2>&1

# Verify build output
RUN if [ ! -d "dist" ]; then echo "Build failed: dist directory not found" && exit 1; fi && \
    ls -lh dist/

# =============================================================================
# STAGE 2: RUNTIME
# =============================================================================
FROM nginx:1.27-alpine

# Set metadata
LABEL org.opencontainers.image.title="THE_BOT Frontend" \
      org.opencontainers.image.description="Educational platform React frontend" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="THE_BOT Team" \
      org.opencontainers.image.source="https://github.com/mego/THE_BOT_platform"

# Create non-root user for security
RUN addgroup -g 1001 -S www && \
    adduser -u 1001 -S www-data -G www

# Install additional packages needed at runtime
RUN apk add --no-cache \
    curl \
    ca-certificates \
    && update-ca-certificates

# Copy nginx configuration
# Note: build context is project root, so we need frontend/ prefix
COPY frontend/nginx.conf /etc/nginx/nginx.conf
COPY frontend/nginx-default.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder stage
COPY --from=builder --chown=www-data:www /build/dist /usr/share/nginx/html

# Create required directories with proper permissions
RUN mkdir -p /var/cache/nginx /var/run/nginx /var/log/nginx && \
    chown -R www-data:www /usr/share/nginx/html && \
    chown -R www-data:www /var/cache/nginx && \
    chown -R www-data:www /var/run/nginx && \
    chown -R www-data:www /var/log/nginx

# Make nginx cache and logs writable by www-data user
RUN chmod -R 755 /usr/share/nginx/html && \
    chmod -R 755 /var/cache/nginx && \
    chmod -R 755 /var/log/nginx && \
    chmod -R 755 /etc/nginx/conf.d

# Expose port
EXPOSE 3000

# Health check to monitor application readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
