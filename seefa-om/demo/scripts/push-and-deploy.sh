#!/usr/bin/env bash
set -euo pipefail

# push-and-deploy.sh
# Wrapper: build & push images, update k8s manifests, apply manifests and wait for rollouts.
# Usage: ./push-and-deploy.sh <aws_region> <aws_account_id> [tag] [--no-monitoring]

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <aws_region> <aws_account_id> [tag] [--no-monitoring]"
  exit 2
fi

AWS_REGION="$1"
AWS_ACCOUNT_ID="$2"
TAG="${3:-latest}"
NO_MONITORING=false
if [ "${4:-}" = "--no-monitoring" ] || [ "${3:-}" = "--no-monitoring" ]; then
  NO_MONITORING=true
fi

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="${ROOT_DIR}/scripts"
K8S_MANIFEST="${ROOT_DIR}/k8s/deployments.yaml"
MONITOR_INSTALLER="${ROOT_DIR}/monitoring/install-monitoring.sh"

# Ensure helper exists
if [ ! -x "${SCRIPTS_DIR}/push-images.sh" ]; then
  chmod +x "${SCRIPTS_DIR}/push-images.sh" || true
fi

echo "Back up k8s manifest before modifications"
cp "${K8S_MANIFEST}" "${K8S_MANIFEST}.prepush.$(date +%s)" || true

# Build & push images (this will update the placeholders in deployments.yaml)
echo "Running push-images.sh ${AWS_REGION} ${AWS_ACCOUNT_ID} ${TAG}"
"${SCRIPTS_DIR}/push-images.sh" "${AWS_REGION}" "${AWS_ACCOUNT_ID}" "${TAG}"

# Apply k8s manifests
echo "Applying k8s manifests: ${K8S_MANIFEST}"
kubectl apply -f "${K8S_MANIFEST}"

# Optionally install monitoring
if [ "$NO_MONITORING" = false ]; then
  if [ -x "${MONITOR_INSTALLER}" ]; then
    echo "Installing monitoring stack (this may take a few minutes)"
    chmod +x "${MONITOR_INSTALLER}" || true
    "${MONITOR_INSTALLER}"
  else
    echo "Monitoring installer not found: ${MONITOR_INSTALLER} — skipping monitoring install"
  fi
else
  echo "--no-monitoring set, skipping monitoring install"
fi

# Wait for rollouts of key deployments
NAMESPACE=demo
DEPLOYMENTS=(mdso-mock sense-provisioning sense-compliance sense-disconnect correlation-engine otel-collector redis)

for d in "${DEPLOYMENTS[@]}"; do
  echo "Waiting for deployment/${d} to rollout..."
  kubectl -n ${NAMESPACE} rollout status deployment/${d} --timeout=180s || {
    echo "Warning: deployment/${d} did not finish rolling out within timeout. Check 'kubectl -n ${NAMESPACE} get pods' for details." >&2
  }
done

# Wait for all pods to be ready as final check
echo "Waiting for all pods in namespace ${NAMESPACE} to be Ready (timeout 120s)"
kubectl wait --for=condition=Ready pod -l app -n ${NAMESPACE} --timeout=120s || true

echo "Deploy finished. You can check pod status with: kubectl -n ${NAMESPACE} get pods"

echo "Tip: to rollback deployments.yaml changes, you have a backup at ${K8S_MANIFEST}.prepush.*"
