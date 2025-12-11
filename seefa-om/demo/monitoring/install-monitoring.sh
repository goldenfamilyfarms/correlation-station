#!/usr/bin/env bash
set -euo pipefail

# Install monitoring stack in order and wait for readiness
# Assumes kubectl is configured and user has cluster-admin privileges for demo cluster

NAMESPACE=demo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add loki https://grafana.github.io/helm-charts
helm repo update

kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

echo "Installing Loki..."
helm upgrade --install loki grafana/loki -n ${NAMESPACE} -f seefa-om/demo/monitoring/loki-values.yaml
kubectl rollout status deployment/loki -n ${NAMESPACE} --timeout=120s || true

echo "Installing Tempo..."
helm upgrade --install tempo grafana/tempo -n ${NAMESPACE} -f seefa-om/demo/monitoring/tempo-values.yaml
kubectl rollout status deployment/tempo -n ${NAMESPACE} --timeout=120s || true

echo "Installing Prometheus stack (without Grafana)..."
helm upgrade --install kp prometheus-community/kube-prometheus-stack -n ${NAMESPACE} -f seefa-om/demo/monitoring/prometheus-values.yaml
kubectl rollout status deployment/kp-prometheus-kube-prometheus-prometheus -n ${NAMESPACE} --timeout=180s || true

echo "Installing Grafana..."
helm upgrade --install grafana grafana/grafana -n ${NAMESPACE} -f seefa-om/demo/monitoring/grafana-values.yaml
kubectl rollout status deployment/grafana -n ${NAMESPACE} --timeout=120s || true

echo "Applying Grafana provisioning ConfigMaps (datasources & dashboards)"
kubectl apply -f seefa-om/demo/monitoring/grafana-datasources-configmap.yaml -n ${NAMESPACE}
kubectl apply -f seefa-om/demo/monitoring/grafana-dashboard-configmap.yaml -n ${NAMESPACE}

# Wait for Grafana sidecar to pick up dashboards (if used)
sleep 5

echo "Installing OTEL Collector via Helm chart"
helm upgrade --install otel-collector seefa-om/demo/helm/otel-collector -n ${NAMESPACE} --create-namespace -f seefa-om/demo/helm/otel-collector/values.yaml
kubectl rollout status deployment/otel-collector -n ${NAMESPACE} --timeout=120s || true

echo "Monitoring stack install complete."

# Print service endpoints
echo "Grafana URL (port-forward):"
echo "kubectl port-forward svc/grafana 3000:80 -n ${NAMESPACE} &"
