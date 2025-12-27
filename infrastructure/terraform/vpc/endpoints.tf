# THE_BOT Platform - VPC Endpoints
# Gateway and Interface endpoints for AWS services

# ==========================================
# S3 Gateway Endpoint
# ==========================================

resource "aws_vpc_endpoint" "s3" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type   = "Gateway"
  route_table_ids     = concat([aws_route_table.public.id], aws_route_table.private_app[*].id)

  tags = {
    Name        = "${var.project_name}-s3-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# S3 Endpoint Policy - restrict to specific bucket
resource "aws_vpc_endpoint_policy" "s3" {
  vpc_endpoint_id = aws_vpc_endpoint.s3.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = "*"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-*",
          "arn:aws:s3:::${var.project_name}-*/*"
        ]
      }
    ]
  })
}

# ==========================================
# DynamoDB Gateway Endpoint
# ==========================================

resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type   = "Gateway"
  route_table_ids     = concat([aws_route_table.public.id], aws_route_table.private_app[*].id)

  tags = {
    Name        = "${var.project_name}-dynamodb-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# DynamoDB Endpoint Policy
resource "aws_vpc_endpoint_policy" "dynamodb" {
  vpc_endpoint_id = aws_vpc_endpoint.dynamodb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = "*"
        Action = [
          "dynamodb:*"
        ]
        Resource = "arn:aws:dynamodb:${var.aws_region}:*:*"
      }
    ]
  })
}

# ==========================================
# ECR API Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-ecr-api-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# ECR DKR Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-ecr-dkr-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# CloudWatch Logs Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "cloudwatch_logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-logs-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# CloudWatch Monitoring Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "cloudwatch_monitoring" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.monitoring"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-monitoring-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# RDS Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "rds" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.rds"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_db[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-rds-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# Secrets Manager Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "secrets_manager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-secrets-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# Systems Manager Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "systems_manager" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-ssm-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# EC2 Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "ec2" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ec2"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-ec2-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# SQS Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "sqs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.sqs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-sqs-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# SNS Interface Endpoint
# ==========================================

resource "aws_vpc_endpoint" "sns" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.sns"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private_app[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name        = "${var.project_name}-sns-endpoint"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ==========================================
# Security Group for VPC Endpoints
# ==========================================

resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.project_name}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-vpc-endpoints-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Allow HTTPS from private subnets
resource "aws_vpc_security_group_ingress_rule" "vpc_endpoints_https" {
  security_group_id = aws_security_group.vpc_endpoints.id

  description = "HTTPS from VPC"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
  cidr_ipv4   = var.vpc_cidr

  tags = {
    Name = "vpc-endpoints-https"
  }
}

# Allow HTTP from private subnets (for S3 redirect)
resource "aws_vpc_security_group_ingress_rule" "vpc_endpoints_http" {
  security_group_id = aws_security_group.vpc_endpoints.id

  description = "HTTP from VPC"
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"
  cidr_ipv4   = var.vpc_cidr

  tags = {
    Name = "vpc-endpoints-http"
  }
}

# No outbound rules needed (managed by backend SG)

# ==========================================
# Outputs
# ==========================================

output "s3_endpoint_id" {
  description = "ID of S3 Gateway Endpoint"
  value       = aws_vpc_endpoint.s3.id
}

output "dynamodb_endpoint_id" {
  description = "ID of DynamoDB Gateway Endpoint"
  value       = aws_vpc_endpoint.dynamodb.id
}

output "ecr_api_endpoint_id" {
  description = "ID of ECR API Endpoint"
  value       = aws_vpc_endpoint.ecr_api.id
}

output "ecr_dkr_endpoint_id" {
  description = "ID of ECR DKR Endpoint"
  value       = aws_vpc_endpoint.ecr_dkr.id
}

output "cloudwatch_logs_endpoint_id" {
  description = "ID of CloudWatch Logs Endpoint"
  value       = aws_vpc_endpoint.cloudwatch_logs.id
}

output "vpc_endpoints_summary" {
  description = "Summary of all VPC endpoints"
  value = {
    s3_gateway      = aws_vpc_endpoint.s3.id
    dynamodb_gateway = aws_vpc_endpoint.dynamodb.id
    ecr_api         = aws_vpc_endpoint.ecr_api.id
    ecr_dkr         = aws_vpc_endpoint.ecr_dkr.id
    cloudwatch_logs = aws_vpc_endpoint.cloudwatch_logs.id
    cloudwatch_monitoring = aws_vpc_endpoint.cloudwatch_monitoring.id
    rds             = aws_vpc_endpoint.rds.id
    secrets_manager = aws_vpc_endpoint.secrets_manager.id
    ssm             = aws_vpc_endpoint.systems_manager.id
    ec2             = aws_vpc_endpoint.ec2.id
    sqs             = aws_vpc_endpoint.sqs.id
    sns             = aws_vpc_endpoint.sns.id
  }
}

output "vpc_endpoints_security_group_id" {
  description = "ID of VPC Endpoints security group"
  value       = aws_security_group.vpc_endpoints.id
}
