OpenTelemetry integration for Blue Planet — README

Directory: `context/architecture-info/bp charter tools/otel-integration/`

Contents
- `prometheus_targets_summary.md` — inferred Prometheus scrape targets (validate against live configs).
- `grafana_dashboards_summary.md` — how to extract dashboard UIDs and export dashboards via Grafana API.
- `instrumentation_checklist.md` — 10–15 bullet OTEL + Prometheus checklist mapping spans/attributes and metrics to BP microservices.
- `otel-collector-config.yaml` — ready-to-run OpenTelemetry Collector config (starter) that receives OTLP and scrapes Prometheus targets; requires minor edits to targets/endpoints.

Quick start — Docker (BP2 / Docker Compose)

1) Place `otel-collector-config.yaml` on a host accessible to the collector and BP containers (we assume BP2 uses Docker Compose/registry for solutions).
2) Example `docker-compose` service snippet to add to your solution (Solution Manager / solman):

  otel-collector:
    image: otel/opentelemetry-collector:latest
    container_name: otel-collector
    volumes:
      - ./otel-collector-config.yaml:/etc/otel-collector-config.yaml:ro
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=${OTEL_EXPORTER_OTLP_ENDPOINT}
    command: ["--config", "/etc/otel-collector-config.yaml"]
    networks:
      - bp-bridge

3) Ensure service names used in `otel-collector-config.yaml` match your Docker Compose service names or replace with correct hostnames/IPs.
4) Start the collector: `docker-compose up -d otel-collector`

Quick start — Kubernetes

1) Create a ConfigMap from the collector config:

kubectl create configmap otel-collector-config --from-file=otel-collector-config.yaml -n observability

2) Apply the Deployment & Service (example manifest):
- See provided `k8s-collector-deployment.yaml` (if you want I can generate it). The collector needs access to the Prometheus endpoints via cluster DNS or service discovery.

Configuration tips
- OTEL_EXPORTER_OTLP_ENDPOINT should point to your tracing/metric backend collector (Tempo, Jaeger, Honeycomb, Signoz, Grafana Cloud). Set TLS settings appropriately.
- If Blue Planet is deployed on Kubernetes, prefer `kubernetes_sd_configs` in the Prometheus receiver. I can generate a K8s-optimized config if needed.
- Secure the collector's OTLP receiver (mTLS or restrict to cluster network) if you are in production.

Next steps I can do for you
- Update `otel-collector-config.yaml` to use Kubernetes service discovery instead of static targets.
- Generate a Kubernetes Deployment + Service YAML and RBAC objects for the collector and a Prometheus `ServiceMonitor` resource (for Prometheus Operator).
- Create a small script to export Grafana dashboards via API and store them in `grafana-exports/`.

Which of the next steps do you want me to take first?