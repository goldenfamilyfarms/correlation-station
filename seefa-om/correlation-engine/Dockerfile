# Multi-stage build for Correlation Engine
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash correlation && \
    chown -R correlation:correlation /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/correlation/.local

# Copy application code
COPY --chown=correlation:correlation app/ /app/app/

# Switch to non-root user
USER correlation

# Add local bin to PATH
ENV PATH=/home/correlation/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
