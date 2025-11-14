# Multi-stage build for Correlation Engine Enhanced
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 1000 -s /bin/bash correlation && \
    chown -R correlation:correlation /app

COPY --from=builder /root/.local /home/correlation/.local

COPY --chown=correlation:correlation app/ /app/app/

USER correlation

ENV PATH=/home/correlation/.local/bin:$PATH

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
