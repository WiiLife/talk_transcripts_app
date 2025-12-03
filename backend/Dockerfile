# ===========================
# BUILDER STAGE
# ===========================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies ONLY in builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies into a temp directory
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ===========================
# FINAL RUNTIME STAGE
# ===========================
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder stage → slimmer final image
COPY --from=builder /install /usr/local

# Copy application code
COPY . /app/backend

EXPOSE 8000

# Use --host 0.0.0.0 for Docker
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
