# THE_BOT Platform - IAM Outputs

# ==========================================
# Role Outputs
# ==========================================

output "developer_role_arn" {
  description = "ARN of the developer IAM role"
  value       = aws_iam_role.developer.arn
}

output "developer_role_name" {
  description = "Name of the developer IAM role"
  value       = aws_iam_role.developer.name
}

output "devops_role_arn" {
  description = "ARN of the DevOps IAM role"
  value       = aws_iam_role.devops.arn
}

output "devops_role_name" {
  description = "Name of the DevOps IAM role"
  value       = aws_iam_role.devops.name
}

output "admin_role_arn" {
  description = "ARN of the admin IAM role"
  value       = aws_iam_role.admin.arn
}

output "admin_role_name" {
  description = "Name of the admin IAM role"
  value       = aws_iam_role.admin.name
}

output "readonly_role_arn" {
  description = "ARN of the read-only IAM role"
  value       = aws_iam_role.readonly.arn
}

output "readonly_role_name" {
  description = "Name of the read-only IAM role"
  value       = aws_iam_role.readonly.name
}

output "cicd_role_arn" {
  description = "ARN of the CI/CD service account role"
  value       = aws_iam_role.cicd_service.arn
}

output "cicd_role_name" {
  description = "Name of the CI/CD service account role"
  value       = aws_iam_role.cicd_service.name
}

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_execution_role_name" {
  description = "Name of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution_role.name
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task_role.arn
}

output "ecs_task_role_name" {
  description = "Name of the ECS task role"
  value       = aws_iam_role.ecs_task_role.name
}

# ==========================================
# Permission Boundary Outputs
# ==========================================

output "pb_developer_arn" {
  description = "ARN of the developer permission boundary policy"
  value       = aws_iam_policy.permission_boundary_developer.arn
}

output "pb_devops_arn" {
  description = "ARN of the DevOps permission boundary policy"
  value       = aws_iam_policy.permission_boundary_devops.arn
}

output "pb_admin_arn" {
  description = "ARN of the admin permission boundary policy"
  value       = aws_iam_policy.permission_boundary_admin.arn
}

output "pb_readonly_arn" {
  description = "ARN of the read-only permission boundary policy"
  value       = aws_iam_policy.permission_boundary_readonly.arn
}

# ==========================================
# Role Assumption Commands
# ==========================================

output "assume_developer_role_command" {
  description = "AWS CLI command to assume developer role"
  value       = "aws sts assume-role --role-arn ${aws_iam_role.developer.arn} --role-session-name dev-session --duration-seconds 3600"
}

output "assume_devops_role_command" {
  description = "AWS CLI command to assume DevOps role"
  value       = "aws sts assume-role --role-arn ${aws_iam_role.devops.arn} --role-session-name devops-session --duration-seconds 3600"
}

output "assume_admin_role_command" {
  description = "AWS CLI command to assume admin role (requires MFA)"
  value       = "aws sts assume-role --role-arn ${aws_iam_role.admin.arn} --role-session-name admin-session --duration-seconds 900 --serial-number arn:aws:iam::ACCOUNT_ID:mfa/MFA_DEVICE_NAME --token-code MFA_TOKEN"
}

output "assume_readonly_role_command" {
  description = "AWS CLI command to assume read-only role"
  value       = "aws sts assume-role --role-arn ${aws_iam_role.readonly.arn} --role-session-name readonly-session --duration-seconds 3600"
}

# ==========================================
# Summary
# ==========================================

output "iam_summary" {
  description = "Summary of IAM roles created"
  value = {
    developer         = aws_iam_role.developer.arn
    devops            = aws_iam_role.devops.arn
    admin             = aws_iam_role.admin.arn
    readonly          = aws_iam_role.readonly.arn
    cicd              = aws_iam_role.cicd_service.arn
    ecs_task_exec     = aws_iam_role.ecs_task_execution_role.arn
    ecs_task_app      = aws_iam_role.ecs_task_role.arn
    environment       = var.environment
    aws_region        = data.aws_region.current.name
    aws_account_id    = data.aws_caller_identity.current.account_id
  }
}
