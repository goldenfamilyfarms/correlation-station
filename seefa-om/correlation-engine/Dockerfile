# FROM artifactory.spectrumflow.net/docker-local/python:3.11-slim

# WORKDIR /app

# # Proxy configuration
# ARG HTTP_PROXY=http://173.197.207.115:3128/
# ARG HTTPS_PROXY=http://173.197.207.115:3128/
# ARG NO_PROXY=localhost,127.0.0.1,::1,.charter.com,.chtrse.com,.spectrumtoolbox.com,.spectrumflow.net,artifactory.spectrumtoolbox.com,docker-artifactory.spectrumflow.net
# ARG ARTIFACTORY_USER=derrick.golden@charter.com
# ARG ARTIFACTORY_TOKEN=AKCpBwCnpmSNG3fGSpoZ22YNEo4uW2vCUuffXxQbX2TxBQCipxeMLFBVKR18D3kqf1VZFp93Q
# ENV HTTP_PROXY=${HTTP_PROXY}
# ENV HTTPS_PROXY=${HTTPS_PROXY}
# ENV NO_PROXY=${NO_PROXY}
# ENV ARTIFACTORY_USER={ARTIFACTORY_USER}
# ENV ARTIFACTORY_TOKEN={ARTIFACTORY_TOKEN}

# # Install dependencies
# COPY requirements.txt .

# # Configure pip to use Artifactory with auth
# RUN pip install --upgrade pip && \
#     pip install --no-cache-dir -r requirements.txt \
#     --index-url https://derrick.golden@charter.com:AKCpBwCnpmSNG3fGSpoZ22YNEo4uW2vCUuffXxQbX2TxBQCipxeMLFBVKR18D3kqf1VZFp93Q@docker-artifactory.spectrumflow.net/artifactory/api/pypi/pypi-local/simple \
#     --trusted-host docker-artifactory.spectrumflow.net;
# # Copy application


# [global]
# index-url = https://derrick.golden@charter.com:AKCpBwCnpmSNG3fGSpoZ22YNEo4uW2vCUuffXxQbX2TxBQCipxeMLFBVKR18D3kqf1VZFp93Q@artifactory.spectrumflow.net/artifactory/api/pypi/pypi/simple

# # Expose port
# EXPOSE 8080

# # Run as non-root user
# RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
# USER apiuser

# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# # Start application
# CMD ["python", "main.py"]


# # FROM artifactory.spectrumflow.net/docker-local/python:3.11-slim

# # WORKDIR /app

# # # Proxy configuration
# # ARG HTTP_PROXY=http://173.197.207.115:3128/
# # ARG HTTPS_PROXY=http://173.197.207.115:3128/
# # ARG NO_PROXY=localhost,127.0.0.1,::1,.charter.com,.chtrse.com,.spectrumtoolbox.com,.spectrumflow.net,artifactory.spectrumtoolbox.com,docker-artifactory.spectrumflow.net
# # ENV HTTP_PROXY=${HTTP_PROXY}
# # ENV HTTPS_PROXY=${HTTPS_PROXY}
# # ENV NO_PROXY=${NO_PROXY}

# # # Artifactory credentials (pass as build args)
# # ARG ARTIFACTORY_USER
# # ARG ARTIFACTORY_TOKEN

# # # Install dependencies
# # COPY requirements.txt .

# # # Configure pip to use Artifactory with auth
# # RUN if [ -n "$ARTIFACTORY_USER" ] && [ -n "$ARTIFACTORY_TOKEN" ]; then \
# #         pip install --upgrade pip && \
# #         pip install --no-cache-dir -r requirements.txt \
# #             --index-url https://${ARTIFACTORY_USER}:${ARTIFACTORY_TOKEN}@docker-artifactory.spectrumflow.net/artifactory/api/pypi/pypi-local/simple \
# #             --trusted-host docker-artifactory.spectrumflow.net; \
# #     else \
# #         echo "ERROR: ARTIFACTORY_USER and ARTIFACTORY_TOKEN build args required" && exit 1; \
# #     fi

