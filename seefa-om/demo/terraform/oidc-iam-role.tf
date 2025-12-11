# Terraform snippet to create an IAM role for CI via OIDC (GitHub/GitLab)
# This is a minimal example; adapt trust policy and permissions to your org's requirements.

variable "oidc_provider_arn" {
  description = "ARN of the OIDC provider (eks module usually creates one)"
  type        = string
}

variable "ci_iam_role_name" {
  type    = string
  default = "demo-ci-role"
}

resource "aws_iam_role" "ci_oidc_role" {
  name = var.ci_iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = var.oidc_provider_arn
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            # Replace audience/issuer conditions according to your CI provider
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })
}

# Least-privilege policy for CI: allow ECR push, EKS kubeconfig update (eks:DescribeCluster) and assume role actions if needed
resource "aws_iam_policy" "ci_policy" {
  name = "demo-ci-policy"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:PutImage",
          "ecr:CreateRepository"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "eks:DescribeCluster"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "iam:PassRole"
        ],
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ci_attach" {
  role       = aws_iam_role.ci_oidc_role.name
  policy_arn = aws_iam_policy.ci_policy.arn
}
