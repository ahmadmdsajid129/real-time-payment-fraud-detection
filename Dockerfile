# ==============================================================================
# REAL-TIME PAYMENT FRAUD DETECTION & RISK ENGINE
# Production Multi-Stage Docker Container
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build React 19 + Tailwind CSS Frontend
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci || npm install

# Build production assets
COPY frontend/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Python Backend Runtime
# ------------------------------------------------------------------------------
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY database/ /app/database/
COPY services/ /app/services/
COPY ml/ /app/ml/
COPY .env.example /app/.env.example

# Copy compiled frontend distribution from Stage 1
COPY --from=frontend-builder /frontend/dist /app/frontend/dist

# Expose API and metrics port
EXPOSE 8000 9100

# Default entrypoint binds dynamically to Render's $PORT or defaults to 8000
CMD ["sh", "-c", "uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
