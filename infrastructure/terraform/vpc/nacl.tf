# THE_BOT Platform - Network ACLs (NACLs)

# ==========================================
# Public Subnet NACL
# ==========================================

resource "aws_network_acl" "public" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.public[*].id

  tags = {
    Name        = "${var.project_name}-public-nacl"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Inbound rules for public NACL

# Allow HTTP from anywhere
resource "aws_network_acl_rule" "public_in_http" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 100
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 80
  to_port        = 80
}

# Allow HTTPS from anywhere
resource "aws_network_acl_rule" "public_in_https" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 110
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 443
  to_port        = 443
}

# Allow SSH from limited IPs (for Bastion)
resource "aws_network_acl_rule" "public_in_ssh" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 120
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.bastion_allowed_cidr
  from_port      = 22
  to_port        = 22
}

# Allow ephemeral ports (for return traffic)
resource "aws_network_acl_rule" "public_in_ephemeral" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 130
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# Allow UDP for DNS and NTP
resource "aws_network_acl_rule" "public_in_dns" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 140
  protocol       = "udp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 53
  to_port        = 53
}

# Outbound rules for public NACL

# Allow all outbound traffic
resource "aws_network_acl_rule" "public_out_all" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 100
  protocol       = "-1"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 0
  to_port        = 0
  egress         = true
}

# ==========================================
# Private Application Subnet NACL
# ==========================================

resource "aws_network_acl" "private_app" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private_app[*].id

  tags = {
    Name        = "${var.project_name}-private-app-nacl"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Inbound rules for private app NACL

# Allow traffic from ALB/Public subnet
resource "aws_network_acl_rule" "private_app_in_alb" {
  network_acl_id = aws_network_acl.public.id
  rule_number    = 100
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 8000
  to_port        = 8000
}

# Allow SSH from Bastion (same VPC)
resource "aws_network_acl_rule" "private_app_in_ssh" {
  network_acl_id = aws_network_acl.private_app.id
  rule_number    = 110
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 22
  to_port        = 22
}

# Allow ephemeral return traffic
resource "aws_network_acl_rule" "private_app_in_ephemeral" {
  network_acl_id = aws_network_acl.private_app.id
  rule_number    = 120
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# Outbound rules for private app NACL

# Allow all outbound (via NAT Gateway)
resource "aws_network_acl_rule" "private_app_out_all" {
  network_acl_id = aws_network_acl.private_app.id
  rule_number    = 100
  protocol       = "-1"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 0
  to_port        = 0
  egress         = true
}

# ==========================================
# Private Database Subnet NACL
# ==========================================

resource "aws_network_acl" "private_db" {
  vpc_id     = aws_vpc.main.id
  subnet_ids = aws_subnet.private_db[*].id

  tags = {
    Name        = "${var.project_name}-private-db-nacl"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Inbound rules for private DB NACL (most restrictive)

# Allow PostgreSQL from backend tier only
resource "aws_network_acl_rule" "private_db_in_postgres_app" {
  network_acl_id = aws_network_acl.private_db.id
  rule_number    = 100
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.0.11.0/24"  # Private app AZ1
  from_port      = 5432
  to_port        = 5432
}

# Allow PostgreSQL from private app tier AZ2
resource "aws_network_acl_rule" "private_db_in_postgres_app2" {
  network_acl_id = aws_network_acl.private_db.id
  rule_number    = 110
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.0.12.0/24"  # Private app AZ2
  from_port      = 5432
  to_port        = 5432
}

# Allow PostgreSQL from private app tier AZ3
resource "aws_network_acl_rule" "private_db_in_postgres_app3" {
  network_acl_id = aws_network_acl.private_db.id
  rule_number    = 120
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "10.0.13.0/24"  # Private app AZ3
  from_port      = 5432
  to_port        = 5432
}

# Allow PostgreSQL from Bastion (for maintenance)
resource "aws_network_acl_rule" "private_db_in_postgres_bastion" {
  network_acl_id = aws_network_acl.private_db.id
  rule_number    = 130
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = var.vpc_cidr
  from_port      = 5432
  to_port        = 5432
}

# Allow ephemeral return traffic
resource "aws_network_acl_rule" "private_db_in_ephemeral" {
  network_acl_id = aws_network_acl.private_db.id
  rule_number    = 140
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# Outbound rules for private DB NACL (minimal)

# Allow outbound DNS
resource "aws_network_acl_rule" "private_db_out_dns" {
  network_acl_id = aws_network_acl.private_db.id
  rule_number    = 100
  protocol       = "udp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 53
  to_port        = 53
  egress         = true
}

# Allow outbound TCP ephemeral (for return traffic)
resource "aws_network_acl_rule" "private_db_out_ephemeral" {
  network_acl_id = aws_network_acl.private_db.id
  rule_number    = 110
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
  egress         = true
}

# ==========================================
# Output NACL Information
# ==========================================

output "public_nacl_id" {
  description = "ID of public subnet NACL"
  value       = aws_network_acl.public.id
}

output "private_app_nacl_id" {
  description = "ID of private application subnet NACL"
  value       = aws_network_acl.private_app.id
}

output "private_db_nacl_id" {
  description = "ID of private database subnet NACL"
  value       = aws_network_acl.private_db.id
}
