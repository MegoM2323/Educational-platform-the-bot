# THE_BOT Platform - Security Groups

# ==========================================
# Bastion Security Group (Jump Host)
# ==========================================

resource "aws_security_group" "bastion" {
  name        = "${var.project_name}-bastion-sg"
  description = "Security group for Bastion host"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-bastion-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# SSH access to Bastion from allowed IPs
resource "aws_vpc_security_group_ingress_rule" "bastion_ssh" {
  security_group_id = aws_security_group.bastion.id

  description = "SSH access to Bastion"
  from_port   = 22
  to_port     = 22
  ip_protocol = "tcp"
  cidr_ipv4   = var.bastion_allowed_cidr

  tags = {
    Name = "bastion-ssh"
  }
}

# Bastion to anywhere (outbound)
resource "aws_vpc_security_group_egress_rule" "bastion_outbound" {
  security_group_id = aws_security_group.bastion.id

  description = "Outbound traffic from Bastion"
  from_port   = 0
  to_port     = 65535
  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "bastion-outbound"
  }
}

# ==========================================
# Frontend/ALB Security Group
# ==========================================

resource "aws_security_group" "frontend" {
  name        = "${var.project_name}-frontend-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-frontend-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# HTTP access (port 80)
resource "aws_vpc_security_group_ingress_rule" "frontend_http" {
  security_group_id = aws_security_group.frontend.id

  description = "HTTP access"
  from_port   = 80
  to_port     = 80
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "frontend-http"
  }
}

# HTTPS access (port 443)
resource "aws_vpc_security_group_ingress_rule" "frontend_https" {
  security_group_id = aws_security_group.frontend.id

  description = "HTTPS access"
  from_port   = 443
  to_port     = 443
  ip_protocol = "tcp"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "frontend-https"
  }
}

# ALB outbound to backend
resource "aws_vpc_security_group_egress_rule" "frontend_to_backend" {
  security_group_id = aws_security_group.frontend.id

  description              = "Outbound to backend"
  from_port                = 8000
  to_port                  = 8000
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.backend.id

  tags = {
    Name = "frontend-to-backend"
  }
}

# ALB outbound to anywhere (for DNS, etc.)
resource "aws_vpc_security_group_egress_rule" "frontend_outbound" {
  security_group_id = aws_security_group.frontend.id

  description = "Outbound traffic from ALB"
  from_port   = 0
  to_port     = 65535
  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "frontend-outbound"
  }
}

# ==========================================
# Backend/ECS Security Group
# ==========================================

