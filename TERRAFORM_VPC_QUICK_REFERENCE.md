# Terraform VPC Quick Reference

**Task**: T_DEV_033 - VPC Configuration for Production
**Status**: ✅ COMPLETED
**Location**: `infrastructure/terraform/vpc/`

## Quick Start

### 1. Initialize Terraform

```bash
cd infrastructure/terraform/vpc
terraform init
```

### 2. Plan Deployment

```bash
# With variables file
terraform plan -var-file=production.tfvars

# Or inline
terraform plan \
  -var="environment=production" \
  -var="bastion_allowed_cidr=203.0.113.0/24"
```

### 3. Apply Configuration

```bash
terraform apply -var-file=production.tfvars
```

### 4. Get Outputs

```bash
# VPC ID
terraform output vpc_id

# All subnet IDs
terraform output public_subnet_ids
terraform output private_app_subnet_ids
terraform output private_db_subnet_ids

# NAT Gateway IPs
terraform output nat_gateway_public_ips

# Security group IDs
terraform output frontend_security_group_id
terraform output backend_security_group_id
terraform output database_security_group_id
```

---

## Variable Reference

### Required Variables

```hcl
variable "environment" {
  type        = string
  description = "Environment name (dev, staging, production)"
}
```

### Optional Variables (with defaults)

```hcl
variable "project_name" {
  default = "thebot"
}

variable "aws_region" {
  default = "us-east-1"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "availability_zones_count" {
  default = 3
}

variable "bastion_allowed_cidr" {
  default = "0.0.0.0/0"  # Restrict in production!
}

variable "flow_logs_retention_days" {
  default = 30
}
```

---

## Resources Created

### Network Resources

| Resource | Count | Details |
|----------|-------|---------|
| VPC | 1 | 10.0.0.0/16 with DNS enabled |
| Internet Gateway | 1 | For public subnet internet access |
| Public Subnets | 3 | 10.0.1-3.0/24 (one per AZ) |
| App Private Subnets | 3 | 10.0.11-13.0/24 (one per AZ) |
| DB Private Subnets | 3 | 10.0.21-23.0/24 (one per AZ) |
| Elastic IPs | 3 | For NAT Gateways |
| NAT Gateways | 3 | One per AZ in public subnets |
| Route Tables | 5 | Public (1) + App private (3) + DB private (1) |

### Security Resources

| Resource | Count | Details |
|----------|-------|---------|
| Security Groups | 6 | Bastion, Frontend, Backend, Database, Redis, Endpoints |
| Network ACLs | 3 | Public, App-Private, DB-Private |
| VPC Endpoints | 10 | S3, DynamoDB, ECR, CloudWatch, RDS, Secrets, SSM, EC2, SQS, SNS |
| Endpoint SG | 1 | For interface endpoints |

### Monitoring Resources

| Resource | Details |
|----------|---------|
| VPC Flow Logs | CloudWatch Logs destination |
| CloudWatch Log Group | /aws/vpc/flowlogs/thebot |
| IAM Role | For Flow Logs |
| IAM Policy | CloudWatch Logs permissions |

---

## File Structure

### `main.tf` (281 lines)
- VPC creation
- Internet Gateway
- Public subnets (3)
- Private app subnets (3)
- Private DB subnets (3)
- Elastic IPs (3)
- NAT Gateways (3)
- Route tables (5)
- VPC Flow Logs configuration

### `variables.tf` (133 lines)
- Input variable definitions
- Default values
- Validation rules
- Documentation for each variable

### `outputs.tf` (180 lines)
- VPC ID and CIDR
- Subnet IDs and CIDRs
- NAT Gateway IDs and EIPs
- Route table IDs
- Flow logs information
- Availability zones
- Summary outputs

### `security-groups.tf` (395 lines)
- **Bastion SG**: SSH access for administration
- **Frontend SG**: ALB for public traffic
- **Backend SG**: ECS/EC2 application tier
- **Database SG**: RDS PostgreSQL
- **Redis SG**: ElastiCache Redis
- All ingress/egress rules with references

