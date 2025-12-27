#!/usr/bin/env python3
"""
THE_BOT Platform - Security Groups Audit Script

Validates security group configuration for compliance and security best practices.
Detects overly permissive rules, missing critical rules, and compliance violations.

Usage:
    python3 security-groups-audit.py --environment production
    python3 security-groups-audit.py --environment staging --format json
    python3 security-groups-audit.py --environment production --check permissive-rules

Requirements:
    - boto3
    - botocore
    - AWS credentials configured
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Install with: pip install boto3")
    sys.exit(1)


class ComplianceStatus(Enum):
    """Compliance status enumeration."""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    WARNING = "WARNING"


class RiskLevel(Enum):
    """Risk level enumeration."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class SecurityGroupRule:
    """Represents a security group rule."""
    group_id: str
    group_name: str
    is_egress: bool
    port: Optional[int]
    from_port: Optional[int]
    to_port: Optional[int]
    protocol: str
    cidr_ipv4: Optional[str]
    source_security_group_id: Optional[str]
    description: str
    tags: Dict[str, str]


@dataclass
class AuditFinding:
    """Represents an audit finding."""
    severity: RiskLevel
    category: str
    rule_id: str
    group_id: str
    group_name: str
    message: str
    details: Dict[str, Any]
    remediation: str


@dataclass
class AuditReport:
    """Represents complete audit report."""
    timestamp: str
    vpc_id: str
    environment: str
    total_security_groups: int
    total_rules: int
    compliant_groups: int
    non_compliant_groups: int
    findings: List[AuditFinding]
    overall_status: ComplianceStatus


