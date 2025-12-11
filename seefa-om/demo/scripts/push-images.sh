#!/usr/bin/env bash
set -euo pipefail

# push-images.sh
# Builds demo images, pushes them to ECR, and updates k8s deployment manifests with fully-qualified image names.
# Usage: ./push-images.sh <aws_region> <aws_account_id> [tag]

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <aws_region> <aws_account_id> [tag]"
  exit 2
fi

AWS_REGION="$1"
AWS_ACCOUNT_ID="$2"
TAG="${3:-latest}"

# local paths
ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
SERVICES=("mdso" "provisioning" "compliance" "disconnect")
ECR_PREFIX="demo"

echo "Authenticating Docker to ECR in ${AWS_REGION}"
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

for svc in "${SERVICES[@]}"; do
  REPO_NAME="${ECR_PREFIX}/${svc}"
  IMAGE_NAME="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:${TAG}"

  echo "Ensuring ECR repository ${REPO_NAME} exists..."
  aws ecr describe-repositories --repository-names "${REPO_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1 || \
    aws ecr create-repository --repository-name "${REPO_NAME}" --region "${AWS_REGION}" >/dev/null

  echo "Building ${svc} image"
  docker build -t ${svc}-demo "${ROOT_DIR}/services/${svc}"
  docker tag ${svc}-demo:latest ${IMAGE_NAME}

  echo "Pushing ${IMAGE_NAME}"
  docker push ${IMAGE_NAME}

  # Update k8s manifest (simple sed; assumes deployments.yaml contains image placeholders like IMAGE_MDso)
  # We'll replace placeholders IMAGE_<SVC_UPPER> with the actual image.
  PLACEHOLDER="IMAGE_$(echo ${svc} | tr '[:lower:]' '[:upper:]')"
  echo "Updating k8s manifest placeholders: ${PLACEHOLDER} -> ${IMAGE_NAME}"
  sed -i.bak "s|${PLACEHOLDER}|${IMAGE_NAME}|g" "${ROOT_DIR}/k8s/deployments.yaml" || true

done

echo "All images pushed and k8s manifests updated. Backups saved as *.bak"
