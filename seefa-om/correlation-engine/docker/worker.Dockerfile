FROM python:3.11-slim

WORKDIR /app

# Install system deps for reportlab (minimal) and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY correlation-engine/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir rq

# Copy app into image
COPY correlation-engine /app

ENV PYTHONPATH=/app

CMD ["bash", "-lc", "python -m rq worker -u ${REDIS_URL:-redis://redis:6379/0} seca"]