### `nacl.tf` (268 lines)
- **Public NACL**: HTTP(80), HTTPS(443), SSH(22), Ephemeral, DNS
- **App NACL**: Port 8000 from ALB, SSH from Bastion, Ephemeral
- **DB NACL**: PostgreSQL (5432) only, DNS and ephemeral outbound

### `endpoints.tf` (369 lines)
- **S3 Gateway**: File storage
- **DynamoDB Gateway**: NoSQL database
- **ECR API**: Docker registry API
- **ECR DKR**: Docker registry
- **CloudWatch Logs**: Application logging
- **CloudWatch Monitoring**: Metrics
- **RDS**: Database management
- **Secrets Manager**: Secret storage
- **Systems Manager**: Session management
- **EC2**: EC2 API access
- **SQS**: Message queue
- **SNS**: Notifications

---

## Security Groups Details

### Bastion (Jump Host)

```
Inbound:
  - SSH (22) from: bastion_allowed_cidr

Outbound:
  - All (0.0.0.0/0)
```

### Frontend (ALB)

```
Inbound:
  - HTTP (80) from: 0.0.0.0/0
  - HTTPS (443) from: 0.0.0.0/0

Outbound:
  - 8000 (TCP) to: Backend SG
  - All (0.0.0.0/0) for DNS
```

### Backend (ECS/EC2)

```
Inbound:
  - 8000 (TCP) from: Frontend SG
  - SSH (22) from: Bastion SG
  - 6379 (TCP) from: Redis SG

Outbound:
  - 5432 (TCP) to: Database SG
  - 6379 (TCP) to: Redis SG
  - All (0.0.0.0/0) via NAT
```

### Database (RDS)

```
Inbound:
  - 5432 (TCP) from: Backend SG
  - 5432 (TCP) from: Bastion SG

Outbound:
  - None (127.0.0.1/32 - unreachable)
```

### Redis (ElastiCache)

```
Inbound:
  - 6379 (TCP) from: Backend SG
  - 6379 (TCP) from: Bastion SG
  - 16379 (TCP) from: Redis SG

Outbound:
  - None (127.0.0.1/32 - unreachable)
```

---

## Network ACL Rules

### Public Subnet

| Rule | Direction | Protocol | Port | Source | Action |
|------|-----------|----------|------|--------|--------|
| 100 | In | TCP | 80 | 0.0.0.0/0 | Allow |
| 110 | In | TCP | 443 | 0.0.0.0/0 | Allow |
| 120 | In | TCP | 22 | var.bastion_allowed_cidr | Allow |
| 130 | In | TCP | 1024-65535 | 0.0.0.0/0 | Allow |
| 140 | In | UDP | 53 | 0.0.0.0/0 | Allow |
| 100 | Out | All | All | 0.0.0.0/0 | Allow |

### Private App Subnet

| Rule | Direction | Protocol | Port | Source | Action |
|------|-----------|----------|------|--------|--------|
| 100 | In | TCP | 8000 | 10.0.0.0/16 | Allow |
| 110 | In | TCP | 22 | 10.0.0.0/16 | Allow |
| 120 | In | TCP | 1024-65535 | 0.0.0.0/0 | Allow |
| 100 | Out | All | All | 0.0.0.0/0 | Allow |

### Private DB Subnet

| Rule | Direction | Protocol | Port | Source | Action |
|------|-----------|----------|------|--------|--------|
| 100 | In | TCP | 5432 | 10.0.11.0/24 | Allow |
| 110 | In | TCP | 5432 | 10.0.12.0/24 | Allow |
| 120 | In | TCP | 5432 | 10.0.13.0/24 | Allow |
| 130 | In | TCP | 5432 | 10.0.0.0/16 | Allow |
| 140 | In | TCP | 1024-65535 | 0.0.0.0/0 | Allow |
| 100 | Out | UDP | 53 | 0.0.0.0/0 | Allow |
| 110 | Out | TCP | 1024-65535 | 0.0.0.0/0 | Allow |

---

## CIDR Allocation

