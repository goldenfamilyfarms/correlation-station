# OpenTelemetry Collector Gateway Dockerfile
FROM otel/opentelemetry-collector-contrib:0.91.0

# Metadata
LABEL maintainer="derrick.golden@charter.com"
LABEL description="OpenTelemetry Collector Gateway for Observability Stack"
LABEL version="1.0.0"

# Create directory for configuration
RUN mkdir -p /etc/otel-gateway

# Copy custom configuration
COPY otel-config.yaml /etc/otel-config.yaml

# Set appropriate permissions
RUN chmod 644 /etc/otel-config.yaml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["/otelcol-contrib", "validate", "--config=/etc/otel-config.yaml"]

# Expose ports
# OTLP gRPC
EXPOSE 4317
# OTLP HTTP
EXPOSE 4318
# Legacy OTLP gRPC
EXPOSE 55680
# Legacy OTLP HTTP
EXPOSE 55681
# Metrics (Prometheus)
EXPOSE 8888
# Health/zpages
EXPOSE 55679

# Use the configuration file
ENTRYPOINT ["/otelcol-contrib"]
CMD ["--config=/etc/otel-config.yaml"]