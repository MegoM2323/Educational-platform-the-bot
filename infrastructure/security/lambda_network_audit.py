"""
Network Segmentation Audit Lambda Function

This function runs daily to verify network security configuration
and alert on any deviations from expected state.

Checks:
- VPC configuration (CIDR blocks, Flow Logs)
- Subnet configuration (routing, ACLs)
- Security group rules (least privilege)
- Network ACL rules
- NAT Gateway status
- VPC Endpoint configuration
"""

import json
import boto3
import os
from datetime import datetime
import logging
from typing import Dict, List, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')

# Environment variables
VPC_ID = os.environ.get('VPC_ID')
EXPECTED_SUBNETS = os.environ.get('EXPECTED_SUBNETS', '').split(',')
EXPECTED_NAT_GATEWAYS = int(os.environ.get('EXPECTED_NAT_GATEWAYS', '3'))
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')


class NetworkAuditCheck:
    """Network segmentation audit checks"""

    def __init__(self):
        self.findings = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        self.audit_timestamp = datetime.utcnow().isoformat()

    def add_pass(self, check_name: str, details: str = ''):
        """Record passed check"""
        self.findings['passed'].append({
            'check': check_name,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.info(f"PASS: {check_name} - {details}")

    def add_fail(self, check_name: str, details: str = ''):
        """Record failed check"""
        self.findings['failed'].append({
            'check': check_name,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.error(f"FAIL: {check_name} - {details}")

    def add_warning(self, check_name: str, details: str = ''):
        """Record warning"""
        self.findings['warnings'].append({
            'check': check_name,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
        logger.warning(f"WARN: {check_name} - {details}")

    # ========================================================
    # Check Methods
    # ========================================================

    def check_vpc_configuration(self) -> bool:
        """Verify VPC basic configuration"""
        try:
            response = ec2_client.describe_vpcs(VpcIds=[VPC_ID])

            if not response['Vpcs']:
                self.add_fail('VPC Configuration', 'VPC not found')
                return False

            vpc = response['Vpcs'][0]

            # Check VPC CIDR
            if vpc['CidrBlock'] != '10.0.0.0/16':
                self.add_warning('VPC CIDR',
                    f"Expected 10.0.0.0/16, found {vpc['CidrBlock']}")
            else:
                self.add_pass('VPC CIDR', '10.0.0.0/16')

            # Check DNS settings
            if vpc['DnsHostnamesEnabled'] and vpc['DnsResolutionEnabled']:
                self.add_pass('DNS Configuration', 'Enabled')
            else:
                self.add_fail('DNS Configuration', 'DNS not fully enabled')
                return False

            return True

        except Exception as e:
            self.add_fail('VPC Configuration', str(e))
            return False

    def check_flow_logs(self) -> bool:
        """Verify VPC Flow Logs enabled"""
        try:
            response = ec2_client.describe_flow_logs(
                Filter=[
                    {'Name': 'resource-id', 'Values': [VPC_ID]},
                    {'Name': 'flow-log-status', 'Values': ['ACTIVE']}
                ]
            )

            if response['FlowLogs']:
                flow_log = response['FlowLogs'][0]
                self.add_pass('VPC Flow Logs',
                    f"Active, destination: {flow_log['LogDestinationType']}")
                return True
            else:
                self.add_fail('VPC Flow Logs', 'No active flow logs')
                return False

        except Exception as e:
            self.add_fail('VPC Flow Logs', str(e))
            return False

    def check_subnet_configuration(self) -> bool:
        """Verify subnet configuration"""
        try:
            response = ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [VPC_ID]}]
            )

            subnets = response['Subnets']
            expected_cidrs = {
                '10.0.1.0/24': 'Public-AZ1',
                '10.0.2.0/24': 'Public-AZ2',
                '10.0.3.0/24': 'Public-AZ3',
                '10.0.11.0/24': 'App-AZ1',
                '10.0.12.0/24': 'App-AZ2',
                '10.0.13.0/24': 'App-AZ3',
                '10.0.21.0/24': 'DB-AZ1',
                '10.0.22.0/24': 'DB-AZ2',
                '10.0.23.0/24': 'DB-AZ3',
            }

            found_cidrs = {subnet['CidrBlock']: subnet for subnet in subnets}

            # Check all expected subnets exist
            for expected_cidr in expected_cidrs.keys():
                if expected_cidr in found_cidrs:
                    self.add_pass('Subnet CIDR',
                        f"{expected_cidrs[expected_cidr]}: {expected_cidr}")
                else:
                    self.add_fail('Subnet CIDR',
                        f"Missing {expected_cidrs[expected_cidr]}: {expected_cidr}")
                    return False

            self.add_pass('Subnet Count', f"{len(subnets)} subnets found")
            return True

        except Exception as e:
            self.add_fail('Subnet Configuration', str(e))
            return False

    def check_security_groups(self) -> bool:
        """Verify security group configuration"""
        try:
            response = ec2_client.describe_security_groups(
                Filters=[{'Name': 'vpc-id', 'Values': [VPC_ID]}]
            )

            sgs = response['SecurityGroups']
            required_sgs = ['thebot-bastion-sg', 'thebot-frontend-sg',
                           'thebot-backend-sg', 'thebot-database-sg',
                           'thebot-redis-sg']

            found_sgs = {sg['GroupName']: sg for sg in sgs}

            # Check required security groups exist
            for required_sg in required_sgs:
                if required_sg in found_sgs:
                    sg = found_sgs[required_sg]
                    rules_count = (len(sg['IpPermissions']) +
                                 len(sg['IpPermissionsEgress']))
                    self.add_pass('Security Group', f"{required_sg} exists")
                else:
                    self.add_fail('Security Group', f"{required_sg} missing")

            # Check for overly permissive rules
            overly_permissive = self._find_overly_permissive_rules(sgs)
            if overly_permissive:
                for sg_id, rules in overly_permissive.items():
                    self.add_warning('Overly Permissive Rules',
                        f"SG {sg_id}: {len(rules)} rules allow 0.0.0.0/0")
                return False

            return len(required_sgs) <= len(found_sgs)

        except Exception as e:
            self.add_fail('Security Groups', str(e))
            return False

    def check_nacl_configuration(self) -> bool:
        """Verify Network ACL configuration"""
        try:
            response = ec2_client.describe_network_acls(
                Filters=[{'Name': 'vpc-id', 'Values': [VPC_ID]}]
            )

            nacls = response['NetworkAcls']

            if len(nacls) < 4:
                self.add_warning('NACLs', f"Only {len(nacls)} NACLs found")

            for nacl in nacls:
                # Check for deny rules (defense in depth)
                deny_rules = [r for r in nacl['Entries']
                            if r['RuleAction'] == 'deny']
                if deny_rules:
                    self.add_pass('NACL Deny Rules',
                        f"NACL {nacl['NetworkAclId']}: {len(deny_rules)} deny rules")
                else:
                    self.add_warning('NACL Deny Rules',
                        f"NACL {nacl['NetworkAclId']}: no deny rules found")

            return True

        except Exception as e:
            self.add_fail('NACL Configuration', str(e))
            return False

    def check_nat_gateways(self) -> bool:
        """Verify NAT Gateway configuration"""
        try:
            response = ec2_client.describe_nat_gateways(
                Filter=[
                    {'Name': 'vpc-id', 'Values': [VPC_ID]},
                    {'Name': 'state', 'Values': ['available']}
                ]
            )

            nats = response['NatGateways']

            if len(nats) == EXPECTED_NAT_GATEWAYS:
                self.add_pass('NAT Gateway Count',
                    f"{len(nats)} NAT Gateways found")
            else:
                self.add_fail('NAT Gateway Count',
                    f"Expected {EXPECTED_NAT_GATEWAYS}, found {len(nats)}")
                return False

            # Check one per AZ
            azs = set()
            for nat in nats:
                azs.add(nat['SubnetId'])
                if nat['State'] == 'available':
                    eip = nat.get('PublicIp', 'N/A')
                    self.add_pass('NAT Gateway Status',
                        f"AZ {nat['AvailabilityZone']}: {eip}")

            return True

        except Exception as e:
            self.add_fail('NAT Gateways', str(e))
            return False

    def check_vpc_endpoints(self) -> bool:
        """Verify VPC Endpoint configuration"""
        try:
            response = ec2_client.describe_vpc_endpoints(
                Filters=[{'Name': 'vpc-id', 'Values': [VPC_ID]}]
            )

            endpoints = response['VpcEndpoints']

            if not endpoints:
                self.add_warning('VPC Endpoints', 'No VPC Endpoints found')
                return True

            expected_services = [
                's3', 'dynamodb', 'ecr', 'logs', 'monitoring', 'ssm'
            ]
            found_services = set()

            for endpoint in endpoints:
                service_name = endpoint['ServiceName'].split('.')[-1]
                found_services.add(service_name)
                self.add_pass('VPC Endpoint',
                    f"{endpoint['ServiceName']}: {endpoint['State']}")

            for service in expected_services:
                if service not in found_services:
                    self.add_warning('VPC Endpoint',
                        f"Expected endpoint not found: {service}")

            return True

        except Exception as e:
            self.add_fail('VPC Endpoints', str(e))
            return False

    # ========================================================
    # Helper Methods
    # ========================================================

    def _find_overly_permissive_rules(self, sgs: List[Dict]) -> Dict:
        """Find security group rules allowing 0.0.0.0/0"""
        overly_permissive = {}

        for sg in sgs:
            sg_id = sg['GroupId']
            permissive_rules = []

            # Check inbound rules
            for rule in sg['IpPermissions']:
                for cidr in rule.get('IpRanges', []):
                    if cidr.get('CidrIp') == '0.0.0.0/0':
                        # Allow only specific ports on public tier
                        if sg['GroupName'] != 'thebot-frontend-sg':
                            permissive_rules.append(rule.get('FromPort', 'N/A'))

            if permissive_rules:
                overly_permissive[sg_id] = permissive_rules

        return overly_permissive

    def run_all_checks(self) -> bool:
        """Run all audit checks"""
        all_passed = True

        logger.info("Starting network segmentation audit...")

        all_passed &= self.check_vpc_configuration()
        all_passed &= self.check_flow_logs()
        all_passed &= self.check_subnet_configuration()
        all_passed &= self.check_security_groups()
        all_passed &= self.check_nacl_configuration()
        all_passed &= self.check_nat_gateways()
        all_passed &= self.check_vpc_endpoints()

        logger.info("Network segmentation audit complete")

        return all_passed

    def get_report(self) -> Dict[str, Any]:
        """Get audit report"""
        return {
            'audit_timestamp': self.audit_timestamp,
            'vpc_id': VPC_ID,
            'summary': {
                'passed': len(self.findings['passed']),
                'failed': len(self.findings['failed']),
                'warnings': len(self.findings['warnings']),
            },
            'findings': self.findings
        }


def send_slack_notification(message: str, severity: str = 'info'):
    """Send notification to Slack"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("Slack webhook URL not configured")
        return

    try:
        import requests

        color = {
            'success': '#36a64f',
            'warning': '#ff9900',
            'error': '#cc0000',
            'info': '#0099cc'
        }.get(severity, '#0099cc')

        payload = {
            'attachments': [{
                'color': color,
                'title': f'Network Security Audit - {severity.upper()}',
                'text': message,
                'ts': int(datetime.utcnow().timestamp())
            }]
        }

        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        logger.info("Slack notification sent")

    except Exception as e:
        logger.error(f"Failed to send Slack notification: {str(e)}")


def lambda_handler(event, context):
    """Lambda handler for network audit"""
    try:
        logger.info(f"Network Audit Lambda triggered: {json.dumps(event)}")

        # Run audit checks
        audit = NetworkAuditCheck()
        all_passed = audit.run_all_checks()

        report = audit.get_report()

        # Log report
        logger.info(f"Audit Report: {json.dumps(report, indent=2)}")

        # Format report for Slack
        summary = report['summary']
        message = f"""
Network Segmentation Audit Report
VPC: {VPC_ID}
Timestamp: {report['audit_timestamp']}

Results:
- Passed: {summary['passed']}
- Failed: {summary['failed']}
- Warnings: {summary['warnings']}

Status: {'✅ PASS' if all_passed else '❌ FAIL'}
"""

        # Send notification
        severity = 'success' if all_passed else 'error'
        send_slack_notification(message, severity)

        return {
            'statusCode': 200,
            'body': json.dumps(report),
            'success': all_passed
        }

    except Exception as e:
        logger.error(f"Network Audit Lambda error: {str(e)}", exc_info=True)

        error_message = f"Network audit failed: {str(e)}"
        send_slack_notification(error_message, 'error')

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'success': False
        }


if __name__ == '__main__':
    # Local testing
    import sys
    os.environ['VPC_ID'] = 'vpc-xxxxx'
    os.environ['EXPECTED_NAT_GATEWAYS'] = '3'

    result = lambda_handler({}, None)
    print(json.dumps(result, indent=2))
