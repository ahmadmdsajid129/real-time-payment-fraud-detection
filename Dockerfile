# ==============================================================================
# REAL-TIME PAYMENT FRAUD DETECTION & RISK ENGINE
# Multi-stage Python Production Container
# ==============================================================================

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
COPY web/ /app/web/
COPY .env.example /app/.env.example

# Expose API and metrics port
EXPOSE 8000 9100

# Default entrypoint starts the FastAPI backend
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
