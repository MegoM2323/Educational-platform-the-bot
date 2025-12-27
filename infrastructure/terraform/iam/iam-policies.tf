# THE_BOT Platform - IAM Management Configuration
# Production-ready IAM roles, policies, and permission boundaries
# Follows least-privilege principle with MFA enforcement

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ==========================================
# Permission Boundaries
# ==========================================

resource "aws_iam_policy" "permission_boundary_developer" {
  name_prefix = "${var.project_name}-pb-developer-"
  description = "Permission boundary for developer role - prevents privilege escalation"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow broad permissions for development
      {
        Sid    = "AllowDevelopmentResources"
        Effect = "Allow"
        Action = [
          "ecs:*",
          "ec2:*",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "rds-db:connect",
          "logs:*",
          "cloudwatch:*",
          "ecr:*",
          "dynamodb:*",
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ]
        Resource = "*"
      },
      # Explicitly deny privilege escalation
      {
        Sid    = "DenyPrivilegeEscalation"
        Effect = "Deny"
        Action = [
          "iam:*",
          "organizations:*",
          "account:*",
          "kms:ScheduleKeyDeletion",
          "kms:DisableKey",
          "s3:DeleteBucketPolicy",
          "s3:PutBucketPolicy",
          "rds:ModifyDBInstance",
          "ec2:ModifyInstanceAttribute",
          "logs:DeleteLogGroup",
          "cloudtrail:StopLogging",
          "cloudtrail:DeleteTrail"
        ]
        Resource = "*"
      },
      # Deny access to sensitive secrets
      {
        Sid    = "DenyProductionSecrets"
        Effect = "Deny"
        Action = [
          "secretsmanager:*"
        ]
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:prod/*",
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:prod-*"
        ]
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-pb-developer"
  })
}

resource "aws_iam_policy" "permission_boundary_devops" {
  name_prefix = "${var.project_name}-pb-devops-"
  description = "Permission boundary for DevOps role - infrastructure management with guardrails"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow infrastructure management
      {
        Sid    = "AllowInfrastructureManagement"
        Effect = "Allow"
        Action = [
          "terraform:*",
          "iam:*",
          "ec2:*",
          "ecs:*",
          "rds:*",
          "s3:*",
          "cloudformation:*",
          "elasticloadbalancing:*",
          "autoscaling:*",
          "cloudwatch:*",
          "logs:*",
          "kms:*",
          "sns:*",
          "sqs:*",
          "secretsmanager:*",
          "ssm:*",
          "ecr:*",
          "dynamodb:*",
          "elasticache:*",
          "rds:*",
          "route53:*",
          "acm:*"
        ]
        Resource = "*"
      },
      # Explicitly deny account-level changes
      {
        Sid    = "DenyAccountChanges"
        Effect = "Deny"
        Action = [
          "organizations:*",
          "account:*",
          "iam:DeleteRole",
          "iam:DeleteRolePolicy",
          "iam:DeleteUser",
          "iam:DeleteGroup",
          "iam:PutUserPolicy",
          "iam:PutGroupPolicy",
          "iam:AttachUserPolicy",
          "iam:AttachGroupPolicy",
          "iam:CreateAccessKey",
          "iam:CreateSecretAccessKey"
        ]
        Resource = "*"
      },
      # Deny KMS key deletion
      {
        Sid    = "DenyKeyDeletion"
        Effect = "Deny"
        Action = [
          "kms:ScheduleKeyDeletion",
          "kms:DisableKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-pb-devops"
  })
}

resource "aws_iam_policy" "permission_boundary_admin" {
  name_prefix = "${var.project_name}-pb-admin-"
  description = "Permission boundary for admin role - full access with MFA requirement"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow all actions
      {
        Sid    = "AllowAllActions"
        Effect = "Allow"
        Action = "*"
        Resource = "*"
      },
      # Deny MFA-disabled access
      {
        Sid    = "DenyWithoutMFA"
        Effect = "Deny"
        Action = [
          "iam:*",
          "organizations:*",
          "account:*",
          "kms:ScheduleKeyDeletion",
          "kms:DisableKey"
        ]
        Resource = "*"
        Condition = {
          BoolIfExists = {
            "aws:MultiFactorAuthPresent" = "false"
          }
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-pb-admin"
  })
}

resource "aws_iam_policy" "permission_boundary_readonly" {
  name_prefix = "${var.project_name}-pb-readonly-"
  description = "Permission boundary for read-only role - view-only access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Allow read-only actions
      {
        Sid    = "AllowReadOnly"
        Effect = "Allow"
        Action = [
          "ec2:Describe*",
          "ecs:Describe*",
          "rds:Describe*",
          "s3:GetObject",
          "s3:ListBucket",
          "logs:Describe*",
          "logs:Get*",
          "cloudwatch:Get*",
          "cloudwatch:List*",
          "cloudtrail:GetTrailStatus",
          "cloudtrail:LookupEvents",
          "kms:Describe*",
          "kms:Get*",
          "kms:List*",
          "iam:Get*",
          "iam:List*",
          "secretsmanager:GetSecretValue",
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:DescribeParameters",
          "route53:List*",
          "route53:Get*",
          "acm:Describe*",
          "acm:List*"
        ]
        Resource = "*"
      },
      # Explicitly deny all write/delete actions
      {
        Sid    = "DenyModifyingActions"
        Effect = "Deny"
        Action = [
          "*:Create*",
          "*:Delete*",
          "*:Modify*",
          "*:Put*",
          "*:Update*",
          "*:Attach*",
          "*:Detach*",
          "*:StartInstances",
          "*:StopInstances",
          "*:TerminateInstances",
          "iam:*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-pb-readonly"
  })
}

# ==========================================
# Developer IAM Role
# ==========================================

resource "aws_iam_role" "developer" {
  name_prefix = "${var.project_name}-developer-role-"
  description = "Role for developers with limited infrastructure access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        }
      }
    ]
  })

  permissions_boundary = aws_iam_policy.permission_boundary_developer.arn

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-developer"
  })
}

resource "aws_iam_policy" "developer_policy" {
  name_prefix = "${var.project_name}-developer-policy-"
  description = "Policy for developer role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECS permissions
      {
        Sid    = "AllowECSOperations"
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListServices",
          "ecs:ListTasks",
          "ecs:ListTaskDefinitions",
          "ecs:UpdateService",
          "ecs:RunTask"
        ]
        Resource = [
          "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:service/${var.project_name}/*",
          "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task-definition/${var.project_name}*:*",
          "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task/${var.project_name}/*"
        ]
      },
      # S3 permissions for dev/staging only
      {
        Sid    = "AllowS3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-${var.environment}-*",
          "arn:aws:s3:::${var.project_name}-${var.environment}-*/*"
        ]
      },
      # RDS DB connect
      {
        Sid    = "AllowRDSConnect"
        Effect = "Allow"
        Action = [
          "rds-db:connect"
        ]
        Resource = [
          "arn:aws:rds:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:db:${var.project_name}-*"
        ]
      },
      # Secrets Manager read
      {
        Sid    = "AllowSecretsManagerRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/${var.environment}/*"
        ]
      },
      # KMS decrypt
      {
        Sid    = "AllowKMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:GenerateDataKey"
        ]
        Resource = "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
        Condition = {
          StringEquals = {
            "kms:ViaService" = [
              "rds.${data.aws_region.current.name}.amazonaws.com",
              "s3.${data.aws_region.current.name}.amazonaws.com"
            ]
          }
        }
      },
      # Logs permissions
      {
        Sid    = "AllowLogsAccess"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${var.project_name}*:*"
      },
      # CloudWatch permissions
      {
        Sid    = "AllowCloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics"
        ]
        Resource = "*"
      },
      # ECR permissions
      {
        Sid    = "AllowECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:DescribeImages",
          "ecr:ListImages",
          "ecr:GetAuthorizationToken"
        ]
        Resource = [
          "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/${var.project_name}/*"
        ]
      },
      # DynamoDB for staging/dev
      {
        Sid    = "AllowDynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}-${var.environment}-*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-developer-policy"
  })
}

