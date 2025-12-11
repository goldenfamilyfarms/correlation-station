AWS demo environment setup (minimal steps)

This file contains step-by-step commands and guidance to provision a low-cost EKS demo cluster and support resources so you can test the demo stack in AWS.

Assumptions
- You have an AWS account and permissions to create EKS clusters, EC2 instances, ECR repos, Route53 records, and IAM roles.
- You run the commands from a Bash shell (Windows: Git Bash / WSL recommended).
- You have Docker installed for building images locally.

WSL note (Windows users)
If you see a message like "Windows Subsystem for Linux has no installed distributions" when running `wsl.exe -l -v`, you have WSL available but no Linux distro installed. Installing a distro (Ubuntu) is the recommended way to run the Linux-based install commands in this guide.

To install Ubuntu on WSL (PowerShell, run as Administrator):

```powershell
# list available distributions
wsl --list --online

# install Ubuntu (recommended)
wsl --install -d Ubuntu

# After the install completes, launch the Ubuntu app from the Start menu or run:
wsl -d Ubuntu
```

Notes:
- Installing a distro requires running the PowerShell command above once from an elevated prompt.
- After installation, open the Ubuntu WSL window to finish distro setup (create username/password). Then switch to the WSL shell for the Linux install commands in this document (AWS CLI, kubectl, helm, eksctl).
- If you cannot run the elevated PowerShell command, or prefer not to install WSL, use the Windows-native installers (winget/choco/MSI) described below instead.

Install required CLIs (one-time)

# macOS / Linux / WSL (example)
# Install awscli, terraform, kubectl, helm, eksctl (optional but handy)
# On Windows use the MSI installers or package manager of choice.

# AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
s
# If you can run as root (Linux) use the default installer:
# sudo ./aws/install
# If sudo is disabled or you want a user-local install, use the installer with explicit directories:
./aws/install --install-dir "$HOME/.local/aws-cli" --bin-dir "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"

# Terraform: follow https://developer.hashicorp.com/terraform/tutorials
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl

# If you have sudo (Linux):
#   sudo mv kubectl /usr/local/bin/
# If sudo is disabled, install to a user-local bin directory instead:
mkdir -p "$HOME/.local/bin"
mv kubectl "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"

# Helm
# The official installer may attempt a system install. For a user-local install, download the release and move the binary to a user bin:
HELM_TGZ="helm-$(curl -s https://api.github.com/repos/helm/helm/releases/latest | grep tag_name | cut -d '"' -f4)-linux-amd64.tar.gz"
curl -fsSL "https://get.helm.sh/${HELM_TGZ}" -o helm.tar.gz
tar -xzf helm.tar.gz
mkdir -p "$HOME/.local/bin"
mv linux-amd64/helm "$HOME/.local/bin/helm"
chmod +x "$HOME/.local/bin/helm"
rm -rf linux-amd64 helm.tar.gz

# On Windows you can instead use Chocolatey or Scoop (PowerShell):
#   choco install kubernetes-cli awscli helm eksctl
#   scoop install kubectl awscli helm eksctl

# eksctl (optional, if you prefer)
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
# If you have sudo: sudo mv /tmp/eksctl /usr/local/bin
# If sudo is disabled, move to user-local bin:
mkdir -p "$HOME/.local/bin"
mv /tmp/eksctl "$HOME/.local/bin/eksctl"
chmod +x "$HOME/.local/bin/eksctl"

Configure AWS credentials (choose one)

# Option A (quick, less secure): AWS access keys for an IAM user with required permissions
aws configure
# Provide AWS Access Key ID, Secret Access Key, region (e.g. us-east-1), output json

# Option B (recommended for CI): OIDC provider + IAM role for GitHub/GitLab Actions. This is more secure and avoids long-lived keys.
# See Terraform snippet in the repo for OIDC/role creation. You'll still need to wire your CI provider.

Prepare Terraform inputs

# Copy the example tfvars and edit values
cp seefa-om/demo/terraform/terraform.tfvars.example seefa-om/demo/terraform/terraform.tfvars
# Edit seefa-om/demo/terraform/terraform.tfvars: set aws_region, route53_zone_id, demo_subdomain and optionally aws_account_id

Run Terraform (init -> plan -> apply)

cd seefa-om/demo/terraform
terraform init
terraform plan -out=tfplan
# Inspect tfplan and when ready:
terraform apply tfplan

Notes on costs and low-cost options
- Use a single node nodegroup with instance type t3.small (1 vCPU, 2GB RAM) for minimal cost.
- Reduce desired_count to 1. Use spot instances to reduce cost further (risk of eviction).
- Alternative: run k3s on a small EC2 t3.nano/xsmall if you only need a single-node demo.
- EKS Fargate can be used to avoid managing nodes, but for many small pods costs may be higher.

Post-provision steps

# Update kubeconfig so kubectl talks to the new cluster
aws eks --region <aws_region> update-kubeconfig --name <cluster_name>

# Create ECR repo(s) if Terraform didn't create them
aws ecr create-repository --repository-name demo/mdso --region <aws_region> || true
aws ecr create-repository --repository-name demo/sense-provisioning --region <aws_region> || true

# Build and push demo images (example)
# authenticate Docker to ECR (replace <account-id> and <region>)
aws ecr get-login-password --region <aws_region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<aws_region>.amazonaws.com

docker build -t mdso-demo seefa-om/demo/services/mdso
docker tag mdso-demo:latest <account-id>.dkr.ecr.<aws_region>.amazonaws.com/demo/mdso:latest
docker push <account-id>.dkr.ecr.<aws_region>.amazonaws.com/demo/mdso:latest

# Update k8s manifests to point to the ECR image locations (or use the GitLab CI to do this automatically with kubectl set image)

# Deploy monitoring & demo apps
seefa-om/demo/monitoring/install-monitoring.sh
kubectl apply -f seefa-om/demo/k8s/deployments.yaml

Helpful Terraform tips
- If you can't provide a Route53 zone id, skip ACM automation and manually request a cert and create DNS records.
- Use terraform workspace or different state files for experiments.

CI notes
- For GitLab CI: you can use AWS access keys as CI variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) or configure OIDC with a short-lived role.
- For GitHub Actions: configure OIDC with GitHub OIDC provider and an IAM role for the actions workflow.

If you want, I can:
- Fill in a ready-to-run terraform.tfvars (masked) with sensible defaults and a small nodegroup.
- Add a helper script to build and push all demo images to ECR and update k8s manifests with the pushed tags.
- Add Terraform snippets for OIDC-based IAM Role creation for GitLab/GitHub (I can prepare a least-privilege policy).
