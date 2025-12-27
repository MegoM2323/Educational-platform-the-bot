# THE_BOT Platform - VPC Outputs

# ==========================================
# VPC Information
# ==========================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

# ==========================================
# Public Subnets
# ==========================================

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "public_subnet_cidrs" {
  description = "CIDR blocks of public subnets"
  value       = aws_subnet.public[*].cidr_block
}

output "public_subnets_by_az" {
  description = "Public subnets mapped by availability zone"
  value = {
    for i, subnet in aws_subnet.public :
    data.aws_availability_zones.available.names[i] => {
      subnet_id = subnet.id
      cidr_block = subnet.cidr_block
    }
  }
}

# ==========================================
# Private Application Subnets
# ==========================================

output "private_app_subnet_ids" {
  description = "IDs of private application subnets"
  value       = aws_subnet.private_app[*].id
}

output "private_app_subnet_cidrs" {
  description = "CIDR blocks of private application subnets"
  value       = aws_subnet.private_app[*].cidr_block
}

output "private_app_subnets_by_az" {
  description = "Private application subnets mapped by availability zone"
  value = {
    for i, subnet in aws_subnet.private_app :
    data.aws_availability_zones.available.names[i] => {
      subnet_id = subnet.id
      cidr_block = subnet.cidr_block
    }
  }
}

# ==========================================
# Private Database Subnets
# ==========================================

output "private_db_subnet_ids" {
  description = "IDs of private database subnets"
  value       = aws_subnet.private_db[*].id
}

output "private_db_subnet_cidrs" {
  description = "CIDR blocks of private database subnets"
  value       = aws_subnet.private_db[*].cidr_block
}

output "private_db_subnets_by_az" {
  description = "Private database subnets mapped by availability zone"
  value = {
    for i, subnet in aws_subnet.private_db :
    data.aws_availability_zones.available.names[i] => {
      subnet_id = subnet.id
      cidr_block = subnet.cidr_block
    }
  }
}

# ==========================================
# NAT Gateways
# ==========================================

output "nat_gateway_ids" {
  description = "IDs of NAT Gateways"
  value       = aws_nat_gateway.main[*].id
}

output "nat_gateway_public_ips" {
  description = "Public IP addresses of NAT Gateways"
  value       = aws_eip.nat[*].public_ip
}

output "nat_gateways_by_az" {
  description = "NAT Gateways mapped by availability zone"
  value = {
    for i, nat in aws_nat_gateway.main :
    data.aws_availability_zones.available.names[i] => {
      nat_gateway_id = nat.id
      public_ip      = aws_eip.nat[i].public_ip
      subnet_id      = nat.subnet_id
    }
  }
}

# ==========================================
# Route Tables
# ==========================================

output "public_route_table_id" {
  description = "ID of public route table"
  value       = aws_route_table.public.id
}

output "private_app_route_table_ids" {
  description = "IDs of private application route tables"
  value       = aws_route_table.private_app[*].id
}

output "private_db_route_table_id" {
  description = "ID of private database route table"
  value       = aws_route_table.private_db.id
}

# ==========================================
# Flow Logs
# ==========================================

output "flow_logs_group_name" {
  description = "Name of CloudWatch Logs group for VPC Flow Logs"
  value       = aws_cloudwatch_log_group.flow_logs.name
}

output "flow_logs_role_arn" {
  description = "ARN of IAM role for VPC Flow Logs"
  value       = aws_iam_role.flow_logs.arn
}

# ==========================================
# Availability Zones
# ==========================================

output "availability_zones" {
  description = "List of availability zones used"
  value       = data.aws_availability_zones.available.names
}

# ==========================================
# Summary
# ==========================================

output "vpc_summary" {
  description = "Summary of VPC configuration"
  value = {
    vpc_id                    = aws_vpc.main.id
    vpc_cidr                  = aws_vpc.main.cidr_block
    availability_zones_count  = var.availability_zones_count
    public_subnets_count      = length(aws_subnet.public)
    private_app_subnets_count = length(aws_subnet.private_app)
    private_db_subnets_count  = length(aws_subnet.private_db)
    nat_gateways_count        = length(aws_nat_gateway.main)
  }
}
