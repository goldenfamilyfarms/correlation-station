Monitoring stack for demo

This folder contains minimal Helm values and instructions to install a lightweight monitoring stack for the demo EKS cluster. The stack includes:

- Prometheus (kube-prometheus-stack) — cluster monitoring and scraping of OTEL Collector metrics
- Grafana — dashboards and data sources (Tempo + Loki)
- Loki — log aggregation
- Tempo — trace storage

The OTEL Collector is configured to export traces to Tempo and logs to Loki. Prometheus will scrape the collector's /metrics endpoint.

Prerequisites
- Helm 3
- kubectl configured to the target cluster (EKS created by Terraform/eksctl)
- Sufficient cluster permissions to create CRDs and install charts

Quick install (example)

1. Add Helm repos

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

2. Install Loki (small values provided)

```bash
helm install loki grafana/loki -n demo --create-namespace -f seefa-om/demo/monitoring/loki-values.yaml
```

3. Install Tempo

```bash
helm install tempo grafana/tempo -n demo -f seefa-om/demo/monitoring/tempo-values.yaml
```

4. Install kube-prometheus-stack (Prometheus + Alertmanager + Grafana)

```bash
helm install kp prometheus-community/kube-prometheus-stack -n demo -f seefa-om/demo/monitoring/prometheus-values.yaml
```

5. Install Grafana (if not enabled by kube-prometheus-stack) and configure data sources

```bash
helm install grafana grafana/grafana -n demo -f seefa-om/demo/monitoring/grafana-values.yaml
```

Notes
- Values files provided are minimal and configured for a low-resource demo cluster. Adjust resource requests/limits for production.
- TLS and authentication are intentionally minimal for demo; enable RBAC and secure credentials in production.
- Once installed, OTEL Collector (installed earlier) will send traces to Tempo and logs to Loki. Grafana can be used to query both.
