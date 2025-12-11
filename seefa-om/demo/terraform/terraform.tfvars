# terraform.tfvars - ready to review and edit
aws_region = "us-east-1"
cluster_name = "demo-eks-cluster"
cluster_version = "1.28"
node_instance_type = "t3.small"
node_desired_capacity = 1
node_min_capacity = 1
node_max_capacity = 2

# Leave vpc_id empty to let the module create a new VPC
vpc_id = ""
private_subnet_ids = []
public_subnet_ids = []

# IMPORTANT: replace with your Route53 hosted zone id for goldenfamilyfarms.org
route53_zone_id = "<REPLACE_WITH_ROUTE53_ZONE_ID>"
# demo subdomain to create (DNS automation)
demo_subdomain = "net-auto-olly.gff.org"

# Optional: AWS account id -- used for ECR naming in helper scripts
aws_account_id = "<YOUR_AWS_ACCOUNT_ID>"

# CI role name (if creating OIDC role)
ci_iam_role_name = "demo-ci-role"

# Keep this file private. Do NOT commit your real secrets to git.