# # # Copy application
# # COPY main.py .

# # # Expose port
# # EXPOSE 8080

# # # Run as non-root user
# # RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
# # USER apiuser

# # # Health check
# # HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
# #     CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# # # Start application
# # CMD ["python", "main.py"]


# # FROM artifactory.spectrumflow.net/docker-local/python:3.11-slim

# # WORKDIR /app

# # # Proxy configuration
# # ARG HTTP_PROXY=http://173.197.207.115:3128/
# # ARG HTTPS_PROXY=http://173.197.207.115:3128/
# # ARG NO_PROXY=localhost,127.0.0.1,::1,.charter.com,.chtrse.com,.spectrumtoolbox.com,.spectrumflow.net,artifactory.spectrumtoolbox.com,docker-artifactory.spectrumflow.net
# # ENV HTTP_PROXY=${HTTP_PROXY}
# # ENV HTTPS_PROXY=${HTTPS_PROXY}
# # ENV NO_PROXY=${NO_PROXY}

# # # Copy pip configuration with credentials
# # # Create this file: correlation-engine/pip.conf
# # COPY pip.conf /etc/pip.conf

# # # Install dependencies
# # COPY requirements.txt .
# # RUN pip install --upgrade pip && \
# #     pip install --no-cache-dir -r requirements.txt

# # # Remove pip.conf to not expose credentials in final image
# # RUN rm -f /etc/pip.conf

# # # Copy application
# # COPY main.py .

# # # Expose port
# # EXPOSE 8080

# # # Run as non-root user
# # RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
# # USER apiuser

# # # Health check
# # HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
# #     CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# # # Start application
# # # CMD ["python", "main.py"]

# FROM artifactory.spectrumflow.net/docker-local/python:3.11-slim

# WORKDIR /app

# # Proxy configuration
# ARG HTTP_PROXY=http://173.197.207.115:3128/
# ARG HTTPS_PROXY=http://173.197.207.115:3128/
# ARG NO_PROXY=localhost,127.0.0.1,::1,.charter.com,.chtrse.com,.spectrumtoolbox.com,.spectrumflow.net,artifactory.spectrumtoolbox.com,docker-artifactory.spectrumflow.net
# ENV HTTP_PROXY=${HTTP_PROXY}
# ENV HTTPS_PROXY=${HTTPS_PROXY}
# ENV NO_PROXY=${NO_PROXY}

# # Artifactory credentials (pass as build args)
# ARG ARTIFACTORY_USER
# ARG ARTIFACTORY_TOKEN

# # Install dependencies
# COPY requirements.txt .

# # Configure pip to use Artifactory with auth and PyPI fallback
# RUN if [ -n "$ARTIFACTORY_USER" ] && [ -n "$ARTIFACTORY_TOKEN" ]; then \
#         pip install --upgrade pip && \
#         pip install --no-cache-dir -r requirements.txt \
#             --index-url https://derrick.golden@charter.com:AKCpBwCnpmSNG3fGSpoZ22YNEo4uW2vCUuffXxQbX2TxBQCipxeMLFBVKR18D3kqf1VZFp93Q@docker-artifactory.spectrumflow.net/artifactory/api/pypi/pypi-local/simple \
#             --extra-index-url https://pypi.org/simple \
#             --trusted-host docker-artifactory.spectrumflow.net; \
#     else \
#         echo "ERROR: ARTIFACTORY_USER and ARTIFACTORY_TOKEN build args required" && exit 1; \
#     fi

# # Copy application
# COPY main.py .

# # Copy application
# COPY main.py .

# # Expose port
# EXPOSE 8080

# # Run as non-root user
# RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
# USER apiuser

# # Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# # Start application
# CMD ["python", "main.py"]
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