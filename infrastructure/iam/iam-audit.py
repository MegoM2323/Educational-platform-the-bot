#!/usr/bin/env python3
"""
THE_BOT Platform - IAM Audit and Validation Tool

Performs comprehensive security audit of IAM roles, policies, and access patterns.
Generates reports on compliance, permission violations, and recommendations.

Usage:
    python3 iam-audit.py --audit-all
    python3 iam-audit.py --check-escalation
    python3 iam-audit.py --review-access --days 30
    python3 iam-audit.py --unused-access
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import subprocess
import re

try:
    import boto3
except ImportError:
    print("ERROR: boto3 not installed. Install with: pip install boto3")
    sys.exit(1)


class IAMaudit:
    """IAM audit and compliance checker"""

    def __init__(self):
        """Initialize AWS clients"""
        self.iam = boto3.client('iam')
        self.cloudtrail = boto3.client('cloudtrail')
        self.sts = boto3.client('sts')
        self.account_id = self._get_account_id()
        self.findings = []
        self.warnings = []

    def _get_account_id(self) -> str:
        """Get current AWS account ID"""
        return self.sts.get_caller_identity()['Account']

    def print_header(self, title: str):
        """Print formatted section header"""
        print(f"\n{'=' * 80}")
        print(f"  {title}")
        print(f"{'=' * 80}\n")

    def print_finding(self, severity: str, title: str, details: str = ""):
        """Print audit finding"""
        colors = {
            'CRITICAL': '\033[91m',  # Red
            'HIGH': '\033[93m',      # Yellow
            'MEDIUM': '\033[94m',    # Blue
            'LOW': '\033[92m',       # Green
            'INFO': '\033[0m'        # Default
        }
        reset = '\033[0m'

        icon = {
            'CRITICAL': '✗',
            'HIGH': '!',
            'MEDIUM': '◆',
            'LOW': '○',
            'INFO': 'ℹ'
        }

        color = colors.get(severity, '\033[0m')
        symbol = icon.get(severity, '*')

        print(f"{color}[{severity:8s}] {symbol} {title}{reset}")
        if details:
            print(f"           {details}")

        self.findings.append({
            'severity': severity,
            'title': title,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })

    def audit_all(self):
        """Run complete IAM audit"""
        self.print_header("THE_BOT IAM Comprehensive Audit")
        print(f"Account ID: {self.account_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        self.check_password_policy()
        self.check_mfa_usage()
        self.check_role_trust_relationships()
        self.check_permission_boundaries()
        self.check_privilege_escalation()
        self.check_unused_roles()
        self.check_outdated_access_keys()
        self.check_inline_policies()
        self.check_cross_account_access()
        self.check_service_accounts()

        self.print_summary()

    def check_password_policy(self):
        """Audit password policy"""
        self.print_header("Password Policy Audit")

        try:
            policy = self.iam.get_account_password_policy()['PasswordPolicy']

            # Check requirements
            checks = [
                ('MinimumPasswordLength', 12, policy.get('MinimumPasswordLength', 0) >= 12),
                ('RequireSymbols', True, policy.get('RequireSymbols', False)),
                ('RequireNumbers', True, policy.get('RequireNumbers', False)),
                ('RequireUppercaseCharacters', True, policy.get('RequireUppercaseCharacters', False)),
                ('RequireLowercaseCharacters', True, policy.get('RequireLowercaseCharacters', False)),
                ('ExpirePasswords', True, policy.get('ExpirePasswords', False)),
                ('MaxPasswordAge', 90, policy.get('MaxPasswordAge', 999) <= 90),
                ('PasswordReusePrevention', True, policy.get('PasswordReusePrevention', False)),
                ('HardExpiry', True, policy.get('HardExpiry', False))
            ]

            for check_name, expected, result in checks:
                if result:
                    self.print_finding('INFO', f"✓ {check_name} configured correctly")
                else:
                    self.print_finding('HIGH', f"✗ {check_name} not configured",
                                      f"Expected: {expected}, Current: {policy.get(check_name)}")

        except self.iam.exceptions.NoSuchEntityException:
            self.print_finding('CRITICAL', "✗ No password policy set",
                              "AWS requires a password policy for all AWS accounts")

    def check_mfa_usage(self):
        """Audit MFA usage"""
        self.print_header("MFA Usage Audit")

        try:
            mfa_devices = self.iam.list_mfa_devices()['MFADevices']
            users = self.iam.list_users()['Users']

            users_count = len(users)
            mfa_count = len(mfa_devices)

            if mfa_count == 0:
                self.print_finding('CRITICAL', "✗ No MFA devices enabled",
                                  "All admin users should have MFA enabled")
            elif mfa_count < users_count * 0.5:
                self.print_finding('HIGH', f"✗ Low MFA adoption: {mfa_count}/{users_count}",
                                  "All users should have MFA enabled")
            else:
                self.print_finding('INFO', f"✓ MFA adoption: {mfa_count}/{users_count} users")

            # Check virtual MFA devices
            virt_mfa = self.iam.list_virtual_mfa_devices()['VirtualMFADevices']
            self.print_finding('INFO', f"Virtual MFA devices: {len(virt_mfa)}")

        except Exception as e:
            self.print_finding('HIGH', "Error checking MFA", str(e))

    def check_role_trust_relationships(self):
        """Audit role trust relationships"""
        self.print_header("Role Trust Relationship Audit")

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']
            thebot_roles = [r for r in roles if 'thebot' in r['RoleName'].lower()]

            print(f"Found {len(thebot_roles)} THE_BOT roles\n")

            for role in thebot_roles:
                role_name = role['RoleName']
                trust_policy = role['AssumeRolePolicyDocument']

                # Check for wildcard principals
                for statement in trust_policy.get('Statement', []):
                    principal = statement.get('Principal', {})

                    if principal == "*":
                        self.print_finding('CRITICAL',
                                         f"✗ {role_name} allows all principals",
                                         "This role can be assumed by anyone")
                    elif principal.get('AWS') == "*":
                        self.print_finding('HIGH',
                                         f"✗ {role_name} allows all AWS principals",
                                         "This role can be assumed by any AWS account")

                    # Check for external ID
                    conditions = statement.get('Condition', {})
                    has_external_id = 'StringEquals' in conditions and \
                                     'sts:ExternalId' in conditions['StringEquals']

                    if not has_external_id and statement.get('Effect') == 'Allow':
                        self.print_finding('MEDIUM',
                                         f"✗ {role_name} lacks external ID protection",
                                         "External ID should be required for role assumption")

                    # Check for IP restrictions on sensitive roles
                    if 'admin' in role_name.lower():
                        has_ip_restriction = 'IpAddress' in conditions
                        if not has_ip_restriction:
                            self.print_finding('MEDIUM',
                                             f"✗ {role_name} lacks IP restrictions",
                                             "Admin roles should have IP restrictions")

        except Exception as e:
            self.print_finding('HIGH', "Error checking trust relationships", str(e))

    def check_permission_boundaries(self):
        """Audit permission boundaries"""
        self.print_header("Permission Boundary Audit")

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']
            thebot_roles = [r for r in roles if 'thebot' in r['RoleName'].lower()]

            roles_with_pb = 0
            roles_without_pb = 0

            for role in thebot_roles:
                if role.get('PermissionsBoundaryArn'):
                    roles_with_pb += 1
                    print(f"✓ {role['RoleName']} has boundary")
                else:
                    roles_without_pb += 1
                    if 'readonly' not in role['RoleName'].lower():
                        self.print_finding('HIGH',
                                         f"✗ {role['RoleName']} missing permission boundary",
                                         "All roles should have permission boundaries")

            print(f"\nSummary: {roles_with_pb} with boundary, {roles_without_pb} without\n")

        except Exception as e:
            self.print_finding('HIGH', "Error checking permission boundaries", str(e))

    def check_privilege_escalation(self):
        """Check for privilege escalation vulnerabilities"""
        self.print_header("Privilege Escalation Risk Assessment")

        dangerous_actions = [
            'iam:CreateAccessKey',
            'iam:CreateUser',
            'iam:AttachUserPolicy',
            'iam:AttachGroupPolicy',
            'iam:AttachRolePolicy',
            'iam:PutUserPolicy',
            'iam:PutGroupPolicy',
            'iam:PutRolePolicy',
            'iam:CreateLoginProfile',
            'iam:UpdateAssumeRolePolicy',
            'iam:PassRole'
        ]

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']
            thebot_roles = [r for r in roles if 'thebot' in r['RoleName'].lower()]

            for role in thebot_roles:
                role_name = role['RoleName']

                # Check inline policies
                inline_policies = self.iam.list_role_policies(RoleName=role_name)['PolicyNames']
                for policy_name in inline_policies:
                    policy_doc = self.iam.get_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name
                    )['RolePolicyDocument']

                    for statement in policy_doc.get('Statement', []):
                        if statement.get('Effect') == 'Allow':
                            actions = statement.get('Action', [])
                            if isinstance(actions, str):
                                actions = [actions]

                            for dangerous_action in dangerous_actions:
                                for action in actions:
                                    if self._action_matches(action, dangerous_action):
                                        resource = statement.get('Resource', [])
                                        if resource == "*" or (isinstance(resource, list) and "*" in resource):
                                            self.print_finding('HIGH',
                                                             f"✗ {role_name} can {dangerous_action}",
                                                             "This could enable privilege escalation")

        except Exception as e:
            self.print_finding('HIGH', "Error checking privilege escalation", str(e))

    def check_unused_roles(self):
        """Check for unused IAM roles"""
        self.print_header("Unused Roles Audit")

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']
            thebot_roles = [r for r in roles if 'thebot' in r['RoleName'].lower()]

            unused_roles = []

            for role in thebot_roles:
                role_name = role['RoleName']
                max_session_duration = role.get('MaxSessionDuration', 3600)

                # Check when role was created
                created = role['CreateDate']
                days_old = (datetime.now(created.tzinfo) - created).days

                # Skip system roles created recently
                if days_old < 7:
                    continue

                # Check attached policies
                attached = self.iam.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']

                # For service accounts, check more strictly
                if 'service' in role_name.lower() or 'lambda' in role_name.lower():
                    if not attached:
                        unused_roles.append((role_name, days_old))

            if unused_roles:
                print(f"\nFound {len(unused_roles)} potentially unused roles:\n")
                for role_name, days_old in unused_roles:
                    self.print_finding('MEDIUM', f"✗ {role_name} (created {days_old} days ago)",
                                      "No policies attached - verify still needed")
            else:
                print("✓ All roles have attached policies\n")

        except Exception as e:
            self.print_finding('HIGH', "Error checking unused roles", str(e))

    def check_outdated_access_keys(self):
        """Check for old access keys"""
        self.print_header("Access Key Rotation Audit")

        try:
            users = self.iam.list_users()['Users']
            old_keys = []

            for user in users:
                user_name = user['UserName']
                access_keys = self.iam.list_access_keys(UserName=user_name)['AccessKeyMetadata']

                for key in access_keys:
                    key_age = (datetime.now(key['CreateDate'].tzinfo) - key['CreateDate']).days

                    if key_age > 90:
                        severity = 'CRITICAL' if key_age > 180 else 'HIGH'
                        old_keys.append((user_name, key['AccessKeyId'], key_age))
                        self.print_finding(severity,
                                         f"✗ {user_name} has {key_age}-day-old access key",
                                         f"Key: {key['AccessKeyId'][:10]}... - Rotate immediately")

            if not old_keys:
                print("✓ All access keys are recent (< 90 days)\n")

        except Exception as e:
            self.print_finding('HIGH', "Error checking access keys", str(e))

    def check_inline_policies(self):
        """Check for inline policies"""
        self.print_header("Inline Policy Audit")

        try:
            users = self.iam.list_users()['Users']
            inline_policy_count = 0

            for user in users:
                user_name = user['UserName']
                inline_policies = self.iam.list_user_policies(UserName=user_name)['PolicyNames']

                if inline_policies:
                    inline_policy_count += len(inline_policies)
                    for policy_name in inline_policies:
                        self.print_finding('LOW',
                                         f"✗ {user_name} has inline policy: {policy_name}",
                                         "Consider using managed policies instead")

            roles = self.iam.list_roles()['Roles']
            for role in roles:
                if 'thebot' in role['RoleName'].lower():
                    inline_policies = self.iam.list_role_policies(RoleName=role['RoleName'])['PolicyNames']
                    if inline_policies:
                        inline_policy_count += len(inline_policies)

            print(f"\nTotal inline policies: {inline_policy_count}")
            if inline_policy_count > 0:
                print("→ Consider consolidating with managed policies\n")

        except Exception as e:
            self.print_finding('HIGH', "Error checking inline policies", str(e))

    def check_cross_account_access(self):
        """Check for cross-account access"""
        self.print_header("Cross-Account Access Audit")

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']
            cross_account_roles = []

            for role in roles:
                trust_policy = role['AssumeRolePolicyDocument']

                for statement in trust_policy.get('Statement', []):
                    principal = statement.get('Principal', {})
                    if isinstance(principal, dict):
                        aws_principals = principal.get('AWS', [])
                        if isinstance(aws_principals, str):
                            aws_principals = [aws_principals]

                        for principal_arn in aws_principals:
                            if isinstance(principal_arn, str) and f':{self.account_id}:' not in principal_arn:
                                if principal_arn != "*":
                                    cross_account_roles.append((role['RoleName'], principal_arn))

            if cross_account_roles:
                print(f"\nFound {len(cross_account_roles)} cross-account roles:\n")
                for role_name, principal in cross_account_roles:
                    self.print_finding('INFO', f"✓ {role_name}",
                                      f"Allows: {principal}")
            else:
                print("✓ No cross-account access roles\n")

        except Exception as e:
            self.print_finding('HIGH', "Error checking cross-account access", str(e))

    def check_service_accounts(self):
        """Check service account security"""
        self.print_header("Service Account Security Audit")

        try:
            roles = self.iam.list_roles(MaxItems=1000)['Roles']
            service_roles = [r for r in roles if 'service' in r['RoleName'].lower() or
                            'lambda' in r['RoleName'].lower() or
                            'ecs' in r['RoleName'].lower()]

            print(f"Found {len(service_roles)} service accounts\n")

            for role in service_roles:
                role_name = role['RoleName']

                # Check for permission boundary
                has_boundary = bool(role.get('PermissionsBoundaryArn'))
                if not has_boundary:
                    self.print_finding('MEDIUM',
                                     f"✗ {role_name} missing permission boundary",
                                     "Service accounts should have permission boundaries")

                # Check for excessive permissions
                attached = self.iam.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']
                for policy in attached:
                    if 'FullAccess' in policy['PolicyName'] or 'Administrator' in policy['PolicyName']:
                        self.print_finding('HIGH',
                                         f"✗ {role_name} has excessive permissions",
                                         f"Policy: {policy['PolicyName']}")

        except Exception as e:
            self.print_finding('HIGH', "Error checking service accounts", str(e))

    def review_access(self, days: int = 30):
        """Review recent access patterns"""
        self.print_header(f"Access Review (last {days} days)")

        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            end_time = datetime.utcnow()

            # Query CloudTrail
            events = self.cloudtrail.lookup_events(
                LookupAttributes=[
                    {
                        'AttributeKey': 'EventSource',
                        'AttributeValue': 'iam.amazonaws.com'
                    }
                ],
                StartTime=start_time,
                MaxResults=50
            )['Events']

            print(f"Found {len(events)} IAM events\n")

            # Categorize events
            event_types = {}
            for event in events:
                event_name = event['EventName']
                event_types[event_name] = event_types.get(event_name, 0) + 1

            # Show top events
            print("Top IAM events:")
            for event_name in sorted(event_types.keys(), key=lambda x: event_types[x], reverse=True)[:10]:
                print(f"  {event_name}: {event_types[event_name]}")

        except Exception as e:
            self.print_finding('HIGH', "Error reviewing access", str(e))

    def check_unused_access(self):
        """Identify unused access keys and credentials"""
        self.print_header("Unused Access Credentials Audit")

        try:
            credential_report = self._get_credential_report()
            if not credential_report:
                return

            now = datetime.utcnow()
            unused_credentials = []

            for row in credential_report:
                user_name = row.get('user')
                if not user_name or user_name == '<root_account>':
                    continue

                # Check last password used
                password_last_used = row.get('password_last_used')
                if password_last_used and password_last_used != 'N/A':
                    try:
                        last_used = datetime.fromisoformat(password_last_used.replace('Z', '+00:00'))
                        days_since_used = (now - last_used).days
                        if days_since_used > 90:
                            unused_credentials.append((user_name, 'password', days_since_used))
                    except:
                        pass

            if unused_credentials:
                print(f"\nFound {len(unused_credentials)} unused credentials:\n")
                for user_name, cred_type, days_old in unused_credentials:
                    self.print_finding('MEDIUM',
                                     f"✗ {user_name} {cred_type} unused for {days_old} days",
                                     "Consider disabling unused credentials")
            else:
                print("✓ All credentials recently used\n")

        except Exception as e:
            self.print_finding('HIGH', "Error checking unused credentials", str(e))

    def _get_credential_report(self) -> List[Dict]:
        """Get IAM credential report"""
        try:
            # Request report
            self.iam.generate_credential_report()

            # Get report (may need retry)
            import time
            for _ in range(10):
                response = self.iam.get_credential_report()
                if response['Content']:
                    import csv
                    from io import StringIO

                    content = response['Content'].decode('utf-8')
                    reader = csv.DictReader(StringIO(content))
                    return list(reader)

                time.sleep(1)

            return []
        except Exception as e:
            self.print_finding('HIGH', "Error generating credential report", str(e))
            return []

    def _action_matches(self, action: str, pattern: str) -> bool:
        """Check if action matches pattern (with wildcards)"""
        if action == pattern:
            return True
        if action == "*":
            return True
        if pattern.endswith("*"):
            return action.startswith(pattern[:-1])
        return False

    def print_summary(self):
        """Print audit summary"""
        self.print_header("Audit Summary")

        # Count findings by severity
        critical = sum(1 for f in self.findings if f['severity'] == 'CRITICAL')
        high = sum(1 for f in self.findings if f['severity'] == 'HIGH')
        medium = sum(1 for f in self.findings if f['severity'] == 'MEDIUM')
        low = sum(1 for f in self.findings if f['severity'] == 'LOW')
        info = sum(1 for f in self.findings if f['severity'] == 'INFO')

        print(f"Total Findings: {len(self.findings)}\n")
        print(f"  Critical: {critical}")
        print(f"  High:     {high}")
        print(f"  Medium:   {medium}")
        print(f"  Low:      {low}")
        print(f"  Info:     {info}")

        if critical > 0:
            print(f"\n⚠️  CRITICAL ISSUES FOUND - IMMEDIATE ACTION REQUIRED")
        elif high > 0:
            print(f"\n⚠️  High-priority issues found - review recommended")
        else:
            print(f"\n✓ No critical or high-priority issues")

    def export_report(self, filename: str = None):
        """Export audit report to JSON"""
        if not filename:
            filename = f"iam-audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

        report = {
            'timestamp': datetime.now().isoformat(),
            'account_id': self.account_id,
            'findings': self.findings,
            'summary': {
                'total': len(self.findings),
                'critical': sum(1 for f in self.findings if f['severity'] == 'CRITICAL'),
                'high': sum(1 for f in self.findings if f['severity'] == 'HIGH'),
                'medium': sum(1 for f in self.findings if f['severity'] == 'MEDIUM'),
                'low': sum(1 for f in self.findings if f['severity'] == 'LOW'),
                'info': sum(1 for f in self.findings if f['severity'] == 'INFO')
            }
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n✓ Report exported to {filename}")
        return filename


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='THE_BOT IAM Audit Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 iam-audit.py --audit-all
  python3 iam-audit.py --check-escalation
  python3 iam-audit.py --review-access --days 30
  python3 iam-audit.py --unused-access
  python3 iam-audit.py --audit-all --export audit.json
        """
    )

    parser.add_argument('--audit-all', action='store_true',
                       help='Run comprehensive IAM audit')
    parser.add_argument('--check-escalation', action='store_true',
                       help='Check for privilege escalation vulnerabilities')
    parser.add_argument('--review-access', action='store_true',
                       help='Review recent access patterns')
    parser.add_argument('--days', type=int, default=30,
                       help='Days to review (default: 30)')
    parser.add_argument('--unused-access', action='store_true',
                       help='Find unused credentials')
    parser.add_argument('--export', type=str,
                       help='Export report to JSON file')

    args = parser.parse_args()

    audit = IAMaudit()

    try:
        if args.audit_all:
            audit.audit_all()
        elif args.check_escalation:
            audit.print_header("Privilege Escalation Risk Check")
            audit.check_privilege_escalation()
            audit.print_summary()
        elif args.review_access:
            audit.review_access(days=args.days)
        elif args.unused_access:
            audit.check_unused_access()
        else:
            parser.print_help()
            return 1

        if args.export:
            audit.export_report(args.export)

        return 0 if len([f for f in audit.findings if f['severity'] == 'CRITICAL']) == 0 else 1

    except KeyboardInterrupt:
        print("\n\nAudit cancelled by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
