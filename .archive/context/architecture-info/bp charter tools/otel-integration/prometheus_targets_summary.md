Prometheus scrape targets — inferred from Blue Planet Admin Guide + bp notes

NOTE: I do not have access to the live Blue Planet instance or exported Prometheus configs. The list below is an inferred, prioritized starting point you can use to verify and add to your real scrape_configs. Replace ports and paths with the exact values from your Deployment Guide / Prometheus config.

Recommended job names and scrape targets (suggested):

- job_name: "bp-prometheus"  # Prometheus itself (for federation / prometheus metrics)
  static_targets:
  - prom:9090

- job_name: "bp-grafana"  # Grafana (dashboard health)
  static_targets:
  - grafana:3000

- job_name: "bp-apigw"  # API gateway / ingress
  static_targets:
  - apigw:8080
  metrics_path: /metrics

- job_name: "bp-bpocore"  # bpocore service (business logic)
  static_targets:
  - bpocore:8080
  metrics_path: /metrics

- job_name: "bp-asset-manager"  # asset-manager
  static_targets:
  - asset-manager:8080
  metrics_path: /metrics

- job_name: "bp-kafka"  # Kafka broker JMX exporter (if present)
  static_targets:
  - kafka-broker-0:9404
  - kafka-broker-1:9404

- job_name: "bp-elasticsearch"  # ES metrics (if using ES exporter)
  static_targets:
  - elasticsearch:9200
  metrics_path: /_prometheus/metrics  # or _prometheus endpoint if using exporter

- job_name: "bp-postgres"  # Postgres exporter
  static_targets:
  - postgres:9187

- job_name: "bp-node-exporter"  # Host / node metrics
  static_targets:
  - host1:9100
  - host2:9100

- job_name: "bp-heroic-graphite"  # heroic / graphite metrics (if export exists)
  static_targets:
  - heroic:9100

- job_name: "bp-nagios"  # Nagios exporter or service checks
  static_targets:
  - nagios:9137

- job_name: "bp-solutionmanager"  # solman / solution manager
  static_targets:
  - solutionmanager:8080

- job_name: "bp-metrics-collector"  # "pm" metric collector mentioned in docs
  static_targets:
  - pm:9091

How to verify and extract from a live instance

1) Prometheus config file: locate `prometheus.yml` on the Prometheus server (or Solution Manager config). The `scrape_configs` block contains authoritative job names and targets.
2) Grafana dashboards: use the Grafana API to list dashboards and UIDs (see grafana_dashboards_summary.md below).
3) Kafka/JMX: check whether a JMX exporter sidecar is deployed; if so use its `/metrics` endpoint (often 9404).

Notes and caveats

- These are inferred defaults. Blue Planet deployments often put services behind a load balancer or sidecar; scrape targets may be service-discovery labels (consul/k8s_sd_configs) rather than static hostnames. In Kubernetes deployments the `kubernetes_sd_configs` should be used (use `role: pod` and relabel by pod labels).
- Ports/paths must be validated with the Blue Planet Deployment Guide and by inspecting container/service definitions. If you want, I can generate a Prometheus `scrape_configs` snippet in YAML using these targets once you confirm which hosts/ports are correct.