class SecurityGroupAudit:
    """Main audit class."""

    # Expected security group names
    EXPECTED_SECURITY_GROUPS = {
        "bastion": {"inbound": ["ssh"], "outbound": ["all"]},
        "frontend": {"inbound": ["http", "https"], "outbound": ["backend", "all"]},
        "backend": {"inbound": ["alb", "bastion", "redis"], "outbound": ["database", "redis", "all"]},
        "database": {"inbound": ["backend", "bastion"], "outbound": []},
        "redis": {"inbound": ["backend", "bastion", "internal"], "outbound": []},
        "vpc_endpoints": {"inbound": ["https", "http"], "outbound": []},
    }

    # High-risk patterns
    OVERLY_PERMISSIVE_PATTERNS = [
        {"ports": [5432], "cidr": "0.0.0.0/0", "protocol": "tcp", "reason": "Public database access"},
        {"ports": [3306], "cidr": "0.0.0.0/0", "protocol": "tcp", "reason": "Public MySQL access"},
        {"ports": [6379], "cidr": "0.0.0.0/0", "protocol": "tcp", "reason": "Public Redis access"},
        {"ports": [27017], "cidr": "0.0.0.0/0", "protocol": "tcp", "reason": "Public MongoDB access"},
        {"ports": [22], "cidr": "0.0.0.0/0", "protocol": "tcp", "reason": "Public SSH (except ALB)"},
    ]

    def __init__(self, environment: str = "production", region: str = "us-east-1"):
        """Initialize audit with AWS clients."""
        self.environment = environment
        self.region = region
        self.ec2 = boto3.client("ec2", region_name=region)
        self.findings: List[AuditFinding] = []

    def run_audit(self, sg_name_filter: Optional[str] = None) -> AuditReport:
        """Run complete security group audit."""
        print(f"\n{'='*70}")
        print(f"THE_BOT Platform - Security Groups Audit Report")
        print(f"{'='*70}")
        print(f"Environment: {self.environment}")
        print(f"Region: {self.region}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"{'='*70}\n")

        try:
            # Get VPC ID
            vpc_response = self.ec2.describe_vpcs(
                Filters=[
                    {"Name": "tag:Environment", "Values": [self.environment]},
                    {"Name": "tag:ManagedBy", "Values": ["Terraform"]},
                ]
            )

            if not vpc_response["Vpcs"]:
                print("ERROR: No VPC found with matching tags")
                sys.exit(1)

            vpc_id = vpc_response["Vpcs"][0]["VpcId"]
            print(f"VPC ID: {vpc_id}\n")

            # Get security groups
            sgs = self._get_security_groups(vpc_id, sg_name_filter)

            if not sgs:
                print("ERROR: No security groups found")
                sys.exit(1)

            # Audit each security group
            total_rules = 0
            compliant_count = 0

            for sg in sgs:
                print(f"\nAuditing: {sg['GroupName']} ({sg['GroupId']})")
                print(f"{'-'*70}")

                sg_rules = self._get_rules_for_sg(sg["GroupId"])
                total_rules += len(sg_rules)

                # Run checks
                self._check_overly_permissive_rules(sg, sg_rules)
                self._check_expected_rules(sg, sg_rules)
                self._check_tag_compliance(sg)
                self._check_rule_documentation(sg_rules)
                self._check_outbound_restrictions(sg, sg_rules)

                compliant = self._is_sg_compliant(sg["GroupId"])
                if compliant:
                    compliant_count += 1
                    print(f"Status: ✓ COMPLIANT\n")
                else:
                    print(f"Status: ✗ NON-COMPLIANT\n")

            # Generate report
            overall_status = (
                ComplianceStatus.COMPLIANT
                if len(self.findings) == 0
                else ComplianceStatus.NON_COMPLIANT
            )

            report = AuditReport(
                timestamp=datetime.now().isoformat(),
                vpc_id=vpc_id,
                environment=self.environment,
                total_security_groups=len(sgs),
                total_rules=total_rules,
                compliant_groups=compliant_count,
                non_compliant_groups=len(sgs) - compliant_count,
                findings=self.findings,
                overall_status=overall_status,
            )

            self._print_summary(report)
            return report

        except ClientError as e:
            print(f"ERROR: AWS API call failed: {e}")
            sys.exit(1)

    def _get_security_groups(
        self, vpc_id: str, sg_name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all security groups in VPC."""
        filters = [{"Name": "vpc-id", "Values": [vpc_id]}]

        if sg_name_filter:
            filters.append({"Name": "group-name", "Values": [f"*{sg_name_filter}*"]})

        response = self.ec2.describe_security_groups(Filters=filters)
        return response["SecurityGroups"]

    def _get_rules_for_sg(self, sg_id: str) -> List[SecurityGroupRule]:
        """Get all rules for a security group."""
        response = self.ec2.describe_security_group_rules(
            Filters=[{"Name": "group-id", "Values": [sg_id]}]
        )

        rules = []
        for rule in response["SecurityGroupRules"]:
            rules.append(
                SecurityGroupRule(
                    group_id=rule["GroupId"],
                    group_name=rule["GroupOwnerId"],  # Will be updated by caller
                    is_egress=rule["IsEgress"],
                    port=rule.get("FromPort"),
                    from_port=rule.get("FromPort"),
                    to_port=rule.get("ToPort"),
                    protocol=rule.get("IpProtocol", "N/A"),
                    cidr_ipv4=rule.get("CidrIpv4"),
                    source_security_group_id=rule.get("ReferencedGroupInfo", {}).get("GroupId"),
                    description=rule.get("Description", ""),
                    tags=rule.get("Tags", {}),
                )
            )

        return rules

    def _check_overly_permissive_rules(
        self, sg: Dict[str, Any], rules: List[SecurityGroupRule]
    ) -> None:
        """Check for overly permissive inbound rules."""
        sg_name = sg["GroupName"]

        # Database and Redis should never be public
        is_restricted_sg = any(
            x in sg_name.lower() for x in ["database", "redis", "db"]
        )

        for rule in rules:
            if rule.is_egress:
                continue

            # Check for public database/redis access
            if is_restricted_sg and rule.cidr_ipv4 == "0.0.0.0/0":
                self.findings.append(
                    AuditFinding(
                        severity=RiskLevel.CRITICAL,
                        category="Overly Permissive Rule",
                        rule_id=f"{sg['GroupId']}_inbound",
                        group_id=sg["GroupId"],
                        group_name=sg_name,
                        message=f"Public access to {sg_name} (port {rule.from_port})",
                        details={
                            "port": rule.from_port,
                            "protocol": rule.protocol,
                            "source": rule.cidr_ipv4,
                        },
                        remediation=f"Remove rule allowing 0.0.0.0/0 on port {rule.from_port}",
                    )
                )

            # Check patterns
            for pattern in self.OVERLY_PERMISSIVE_PATTERNS:
                if (
                    rule.from_port in pattern.get("ports", [])
                    and rule.cidr_ipv4 == pattern.get("cidr")
                    and rule.protocol == pattern.get("protocol")
                    and "bastion" not in sg_name.lower()  # SSH on Bastion is OK
                ):
                    self.findings.append(
                        AuditFinding(
                            severity=RiskLevel.HIGH,
                            category="Overly Permissive Rule",
                            rule_id=f"{sg['GroupId']}_inbound_{rule.from_port}",
                            group_id=sg["GroupId"],
                            group_name=sg_name,
                            message=pattern["reason"],
                            details={
                                "port": rule.from_port,
                                "protocol": rule.protocol,
                                "source": rule.cidr_ipv4,
                            },
                            remediation=f"Restrict access to specific security group",
                        )
                    )

    def _check_expected_rules(
        self, sg: Dict[str, Any], rules: List[SecurityGroupRule]
    ) -> None:
        """Check if expected rules are present."""
        sg_name = sg["GroupName"]

        # Find matching expected config
        for expected_name, expected_config in self.EXPECTED_SECURITY_GROUPS.items():
            if expected_name in sg_name.lower():
                # Check inbound
                inbound_rules = [r for r in rules if not r.is_egress]
                if not inbound_rules and expected_config.get("inbound"):
                    self.findings.append(
                        AuditFinding(
                            severity=RiskLevel.MEDIUM,
                            category="Missing Expected Rules",
                            rule_id=f"{sg['GroupId']}_missing_inbound",
                            group_id=sg["GroupId"],
                            group_name=sg_name,
                            message=f"No inbound rules found for {expected_name}",
                            details={"expected": expected_config.get("inbound", [])},
                            remediation=f"Add inbound rules: {expected_config.get('inbound', [])}",
                        )
                    )

    def _check_tag_compliance(self, sg: Dict[str, Any]) -> None:
        """Check if required tags are present."""
        required_tags = ["Name", "Environment", "ManagedBy"]
        tags = sg.get("Tags", {})
        tag_keys = {tag["Key"] for tag in tags}

        for required in required_tags:
            if required not in tag_keys:
                self.findings.append(
                    AuditFinding(
                        severity=RiskLevel.LOW,
                        category="Tag Compliance",
                        rule_id=f"{sg['GroupId']}_tag_{required}",
                        group_id=sg["GroupId"],
                        group_name=sg["GroupName"],
                        message=f"Missing required tag: {required}",
                        details={"expected_tag": required, "current_tags": tag_keys},
                        remediation=f"Add tag: {required}=<value>",
                    )
                )

    def _check_rule_documentation(self, rules: List[SecurityGroupRule]) -> None:
        """Check if rules have descriptions."""
        for rule in rules:
            if not rule.description:
                self.findings.append(
                    AuditFinding(
                        severity=RiskLevel.LOW,
                        category="Documentation",
                        rule_id=f"{rule.group_id}_undocumented",
                        group_id=rule.group_id,
                        group_name=rule.group_name,
                        message="Rule missing description",
                        details={
                            "port": rule.from_port,
                            "direction": "egress" if rule.is_egress else "ingress",
                        },
                        remediation="Add description to rule",
                    )
                )

    def _check_outbound_restrictions(
        self, sg: Dict[str, Any], rules: List[SecurityGroupRule]
    ) -> None:
        """Check if restricted SGs block outbound properly."""
        sg_name = sg["GroupName"]
        is_restricted = any(
            x in sg_name.lower() for x in ["database", "redis", "db"]
        )

        if is_restricted:
            outbound_rules = [r for r in rules if r.is_egress]

            # Check if there's any real outbound allowed
            for rule in outbound_rules:
                if rule.cidr_ipv4 and rule.cidr_ipv4 != "127.0.0.1/32":
                    self.findings.append(
                        AuditFinding(
                            severity=RiskLevel.HIGH,
                            category="Outbound Restriction",
                            rule_id=f"{sg['GroupId']}_outbound_allowed",
                            group_id=sg["GroupId"],
                            group_name=sg_name,
                            message=f"Restricted service has outbound access",
                            details={
                                "destination": rule.cidr_ipv4,
                                "port": rule.from_port,
                            },
                            remediation="Remove outbound rule or restrict to unreachable IP",
                        )
                    )

    def _is_sg_compliant(self, sg_id: str) -> bool:
        """Check if security group has any critical findings."""
        for finding in self.findings:
            if finding.group_id == sg_id and finding.severity == RiskLevel.CRITICAL:
                return False
        return True

    def _print_summary(self, report: AuditReport) -> None:
        """Print audit summary."""
        print(f"\n{'='*70}")
        print("AUDIT SUMMARY")
        print(f"{'='*70}")
        print(f"Overall Status: {report.overall_status.value}")
        print(f"Security Groups Audited: {report.total_security_groups}")
        print(f"Compliant Groups: {report.compliant_groups}")
        print(f"Non-Compliant Groups: {report.non_compliant_groups}")
        print(f"Total Rules Checked: {report.total_rules}")
        print(f"Total Findings: {len(report.findings)}")

        # Group findings by severity
        critical = [f for f in report.findings if f.severity == RiskLevel.CRITICAL]
        high = [f for f in report.findings if f.severity == RiskLevel.HIGH]
        medium = [f for f in report.findings if f.severity == RiskLevel.MEDIUM]
        low = [f for f in report.findings if f.severity == RiskLevel.LOW]

        if critical:
            print(f"\nCRITICAL Findings: {len(critical)}")
            for finding in critical[:5]:  # Show first 5
                print(f"  - {finding.message}")
                print(f"    Group: {finding.group_name}")
                print(f"    Remediation: {finding.remediation}")

        if high:
            print(f"\nHIGH Findings: {len(high)}")
            for finding in high[:5]:  # Show first 5
                print(f"  - {finding.message}")

        if medium:
            print(f"\nMEDIUM Findings: {len(medium)}")

        if low:
            print(f"\nLOW Findings: {len(low)}")

        print(f"\n{'='*70}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="THE_BOT Platform - Security Groups Audit Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Audit production environment
  python3 security-groups-audit.py --environment production

  # Audit staging with JSON output
  python3 security-groups-audit.py --environment staging --format json

  # Audit specific security group
  python3 security-groups-audit.py --environment production --sg-name backend

  # Check for specific violation type
  python3 security-groups-audit.py --environment production --check permissive-rules
        """,
    )

    parser.add_argument(
        "--environment",
        default="production",
        choices=["production", "staging", "development"],
        help="Environment to audit (default: production)",
    )

    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )

    parser.add_argument(
        "--sg-name",
        dest="sg_name",
        help="Filter to specific security group name pattern",
    )

    parser.add_argument(
        "--format",
        default="text",
        choices=["text", "json", "csv"],
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--check",
        choices=["permissive-rules", "missing-rules", "tags", "all"],
        default="all",
        help="Specific check to run (default: all)",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    # Run audit
    audit = SecurityGroupAudit(environment=args.environment, region=args.region)
    report = audit.run_audit(sg_name_filter=args.sg_name)

    # Format output
    if args.format == "json":
        output = json.dumps(
            {
                "timestamp": report.timestamp,
                "vpc_id": report.vpc_id,
                "environment": report.environment,
                "status": report.overall_status.value,
                "summary": {
                    "total_security_groups": report.total_security_groups,
                    "total_rules": report.total_rules,
                    "compliant_groups": report.compliant_groups,
                    "non_compliant_groups": report.non_compliant_groups,
                    "findings_count": len(report.findings),
                },
                "findings": [
                    {
                        "severity": f.severity.value,
                        "category": f.category,
                        "group": f.group_name,
                        "message": f.message,
                        "remediation": f.remediation,
                    }
                    for f in report.findings
                ],
            },
            indent=2,
        )
    elif args.format == "csv":
        output = "Severity,Category,Group,Message,Remediation\n"
        for finding in report.findings:
            output += (
                f'"{finding.severity.value}","{finding.category}",'
                f'"{finding.group_name}","{finding.message}","{finding.remediation}"\n'
            )
    else:
        output = ""  # Text output already printed

    if args.output:
        with open(args.output, "w") as f:
            if output:
                f.write(output)
    else:
        if output:
            print(output)

    # Exit with appropriate code
    sys.exit(0 if report.overall_status == ComplianceStatus.COMPLIANT else 1)


if __name__ == "__main__":
    main()