resource "aws_iam_role_policy_attachment" "developer_policy" {
  role       = aws_iam_role.developer.name
  policy_arn = aws_iam_policy.developer_policy.arn
}

# ==========================================
# DevOps IAM Role
# ==========================================

resource "aws_iam_role" "devops" {
  name_prefix = "${var.project_name}-devops-role-"
  description = "Role for DevOps engineers with infrastructure management access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
          IpAddress = {
            "aws:SourceIp" = var.devops_allowed_ips
          }
        }
      }
    ]
  })

  permissions_boundary = aws_iam_policy.permission_boundary_devops.arn

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-devops"
  })
}

resource "aws_iam_policy" "devops_policy" {
  name_prefix = "${var.project_name}-devops-policy-"
  description = "Policy for DevOps role - infrastructure management"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Terraform state management
      {
        Sid    = "AllowTerraformState"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-terraform-state*",
          "arn:aws:s3:::${var.project_name}-terraform-state*/*",
          "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}-terraform-locks"
        ]
      },
      # Full EC2 management
      {
        Sid    = "AllowEC2Management"
        Effect = "Allow"
        Action = "ec2:*"
        Resource = "*"
      },
      # Full ECS management
      {
        Sid    = "AllowECSManagement"
        Effect = "Allow"
        Action = "ecs:*"
        Resource = "*"
      },
      # Full RDS management
      {
        Sid    = "AllowRDSManagement"
        Effect = "Allow"
        Action = "rds:*"
        Resource = "*"
      },
      # Full S3 management
      {
        Sid    = "AllowS3Management"
        Effect = "Allow"
        Action = "s3:*"
        Resource = "*"
      },
      # CloudFormation
      {
        Sid    = "AllowCloudFormation"
        Effect = "Allow"
        Action = "cloudformation:*"
        Resource = "*"
      },
      # Load Balancer management
      {
        Sid    = "AllowLoadBalancerManagement"
        Effect = "Allow"
        Action = "elasticloadbalancing:*"
        Resource = "*"
      },
      # Auto Scaling
      {
        Sid    = "AllowAutoScaling"
        Effect = "Allow"
        Action = "autoscaling:*"
        Resource = "*"
      },
      # CloudWatch and Logs
      {
        Sid    = "AllowCloudWatchManagement"
        Effect = "Allow"
        Action = [
          "cloudwatch:*",
          "logs:*"
        ]
        Resource = "*"
      },
      # KMS
      {
        Sid    = "AllowKMSManagement"
        Effect = "Allow"
        Action = "kms:*"
        Resource = "*"
      },
      # Secrets Manager
      {
        Sid    = "AllowSecretsManager"
        Effect = "Allow"
        Action = "secretsmanager:*"
        Resource = "*"
      },
      # SNS and SQS
      {
        Sid    = "AllowMessaging"
        Effect = "Allow"
        Action = [
          "sns:*",
          "sqs:*"
        ]
        Resource = "*"
      },
      # SSM for parameter store and Session Manager
      {
        Sid    = "AllowSSM"
        Effect = "Allow"
        Action = "ssm:*"
        Resource = "*"
      },
      # ECR
      {
        Sid    = "AllowECRManagement"
        Effect = "Allow"
        Action = "ecr:*"
        Resource = "*"
      },
      # Route53
      {
        Sid    = "AllowRoute53Management"
        Effect = "Allow"
        Action = "route53:*"
        Resource = "*"
      },
      # ACM
      {
        Sid    = "AllowACMManagement"
        Effect = "Allow"
        Action = "acm:*"
        Resource = "*"
      },
      # IAM read-only for Terraform
      {
        Sid    = "AllowIAMRead"
        Effect = "Allow"
        Action = [
          "iam:Get*",
          "iam:List*",
          "iam:Simulate*"
        ]
        Resource = "*"
      },
      # Pass role for services
      {
        Sid    = "AllowPassRole"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-devops-policy"
  })
}

