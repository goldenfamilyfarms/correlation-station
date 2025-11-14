Grafana dashboards — summary + how to extract UIDs

Note: I don't have access to your live Grafana. Use the commands below against your Grafana instance to export real dashboard UIDs and JSON exports.

Likely important dashboards to look for (names to search for in Grafana):

- BP Application Overview
- BP Common Troubleshooting
- BP System Health / Node Exporter
- BP Kafka Overview
- BP Elasticsearch / Kibana Metrics
- BP PostgreSQL / DB Metrics
- BP Prometheus / Alertmanager Overview
- BP Grafana: Application dashboards for `mdso`, `bpo`, `bpocore`, `asset-manager`, `solutionmanager`

How to list dashboards and get UIDs (Grafana HTTP API)

1) List folders and dashboards (requires an API key with `Viewer` or higher):

curl -s -H "Authorization: Bearer ${GRAFANA_API_KEY}" "https://<grafana-host>:3000/api/search?query=BP"

This returns an array of dashboards with the fields `uid`, `title`, `uri`.

2) Get a dashboard by UID:

curl -s -H "Authorization: Bearer ${GRAFANA_API_KEY}" "https://<grafana-host>:3000/api/dashboards/uid/<UID>" > dashboard-<UID>.json

3) Recommended exports:
- Export JSON for each critical dashboard (store under `context/architecture-info/bp charter tools/otel-integration/grafana-exports/`).
- Record UID, title, and a one-line purpose for each dashboard in a small index file.

If you want, I can generate a small script (shell or Python) that accepts a list of dashboard names and uses the Grafana API to fetch UIDs and JSON exports. Want me to create that next?