```
VPC: 10.0.0.0/16 (65,536 IPs)
├── Public Subnets: 10.0.1.0/24 - 10.0.3.0/24 (762 IPs)
├── App Subnets: 10.0.11.0/24 - 10.0.13.0/24 (762 IPs)
├── DB Subnets: 10.0.21.0/24 - 10.0.23.0/24 (762 IPs)
└── Reserved: 10.0.0.0/24, 10.0.4-10.0/24, 10.0.14-20.0/24, 10.0.24-255.0/24
```

---

## VPC Endpoints

### Gateway Endpoints (Free)

- **S3**: com.amazonaws.REGION.s3
- **DynamoDB**: com.amazonaws.REGION.dynamodb

### Interface Endpoints ($7.20/month each)

- **ECR API**: com.amazonaws.REGION.ecr.api
- **ECR DKR**: com.amazonaws.REGION.ecr.dkr
- **CloudWatch Logs**: com.amazonaws.REGION.logs
- **CloudWatch Monitoring**: com.amazonaws.REGION.monitoring
- **RDS**: com.amazonaws.REGION.rds
- **Secrets Manager**: com.amazonaws.REGION.secretsmanager
- **Systems Manager**: com.amazonaws.REGION.ssm
- **EC2**: com.amazonaws.REGION.ec2
- **SQS**: com.amazonaws.REGION.sqs
- **SNS**: com.amazonaws.REGION.sns

---

## Flow Logs Configuration

```
Log Group: /aws/vpc/flowlogs/thebot
Retention: 30 days
Traffic Type: ALL (accepted + rejected)
Format: Version 2
IAM Role: thebot-flow-logs-role
```

---

## Common Commands

### Get Information

```bash
# VPC ID
terraform output vpc_id

# All outputs
terraform output

# Specific subnet
terraform output private_db_subnet_ids

# NAT Gateway IPs
terraform output nat_gateway_public_ips
```

### Modify Configuration

```bash
# Update variables
terraform apply -var="flow_logs_retention_days=60"

# Change VPC CIDR (creates new VPC!)
terraform apply -var="vpc_cidr=10.1.0.0/16"

# Restrict Bastion access
terraform apply -var="bastion_allowed_cidr=203.0.113.0/24"
```

### Destroy (Use with caution!)

```bash
# Destroy entire VPC and all resources
terraform destroy -var-file=production.tfvars
```

---

## Troubleshooting

### Error: "resource not found"

**Cause**: Resource was deleted outside Terraform
**Fix**: Recreate with `terraform apply`

### Error: "InvalidParameterValue"

**Cause**: Invalid CIDR block or parameter
**Fix**: Check variable values match AWS requirements

### VPC Endpoint not working

**Cause**: Security group blocking traffic
**Fix**: Verify endpoint SG allows 443 from source SGs

### NAT Gateway showing errors

**Cause**: May be over capacity
**Fix**: Check CloudWatch metrics or increase capacity

---

## Production Checklist

- [ ] Set environment variable: `environment=production`
- [ ] Configure bastion_allowed_cidr with actual IP range
- [ ] Review all SG rules before applying
- [ ] Backup current infrastructure (if migrating)
- [ ] Plan for 30-60 minute deployment window
- [ ] Test with `terraform plan` first
- [ ] Have rollback procedure ready
- [ ] Verify all endpoints after deployment
- [ ] Enable CloudWatch alarms for NAT
- [ ] Document any custom changes

---

## Cost Estimation

**Monthly Cost** (approximate for us-east-1):

```
NAT Gateways (3 @ $32)             $96.00
NAT Data Transfer (100 GB)          $4.50
Interface Endpoints (10 @ $7.20)   $72.00
Data Transfer (10 GB)               $0.10
─────────────────────────────────────────
Total                             $172.60
```

---

## References

- [Terraform AWS VPC](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc)
- [AWS VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Security.html)
- [Security Groups Guide](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html)
- [Network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)
- [VPC Endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints.html)

---

**Last Updated**: December 27, 2025
**Status**: Production Ready