resource "aws_iam_role_policy_attachment" "devops_policy" {
  role       = aws_iam_role.devops.name
  policy_arn = aws_iam_policy.devops_policy.arn
}

# ==========================================
# Admin IAM Role
# ==========================================

resource "aws_iam_role" "admin" {
  name_prefix = "${var.project_name}-admin-role-"
  description = "Administrator role with full access (requires MFA)"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
          IpAddress = {
            "aws:SourceIp" = var.admin_allowed_ips
          }
          Bool = {
            "aws:MultiFactorAuthPresent" = "true"
          }
        }
      }
    ]
  })

  permissions_boundary = aws_iam_policy.permission_boundary_admin.arn

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-admin"
  })
}

resource "aws_iam_policy" "admin_policy" {
  name_prefix = "${var.project_name}-admin-policy-"
  description = "Full administrator policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowAdministratorAccess"
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-admin-policy"
  })
}

resource "aws_iam_role_policy_attachment" "admin_policy" {
  role       = aws_iam_role.admin.name
  policy_arn = aws_iam_policy.admin_policy.arn
}

# ==========================================
# Read-Only IAM Role
# ==========================================

resource "aws_iam_role" "readonly" {
  name_prefix = "${var.project_name}-readonly-role-"
  description = "Read-only role for auditing and viewing infrastructure"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        }
      }
    ]
  })

  permissions_boundary = aws_iam_policy.permission_boundary_readonly.arn

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-readonly"
  })
}

resource "aws_iam_role_policy_attachment" "readonly_policy" {
  role       = aws_iam_role.readonly.name
  policy_arn = aws_iam_policy.permission_boundary_readonly.arn
}

# ==========================================
# CI/CD Service Account Role
# ==========================================