resource "aws_security_group" "backend" {
  name        = "${var.project_name}-backend-sg"
  description = "Security group for backend application servers"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-backend-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Ingress from ALB
resource "aws_vpc_security_group_ingress_rule" "backend_from_alb" {
  security_group_id = aws_security_group.backend.id

  description              = "Traffic from ALB"
  from_port                = 8000
  to_port                  = 8000
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.frontend.id

  tags = {
    Name = "backend-from-alb"
  }
}

# Ingress from Bastion (SSH)
resource "aws_vpc_security_group_ingress_rule" "backend_from_bastion" {
  security_group_id = aws_security_group.backend.id

  description              = "SSH from Bastion"
  from_port                = 22
  to_port                  = 22
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.bastion.id

  tags = {
    Name = "backend-from-bastion"
  }
}

# Ingress for Redis communication
resource "aws_vpc_security_group_ingress_rule" "backend_from_redis" {
  security_group_id = aws_security_group.backend.id

  description              = "Redis connection"
  from_port                = 6379
  to_port                  = 6379
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.redis.id

  tags = {
    Name = "backend-from-redis"
  }
}

# Backend to database
resource "aws_vpc_security_group_egress_rule" "backend_to_database" {
  security_group_id = aws_security_group.backend.id

  description              = "Outbound to database"
  from_port                = 5432
  to_port                  = 5432
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.database.id

  tags = {
    Name = "backend-to-database"
  }
}

# Backend to Redis
resource "aws_vpc_security_group_egress_rule" "backend_to_redis" {
  security_group_id = aws_security_group.backend.id

  description              = "Outbound to Redis"
  from_port                = 6379
  to_port                  = 6379
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.redis.id

  tags = {
    Name = "backend-to-redis"
  }
}

# Backend outbound to internet (NAT)
resource "aws_vpc_security_group_egress_rule" "backend_outbound" {
  security_group_id = aws_security_group.backend.id

  description = "Outbound traffic from backend"
  from_port   = 0
  to_port     = 65535
  ip_protocol = "-1"
  cidr_ipv4   = "0.0.0.0/0"

  tags = {
    Name = "backend-outbound"
  }
}

# ==========================================
# Database Security Group
# ==========================================

resource "aws_security_group" "database" {
  name        = "${var.project_name}-database-sg"
  description = "Security group for RDS PostgreSQL database"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-database-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Ingress from backend (PostgreSQL)
resource "aws_vpc_security_group_ingress_rule" "database_from_backend" {
  security_group_id = aws_security_group.database.id

  description              = "PostgreSQL from backend"
  from_port                = 5432
  to_port                  = 5432
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.backend.id

  tags = {
    Name = "database-from-backend"
  }
}

# Ingress from Bastion (PostgreSQL)
resource "aws_vpc_security_group_ingress_rule" "database_from_bastion" {
  security_group_id = aws_security_group.database.id

  description              = "PostgreSQL from Bastion"
  from_port                = 5432
  to_port                  = 5432
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.bastion.id

  tags = {
    Name = "database-from-bastion"
  }
}

# No outbound rules for database (most restrictive)
resource "aws_vpc_security_group_egress_rule" "database_outbound_none" {
  security_group_id = aws_security_group.database.id

  description = "No outbound traffic allowed"
  from_port   = 0
  to_port     = 65535
  ip_protocol = "-1"
  cidr_ipv4   = "127.0.0.1/32"  # Unreachable address

  tags = {
    Name = "database-no-outbound"
  }
}

# ==========================================
# Redis Security Group
# ==========================================

resource "aws_security_group" "redis" {
  name        = "${var.project_name}-redis-sg"
  description = "Security group for Redis ElastiCache"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-redis-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Ingress from backend
resource "aws_vpc_security_group_ingress_rule" "redis_from_backend" {
  security_group_id = aws_security_group.redis.id

  description              = "Redis from backend"
  from_port                = 6379
  to_port                  = 6379
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.backend.id

  tags = {
    Name = "redis-from-backend"
  }
}

# Ingress from Bastion
resource "aws_vpc_security_group_ingress_rule" "redis_from_bastion" {
  security_group_id = aws_security_group.redis.id

  description              = "Redis from Bastion"
  from_port                = 6379
  to_port                  = 6379
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.bastion.id

  tags = {
    Name = "redis-from-bastion"
  }
}

# Redis cluster communication (internal)
resource "aws_vpc_security_group_ingress_rule" "redis_internal" {
  security_group_id = aws_security_group.redis.id

  description              = "Redis cluster internal"
  from_port                = 16379
  to_port                  = 16379
  ip_protocol              = "tcp"
  referenced_security_group_id = aws_security_group.redis.id

  tags = {
    Name = "redis-internal"
  }
}

# No outbound rules for Redis
resource "aws_vpc_security_group_egress_rule" "redis_outbound_none" {
  security_group_id = aws_security_group.redis.id

  description = "No outbound traffic allowed"
  from_port   = 0
  to_port     = 65535
  ip_protocol = "-1"
  cidr_ipv4   = "127.0.0.1/32"

  tags = {
    Name = "redis-no-outbound"
  }
}

# ==========================================
# Output Security Group IDs
# ==========================================

output "bastion_security_group_id" {
  description = "ID of Bastion security group"
  value       = aws_security_group.bastion.id
}

output "frontend_security_group_id" {
  description = "ID of Frontend/ALB security group"
  value       = aws_security_group.frontend.id
}

output "backend_security_group_id" {
  description = "ID of Backend security group"
  value       = aws_security_group.backend.id
}

output "database_security_group_id" {
  description = "ID of Database security group"
  value       = aws_security_group.database.id
}

output "redis_security_group_id" {
  description = "ID of Redis security group"
  value       = aws_security_group.redis.id
}
