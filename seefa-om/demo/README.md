Demo Correlation Station

This folder contains a minimal, public-safe demo of the correlation-engine stack.
It purposefully removes proprietary Charter/Spectrum identifiers and uses mock services.

Contents
- mock/mdso_mock.py  - Minimal MDSO-like API for demo data
- mock/sense_mock.py - Minimal SENSE-like API endpoints used by frontend/tests
- docker-compose.yml - Run the demo locally with two services
- .gitlab-ci.yml     - CI/CD pipeline skeleton (build -> push -> deploy)

Goals
- Showcase full-stack behavior without exposing internal data
- Keep resource usage small so it can run on a single small EC2 instance or in EKS

Quick start (local)
1. From this folder run:

   python -m pip install -r requirements.txt
   docker-compose up --build

2. MDSO mock: http://localhost:5001
   SENSE mock: http://localhost:5002

CI/CD and AWS
- Use the provided `.gitlab-ci.yml` as a starting point. Set CI variables (AWS keys, ECR repo, KUBE_CONFIG) in GitLab.
- For a low-cost Kubernetes demo consider k3s on a t3.small EC2 for minimal cost, or EKS with a single small nodegroup for a more cloud-native demo (EKS control plane has costs).

Next steps
- I can add Kubernetes manifests (k8s/), Helm chart, and Terraform for Route53/EKS if you'd like. Tell me which infra option you prefer: lightweight k3s on EC2 (cheapest) or managed EKS (more realistic).