resource "aws_iam_role" "cicd_service" {
  name_prefix = "${var.project_name}-cicd-role-"
  description = "Service account role for CI/CD pipelines (GitHub Actions, GitLab CI)"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        }
      },
      # For OIDC (GitHub Actions, GitLab CI)
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.oidc_provider_url}"
        }
        Condition = {
          StringEquals = {
            "${var.oidc_provider_url}:aud" = var.oidc_client_id
            "${var.oidc_provider_url}:sub" = "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main"
          }
        }
      }
    ]
  })

  permissions_boundary = aws_iam_policy.permission_boundary_devops.arn

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-cicd"
  })
}

resource "aws_iam_policy" "cicd_policy" {
  name_prefix = "${var.project_name}-cicd-policy-"
  description = "Minimal permissions for CI/CD pipelines"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR push/pull
      {
        Sid    = "AllowECRPushPull"
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:DescribeImages",
          "ecr:ListImages",
          "ecr:GetAuthorizationToken"
        ]
        Resource = [
          "arn:aws:ecr:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:repository/${var.project_name}/*"
        ]
      },
      # ECS service update
      {
        Sid    = "AllowECSUpdate"
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:RegisterTaskDefinition"
        ]
        Resource = [
          "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:service/${var.project_name}/*",
          "arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:task-definition/${var.project_name}*:*"
        ]
      },
      # Secrets Manager read
      {
        Sid    = "AllowSecretsManagerRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
        ]
      },
      # KMS decrypt
      {
        Sid    = "AllowKMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
      },
      # IAM pass role
      {
        Sid    = "AllowPassRole"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-ecs-task-execution-role",
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-ecs-task-role"
        ]
      },
      # CloudWatch logs
      {
        Sid    = "AllowCloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${var.project_name}*:*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-cicd-policy"
  })
}

resource "aws_iam_role_policy_attachment" "cicd_policy" {
  role       = aws_iam_role.cicd_service.name
  policy_arn = aws_iam_policy.cicd_policy.arn
}

# ==========================================
# Service Accounts for ECS Tasks
# ==========================================

resource "aws_iam_role" "ecs_task_execution_role" {
  name_prefix = "${var.project_name}-ecs-task-execution-role-"
  description = "ECS task execution role for pulling images and logs"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ecs-task-execution-role"
  })
}

resource "aws_iam_policy" "ecs_task_execution_policy" {
  name_prefix = "${var.project_name}-ecs-task-execution-policy-"
  description = "ECS task execution policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR permissions
      {
        Sid    = "AllowECRPull"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = "*"
      },
      # CloudWatch Logs
      {
        Sid    = "AllowCloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${var.project_name}*:*"
      },
      # Secrets Manager for sensitive environment variables
      {
        Sid    = "AllowSecretsManagerRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/*"
      },
      # KMS for encrypted secrets
      {
        Sid    = "AllowKMSDecrypt"
        Effect = "Allow"
        Action = [
          "kms:Decrypt"
        ]
        Resource = "arn:aws:kms:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:key/*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ecs-task-execution-policy"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_task_execution_policy.arn
}

# ==========================================
# Application Task Role (for containers)
# ==========================================

resource "aws_iam_role" "ecs_task_role" {
  name_prefix = "${var.project_name}-ecs-task-role-"
  description = "ECS task role for application permissions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ecs-task-role"
  })
}

resource "aws_iam_policy" "ecs_task_role_policy" {
  name_prefix = "${var.project_name}-ecs-task-policy-"
  description = "ECS task application policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 access for uploads
      {
        Sid    = "AllowS3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-${var.environment}-*/*"
      },
      # RDS database connection
      {
        Sid    = "AllowRDSAccess"
        Effect = "Allow"
        Action = [
          "rds-db:connect"
        ]
        Resource = "arn:aws:rds:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:db:${var.project_name}-*"
      },
      # ElastiCache
      {
        Sid    = "AllowElastiCacheAccess"
        Effect = "Allow"
        Action = [
          "elasticache:DescribeCacheClusters"
        ]
        Resource = "*"
      },
      # DynamoDB
      {
        Sid    = "AllowDynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = "arn:aws:dynamodb:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:table/${var.project_name}-${var.environment}-*"
      },
      # SNS and SQS
      {
        Sid    = "AllowMessaging"
        Effect = "Allow"
        Action = [
          "sns:Publish",
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          "arn:aws:sns:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.project_name}-*",
          "arn:aws:sqs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:${var.project_name}-*"
        ]
      },
      # CloudWatch metrics
      {
        Sid    = "AllowCloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      # Secrets Manager for application secrets
      {
        Sid    = "AllowSecretsManagerRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/${var.environment}/*"
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-ecs-task-policy"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_role_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_role_policy.arn
}

# ==========================================
# Data Sources
# ==========================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}
