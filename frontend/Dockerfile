# =============================================================================
# Infralytix Frontend — Multi-Stage Dockerfile
# =============================================================================
# Stages:
#   builder     — npm install + vite build
#   production  — nginx serving the static build
# =============================================================================

# ── Builder: Node.js + Vite Build ────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first (Docker layer cache: npm install only re-runs
# when package.json or package-lock.json changes, not on every source change)
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies for the build)
RUN npm ci --frozen-lockfile

# Copy source files
COPY . .

# Build production bundle
# VITE_API_BASE_URL is injected at build time; default to /api for nginx proxy
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ── Production: Nginx serving static files ───────────────────────────────────
FROM nginx:1.27-alpine AS production

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx runs as root by default but we can restrict it
# The master process must bind port 80, workers can be non-root
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d

EXPOSE 80

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=5s \
    --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
