#!/usr/bin/env python3
"""
THE_BOT Platform - IAM Policy Validator

Validates IAM policies against security best practices and compliance requirements.
Checks for common mistakes, vulnerabilities, and suggests improvements.

Usage:
    python3 iam-validator.py --validate-policies
    python3 iam-validator.py --check-principals
    python3 iam-validator.py --validate-boundaries
"""

import json
import sys
import argparse
from typing import Dict, List, Tuple, Set
from datetime import datetime

try:
    import boto3
except ImportError:
    print("ERROR: boto3 not installed. Install with: pip install boto3")
    sys.exit(1)


class PolicyValidator:
    """Validates IAM policies against security best practices"""

    # Dangerous actions that should trigger alerts
    DANGEROUS_ACTIONS = {
        'iam:CreateUser': 'Critical',
        'iam:CreateAccessKey': 'Critical',
        'iam:CreateLoginProfile': 'Critical',
        'iam:AttachUserPolicy': 'Critical',
        'iam:PutUserPolicy': 'Critical',
        'iam:UpdateAssumeRolePolicy': 'Critical',
        'iam:PassRole': 'High',
        'ec2:TerminateInstances': 'High',
        'ec2:StopInstances': 'Medium',
        'rds:DeleteDBInstance': 'Critical',
        's3:DeleteBucket': 'Critical',
        's3:PutBucketPolicy': 'High',
        'kms:DisableKey': 'Critical',
        'kms:ScheduleKeyDeletion': 'Critical',
        'organizations:*': 'Critical',
        'account:*': 'Critical'
    }

    def __init__(self):
        """Initialize AWS clients"""
        self.iam = boto3.client('iam')
        self.findings = []

    def print_finding(self, severity: str, title: str, details: str = "", location: str = ""):
        """Print validation finding"""
        colors = {
            'Critical': '\033[91m',
            'High': '\033[93m',
            'Medium': '\033[94m',
            'Low': '\033[92m',
            'Info': '\033[0m'
        }
        reset = '\033[0m'

        color = colors.get(severity, '\033[0m')
        print(f"{color}[{severity:8s}]{reset} {title}")
        if location:
            print(f"           Location: {location}")
        if details:
            print(f"           {details}\n")

        self.findings.append({
            'severity': severity,
            'title': title,
            'details': details,
            'location': location
        })

    def validate_all_policies(self):
        """Validate all IAM policies"""
        print("\n" + "=" * 80)
        print("  THE_BOT IAM Policy Validation")
        print("=" * 80 + "\n")

        # Validate user policies
        self._validate_user_policies()

        # Validate role policies
        self._validate_role_policies()

        # Validate managed policies
        self._validate_managed_policies()

        self._print_summary()

    def _validate_user_policies(self):
        """Validate all user inline and attached policies"""
        print("Validating User Policies...\n")

        try:
            users = self.iam.list_users()['Users']

            for user in users:
                user_name = user['UserName']

                # Check inline policies
                inline_policies = self.iam.list_user_policies(UserName=user_name)['PolicyNames']
                for policy_name in inline_policies:
                    policy_doc = self.iam.get_user_policy(
                        UserName=user_name,
                        PolicyName=policy_name
                    )['UserPolicyDocument']

                    self._validate_policy_document(
                        policy_doc,
                        f"User: {user_name}, Policy: {policy_name}"
                    )

                # Check attached policies
                attached = self.iam.list_attached_user_policies(UserName=user_name)['AttachedPolicies']
                for policy in attached:
                    self._validate_attached_policy(policy['PolicyArn'], f"User: {user_name}")

        except Exception as e:
            self.print_finding('High', "Error validating user policies", str(e))

    def _validate_role_policies(self):
        """Validate all role inline and attached policies"""
        print("Validating Role Policies...\n")

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']

            for role in roles:
                role_name = role['RoleName']

                # Check trust relationship
                trust_policy = role['AssumeRolePolicyDocument']
                self._validate_trust_relationship(trust_policy, role_name)

                # Check inline policies
                inline_policies = self.iam.list_role_policies(RoleName=role_name)['PolicyNames']
                for policy_name in inline_policies:
                    policy_doc = self.iam.get_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name
                    )['RolePolicyDocument']

                    self._validate_policy_document(
                        policy_doc,
                        f"Role: {role_name}, Policy: {policy_name}"
                    )

                # Check attached policies
                attached = self.iam.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']
                for policy in attached:
                    self._validate_attached_policy(policy['PolicyArn'], f"Role: {role_name}")

        except Exception as e:
            self.print_finding('High', "Error validating role policies", str(e))

    def _validate_managed_policies(self):
        """Validate custom managed policies"""
        print("Validating Managed Policies...\n")

        try:
            policies = self.iam.list_policies(Scope='Local')['Policies']

            for policy in policies:
                # Only check THE_BOT policies
                if 'thebot' not in policy['PolicyName'].lower():
                    continue

                # Get policy version
                version = self.iam.get_policy(PolicyArn=policy['Arn'])['Policy']
                default_version_id = version['DefaultVersionId']

                policy_doc = self.iam.get_policy_version(
                    PolicyArn=policy['Arn'],
                    VersionId=default_version_id
                )['PolicyVersion']['Document']

                self._validate_policy_document(
                    policy_doc,
                    f"Managed Policy: {policy['PolicyName']}"
                )

        except Exception as e:
            self.print_finding('High', "Error validating managed policies", str(e))

    def _validate_policy_document(self, policy_doc: Dict, location: str):
        """Validate a single policy document"""
        version = policy_doc.get('Version', '2012-10-17')

        # Check version
        if version != '2012-10-17':
            self.print_finding('Medium', "Outdated policy version",
                              f"Current: {version}, Should be: 2012-10-17",
                              location)

        # Check statements
        statements = policy_doc.get('Statement', [])
        for idx, statement in enumerate(statements):
            self._validate_statement(statement, f"{location} [Statement {idx}]")

    def _validate_statement(self, statement: Dict, location: str):
        """Validate a single IAM statement"""
        effect = statement.get('Effect')
        actions = statement.get('Action', [])
        resources = statement.get('Resource', [])
        conditions = statement.get('Condition', {})

        if not isinstance(actions, list):
            actions = [actions]

        if not isinstance(resources, list):
            resources = [resources]

        # Check for wildcard principal (only for Trust policies)
        principal = statement.get('Principal')
        if principal == "*":
            self.print_finding('Critical', "Wildcard principal in statement",
                              "Anyone can assume this role",
                              location)

        # Check for dangerous actions with wildcard resources
        for action in actions:
            if self._is_dangerous_action(action):
                severity = self.DANGEROUS_ACTIONS.get(action, 'Medium')

                if resources == ["*"] or "*" in resources:
                    self.print_finding(severity,
                                     f"Dangerous action with wildcard resource: {action}",
                                     "This grants very broad permissions",
                                     location)
                elif len(resources) == 0:
                    self.print_finding('High', f"Dangerous action with no resources: {action}",
                                     "Resources should be explicitly specified",
                                     location)

        # Check for wildcard actions
        for action in actions:
            if action == "*":
                self.print_finding('Critical', "Wildcard action (*)",
                                 "This grants full AWS API access",
                                 location)

            elif action.endswith("*"):
                # Allow service:* patterns for specific services
                service = action.split(":")[0] if ":" in action else ""
                if service in ['ec2', 'iam', 'rds', 's3', 'kms', 'dynamodb']:
                    severity = 'High' if service in ['iam', 'kms'] else 'Medium'
                    self.print_finding(severity,
                                     f"Broad service actions: {action}",
                                     "Consider limiting to specific actions",
                                     location)

        # Check for missing conditions on powerful actions
        for action in actions:
            if action in ['iam:AssumeRole', 'sts:AssumeRole']:
                if not conditions:
                    self.print_finding('Medium', "AssumeRole without conditions",
                                     "Consider adding IP/MFA/ExternalId conditions",
                                     location)

        # Check for missing NotActions with Allow
        if statement.get('Effect') == 'Allow' and 'NotAction' in statement:
            self.print_finding('High', "Allow effect with NotAction",
                             "NotAction with Allow is dangerous - use explicit actions instead",
                             location)

        # Check for resource specification
        if statement.get('Effect') == 'Allow':
            if not resources and 'NotResource' not in statement:
                # Some services don't require resources (e.g., iam:ListUsers)
                services = set()
                for action in actions:
                    if ':' in action:
                        services.add(action.split(':')[0])

                if any(service in ['iam', 'sts', 'organizations'] for service in services):
                    # These services often use * for resources
                    pass
                else:
                    self.print_finding('Medium', "Missing Resource specification",
                                     "Should explicitly specify which resources the policy applies to",
                                     location)

    def _validate_trust_relationship(self, trust_policy: Dict, role_name: str):
        """Validate role trust relationship"""
        statements = trust_policy.get('Statement', [])

        for idx, statement in enumerate(statements):
            principal = statement.get('Principal')

            # Check for wildcard principal
            if principal == "*":
                self.print_finding('Critical',
                                 f"Role {role_name} has wildcard principal",
                                 "Anyone in any AWS account can assume this role",
                                 f"Trust Policy Statement {idx}")
                return

            # Check for broad principal
            if isinstance(principal, dict):
                aws_principals = principal.get('AWS', [])
                if isinstance(aws_principals, str):
                    aws_principals = [aws_principals]

                for principal_arn in aws_principals:
                    if principal_arn == "*":
                        self.print_finding('Critical',
                                         f"Role {role_name} allows all AWS principals",
                                         "Anyone in any AWS account can assume this role",
                                         f"Trust Policy Statement {idx}")

                    elif ":root" in principal_arn and not principal_arn.startswith("arn:aws:iam::"):
                        self.print_finding('High',
                                         f"Role {role_name} allows cross-account root access",
                                         f"Principal: {principal_arn}",
                                         f"Trust Policy Statement {idx}")

            # Check for external ID
            conditions = statement.get('Condition', {})
            has_external_id = 'StringEquals' in conditions and \
                             'sts:ExternalId' in conditions['StringEquals']

            # For sensitive roles, require external ID
            if 'admin' in role_name.lower() or 'prod' in role_name.lower():
                if not has_external_id:
                    self.print_finding('Medium',
                                     f"Role {role_name} lacks external ID",
                                     "External ID provides additional security for cross-account access",
                                     f"Trust Policy Statement {idx}")

    def _validate_attached_policy(self, policy_arn: str, location: str):
        """Validate an attached managed policy"""
        try:
            version_id = self.iam.get_policy(PolicyArn=policy_arn)['Policy']['DefaultVersionId']
            policy_doc = self.iam.get_policy_version(
                PolicyArn=policy_arn,
                VersionId=version_id
            )['PolicyVersion']['Document']

            self._validate_policy_document(policy_doc, f"{location}, Policy: {policy_arn}")

        except Exception as e:
            print(f"Error validating policy {policy_arn}: {e}")

    def _is_dangerous_action(self, action: str) -> bool:
        """Check if action is potentially dangerous"""
        # Check exact match
        if action in self.DANGEROUS_ACTIONS:
            return True

        # Check with wildcards
        for dangerous in self.DANGEROUS_ACTIONS.keys():
            if dangerous.endswith("*"):
                if action.startswith(dangerous[:-1]):
                    return True

        return False

    def validate_permission_boundaries(self):
        """Validate permission boundary configurations"""
        print("\n" + "=" * 80)
        print("  Permission Boundary Validation")
        print("=" * 80 + "\n")

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']

            roles_with_boundary = []
            roles_without_boundary = []

            for role in roles:
                if 'thebot' not in role['RoleName'].lower():
                    continue

                if role.get('PermissionsBoundaryArn'):
                    roles_with_boundary.append(role['RoleName'])
                    print(f"✓ {role['RoleName']} has boundary")
                else:
                    roles_without_boundary.append(role['RoleName'])
                    self.print_finding('High',
                                     f"Role {role['RoleName']} missing permission boundary",
                                     "All roles should have permission boundaries for security")

            print(f"\nSummary:")
            print(f"  Roles with boundary:    {len(roles_with_boundary)}")
            print(f"  Roles without boundary: {len(roles_without_boundary)}")

        except Exception as e:
            self.print_finding('High', "Error validating permission boundaries", str(e))

    def validate_principals(self):
        """Validate IAM principals and their configuration"""
        print("\n" + "=" * 80)
        print("  Principal Validation")
        print("=" * 80 + "\n")

        try:
            users = self.iam.list_users()['Users']
            roles = self.iam.list_roles(MaxItems=1000)['Roles']

            # Check users
            print("Checking Users:")
            for user in users:
                user_name = user['UserName']

                # Check for MFA
                mfa_devices = self.iam.list_mfa_devices(UserName=user_name)['MFADevices']
                if not mfa_devices and 'service' not in user_name.lower():
                    if user_name != 'root':
                        self.print_finding('Medium',
                                         f"User {user_name} lacks MFA",
                                         "Interactive users should have MFA enabled")

                # Check access key age
                access_keys = self.iam.list_access_keys(UserName=user_name)['AccessKeyMetadata']
                for key in access_keys:
                    age_days = (datetime.utcnow() - key['CreateDate'].replace(tzinfo=None)).days
                    if age_days > 90:
                        self.print_finding('Medium',
                                         f"User {user_name} access key {key['AccessKeyId'][:10]}... is {age_days} days old",
                                         "Access keys should be rotated every 90 days")

            # Check roles
            print("\nChecking Roles:")
            thebot_roles = [r for r in roles if 'thebot' in r['RoleName'].lower()]
            for role in thebot_roles:
                print(f"  ✓ {role['RoleName']}")

        except Exception as e:
            self.print_finding('High', "Error validating principals", str(e))

    def _print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 80)
        print("  Validation Summary")
        print("=" * 80 + "\n")

        # Count by severity
        by_severity = {}
        for finding in self.findings:
            severity = finding['severity']
            by_severity[severity] = by_severity.get(severity, 0) + 1

        total = len(self.findings)
        critical = by_severity.get('Critical', 0)
        high = by_severity.get('High', 0)
        medium = by_severity.get('Medium', 0)
        low = by_severity.get('Low', 0)

        print(f"Total Findings: {total}\n")
        print(f"  Critical: {critical}")
        print(f"  High:     {high}")
        print(f"  Medium:   {medium}")
        print(f"  Low:      {low}")

        if critical > 0:
            print(f"\n⚠️  CRITICAL ISSUES FOUND - IMMEDIATE ACTION REQUIRED")
        elif high > 0:
            print(f"\n⚠️  High-priority issues found - review recommended")
        else:
            print(f"\n✓ Validation complete")

    def export_findings(self, filename: str = None):
        """Export findings to JSON"""
        if not filename:
            filename = f"iam-validation-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        report = {
            'timestamp': datetime.now().isoformat(),
            'findings': self.findings,
            'summary': {
                'total': len(self.findings),
                'critical': sum(1 for f in self.findings if f['severity'] == 'Critical'),
                'high': sum(1 for f in self.findings if f['severity'] == 'High'),
                'medium': sum(1 for f in self.findings if f['severity'] == 'Medium'),
                'low': sum(1 for f in self.findings if f['severity'] == 'Low')
            }
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n✓ Findings exported to {filename}")


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='THE_BOT IAM Policy Validator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 iam-validator.py --validate-policies
  python3 iam-validator.py --validate-boundaries
  python3 iam-validator.py --check-principals
  python3 iam-validator.py --validate-policies --export report.json
        """
    )

    parser.add_argument('--validate-policies', action='store_true',
                       help='Validate all IAM policies')
    parser.add_argument('--validate-boundaries', action='store_true',
                       help='Validate permission boundaries')
    parser.add_argument('--check-principals', action='store_true',
                       help='Check IAM principals configuration')
    parser.add_argument('--export', type=str,
                       help='Export findings to JSON file')

    args = parser.parse_args()

    validator = PolicyValidator()

    try:
        if args.validate_policies:
            validator.validate_all_policies()
        elif args.validate_boundaries:
            validator.validate_permission_boundaries()
        elif args.check_principals:
            validator.validate_principals()
        else:
            # Run all validations by default
            validator.validate_all_policies()
            validator.validate_permission_boundaries()
            validator.validate_principals()

        if args.export:
            validator.export_findings(args.export)

        return 0 if not validator.findings else 1

    except KeyboardInterrupt:
        print("\n\nValidation cancelled by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
