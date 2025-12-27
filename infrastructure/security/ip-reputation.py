#!/usr/bin/env python3
"""
IP Reputation Checker and Aggregator

Integrates with multiple threat intelligence sources:
- AbuseIPDB (https://www.abuseipdb.com/)
- Spamhaus (https://www.spamhaus.org/)
- AWS WAF IP sets management

Usage:
    python ip-reputation.py --check <ip>          Check single IP
    python ip-reputation.py --update              Update all IP lists
    python ip-reputation.py --export terraform    Export as Terraform variables
"""

import os
import sys
import json
import logging
import requests
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
from pathlib import Path
import boto3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ABUSEIPDB_API_KEY = os.getenv('ABUSEIPDB_API_KEY', '')
ABUSEIPDB_THRESHOLD = int(os.getenv('ABUSEIPDB_THRESHOLD', '75'))
SPAMHAUS_API_KEY = os.getenv('SPAMHAUS_API_KEY', '')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# File paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / 'ip-reputation-data'
ABUSEIPDB_FILE = DATA_DIR / 'abuseipdb.json'
SPAMHAUS_FILE = DATA_DIR / 'spamhaus.json'
COMBINED_FILE = DATA_DIR / 'combined-blocklist.json'

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


class IPReputationChecker:
    """
    Checks IP reputation across multiple threat intelligence sources.

    Поддерживает интеграцию с:
    - AbuseIPDB: контроль за IP с высоким уровнем злоупотреблений
    - Spamhaus: защита от спама и ботнетов
    - AWS WAF: управление списками блокировок
    """

    def __init__(self):
        """Инициализация проверки репутации IP."""
        self.abuseipdb_ips: Set[str] = set()
        self.spamhaus_ips: Set[str] = set()
        self.combined_ips: Set[str] = set()
        self.s3_client = boto3.client('s3', region_name=AWS_REGION)
        self.waf_client = boto3.client('wafv2', region_name=AWS_REGION)

    def check_abuseipdb(self, ip: str, days: int = 90) -> Dict:
        """
        Check IP reputation on AbuseIPDB.

        Args:
            ip: IP address to check
            days: Number of days to look back

        Returns:
            Dictionary with abuse score and details
        """
        if not ABUSEIPDB_API_KEY:
            logger.warning("ABUSEIPDB_API_KEY not set, skipping AbuseIPDB check")
            return {}

        try:
            url = 'https://api.abuseipdb.com/api/v2/check'
            headers = {
                'Key': ABUSEIPDB_API_KEY,
                'Accept': 'application/json'
            }
            params = {
                'ipAddress': ip,
                'maxAgeInDays': days,
                'verbose': ''
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            abuseData = data.get('data', {})

            return {
                'ip': ip,
                'source': 'abuseipdb',
                'score': abuseData.get('abuseConfidenceScore', 0),
                'reports': abuseData.get('totalReports', 0),
                'usage_type': abuseData.get('usageType', 'Unknown'),
                'isp': abuseData.get('isp', ''),
                'domain': abuseData.get('domain', ''),
                'is_whitelisted': abuseData.get('isWhitelisted', False),
                'timestamp': datetime.now().isoformat()
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking AbuseIPDB for {ip}: {e}")
            return {}

    def fetch_abuseipdb_blocklist(self) -> List[str]:
        """
        Fetch AbuseIPDB blacklist (IPs with high abuse scores).

        Returns:
            List of blocked IP addresses
        """
        if not ABUSEIPDB_API_KEY:
            logger.warning("ABUSEIPDB_API_KEY not set, skipping blocklist fetch")
            return []

        try:
            url = 'https://api.abuseipdb.com/api/v2/blacklist'
            headers = {
                'Key': ABUSEIPDB_API_KEY,
                'Accept': 'text/plain'
            }
            params = {
                'limit': 100000,
                'plaintext': ''
            }

            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            # Parse plaintext list
            ips = [line.strip() for line in response.text.split('\n')
                   if line.strip() and not line.startswith('#')]

            logger.info(f"Fetched {len(ips)} IPs from AbuseIPDB blacklist")
            return ips

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching AbuseIPDB blacklist: {e}")
            return []

    def fetch_spamhaus_drop_list(self) -> List[str]:
        """
        Fetch Spamhaus DROP (Don't Route Or Peer) list.

        Spamhaus maintains several lists:
        - DROP: Single IP addresses with highest confidence
        - EDROP: Extended DROP list

        Returns:
            List of blocked IP addresses/subnets
        """
        try:
            # Fetch DROP list
            drop_ips = self._fetch_spamhaus_list('https://www.spamhaus.org/drop/drop.txt')
            # Fetch EDROP list
            edrop_ips = self._fetch_spamhaus_list('https://www.spamhaus.org/drop/edrop.txt')

            combined = drop_ips + edrop_ips
            logger.info(f"Fetched {len(combined)} entries from Spamhaus (DROP + EDROP)")
            return combined

        except Exception as e:
            logger.error(f"Error fetching Spamhaus lists: {e}")
            return []

    def _fetch_spamhaus_list(self, url: str) -> List[str]:
        """
        Helper to fetch individual Spamhaus list.

        Args:
            url: URL to Spamhaus list

        Returns:
            List of IPs/subnets
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            entries = []
            for line in response.text.split('\n'):
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith(';'):
                    entries.append(line)

            return entries

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return []

    def update_abuseipdb_list(self) -> None:
        """Update and save AbuseIPDB blocklist."""
        logger.info("Updating AbuseIPDB blocklist...")
        ips = self.fetch_abuseipdb_blocklist()

        if ips:
            self.abuseipdb_ips = set(ips)
            with open(ABUSEIPDB_FILE, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'count': len(ips),
                    'ips': ips,
                    'source': 'abuseipdb',
                    'threshold': ABUSEIPDB_THRESHOLD
                }, f, indent=2)
            logger.info(f"Saved {len(ips)} IPs from AbuseIPDB")

    def update_spamhaus_list(self) -> None:
        """Update and save Spamhaus DROP/EDROP lists."""
        logger.info("Updating Spamhaus DROP/EDROP lists...")
        ips = self.fetch_spamhaus_drop_list()

        if ips:
            self.spamhaus_ips = set(ips)
            with open(SPAMHAUS_FILE, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'count': len(ips),
                    'entries': ips,
                    'source': 'spamhaus',
                    'lists': ['DROP', 'EDROP']
                }, f, indent=2)
            logger.info(f"Saved {len(ips)} entries from Spamhaus")

    def combine_blocklists(self) -> Set[str]:
        """
        Combine all blocklists into a single set.

        Returns:
            Set of all blocked IPs
        """
        # Load existing lists
        self.abuseipdb_ips = self._load_ip_list(ABUSEIPDB_FILE)
        self.spamhaus_ips = self._load_ip_list(SPAMHAUS_FILE)

        # Combine (exclude CIDR ranges for single IPs)
        combined = set()
        combined.update(ip for ip in self.abuseipdb_ips if '/' not in ip)
        combined.update(ip for ip in self.spamhaus_ips if '/' not in ip)

        self.combined_ips = combined

        # Save combined list
        with open(COMBINED_FILE, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_ips': len(combined),
                'abuseipdb_count': len(self.abuseipdb_ips),
                'spamhaus_count': len(self.spamhaus_ips),
                'ips': sorted(list(combined))
            }, f, indent=2)

        logger.info(f"Combined blocklist: {len(combined)} unique IPs")
        return combined

    def _load_ip_list(self, filepath: Path) -> Set[str]:
        """
        Load IP list from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            Set of IP addresses
        """
        if not filepath.exists():
            return set()

        try:
            with open(filepath) as f:
                data = json.load(f)
                ips = data.get('ips') or data.get('entries', [])
                return set(ips)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return set()

    def update_waf_ip_sets(self, project_name: str) -> None:
        """
        Update AWS WAF IP sets with current blocklists.

        Args:
            project_name: Project name for WAF naming
        """
        logger.info("Updating AWS WAF IP sets...")

        try:
            # Load combined blocklist
            combined = self.combine_blocklists()

            # Convert IPs to CIDR notation (single IPs need /32)
            ip_set_addresses = [f"{ip}/32" if '/' not in ip else ip
                              for ip in list(combined)[:10000]]  # WAF limit

            # Update AbuseIPDB IP set
            self._update_waf_ip_set(
                f"{project_name}-abuseipdb-ips",
                list(self.abuseipdb_ips)[:10000]
            )

            # Update Spamhaus IP set
            self._update_waf_ip_set(
                f"{project_name}-spamhaus-ips",
                list(self.spamhaus_ips)[:10000]
            )

            logger.info("AWS WAF IP sets updated successfully")

        except Exception as e:
            logger.error(f"Error updating WAF IP sets: {e}")

    def _update_waf_ip_set(self, ip_set_name: str, addresses: List[str]) -> None:
        """
        Update specific WAF IP set.

        Args:
            ip_set_name: Name of the IP set
            addresses: List of IP addresses
        """
        try:
            # Find IP set ID
            response = self.waf_client.list_ip_sets(Scope='REGIONAL')
            ip_set = None
            for item in response.get('IPSets', []):
                if item['Name'] == ip_set_name:
                    ip_set = item
                    break

            if not ip_set:
                logger.warning(f"IP set {ip_set_name} not found")
                return

            # Format addresses to CIDR notation
            formatted_addresses = [
                f"{addr}/32" if '/' not in addr else addr
                for addr in addresses
            ]

            # Update IP set
            self.waf_client.update_ip_set(
                Name=ip_set_name,
                Scope='REGIONAL',
                Id=ip_set['Id'],
                Addresses=set(formatted_addresses),
                LockToken=self.waf_client.get_ip_set(
                    Name=ip_set_name,
                    Scope='REGIONAL',
                    Id=ip_set['Id']
                )['LockToken']
            )

            logger.info(f"Updated {ip_set_name} with {len(addresses)} IPs")

        except Exception as e:
            logger.error(f"Error updating {ip_set_name}: {e}")

    def export_terraform_variables(self) -> str:
        """
        Export blocklists as Terraform variables.

        Returns:
            Terraform variable definitions
        """
        combined = self.combine_blocklists()

        # Convert to Terraform format
        terraform_vars = f'''
# Auto-generated IP reputation lists
# Generated: {datetime.now().isoformat()}
# Source: AbuseIPDB, Spamhaus

variable "abuseipdb_blocked_ips" {{
  description = "IPs blocked by AbuseIPDB (threshold > {ABUSEIPDB_THRESHOLD}%)"
  type        = list(string)
  default     = {json.dumps(sorted(list(self.abuseipdb_ips))[:10000])}
}}

variable "spamhaus_blocked_ips" {{
  description = "IPs from Spamhaus DROP/EDROP lists"
  type        = list(string)
  default     = {json.dumps(sorted(list(self.spamhaus_ips))[:10000])}
}}

variable "combined_blocked_ips" {{
  description = "Combined blocklist from all sources"
  type        = list(string)
  default     = {json.dumps(sorted(list(combined))[:10000])}
}}
'''
        return terraform_vars

    def check_ip(self, ip: str) -> Dict:
        """
        Comprehensive check of IP reputation.

        Args:
            ip: IP address to check

        Returns:
            Dictionary with reputation details
        """
        logger.info(f"Checking reputation for {ip}...")

        result = {
            'ip': ip,
            'checked_at': datetime.now().isoformat(),
            'sources': {}
        }

        # Check AbuseIPDB
        abuseipdb_result = self.check_abuseipdb(ip)
        if abuseipdb_result:
            result['sources']['abuseipdb'] = abuseipdb_result

        # Check if in local blocklists
        abuseipdb_ips = self._load_ip_list(ABUSEIPDB_FILE)
        spamhaus_ips = self._load_ip_list(SPAMHAUS_FILE)

        result['in_abuseipdb_list'] = ip in abuseipdb_ips
        result['in_spamhaus_list'] = ip in spamhaus_ips
        result['blocked'] = result['in_abuseipdb_list'] or result['in_spamhaus_list']

        return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='IP Reputation Checker and WAF Blocklist Manager'
    )
    parser.add_argument('--check', help='Check specific IP address')
    parser.add_argument('--update', action='store_true', help='Update all blocklists')
    parser.add_argument('--export', choices=['terraform', 'json'],
                       help='Export blocklists in specified format')
    parser.add_argument('--project', default='thebot',
                       help='Project name for WAF (default: thebot)')

    args = parser.parse_args()

    checker = IPReputationChecker()

    if args.check:
        result = checker.check_ip(args.check)
        print(json.dumps(result, indent=2))

    elif args.update:
        checker.update_abuseipdb_list()
        checker.update_spamhaus_list()
        checker.combine_blocklists()
        checker.update_waf_ip_sets(args.project)
        logger.info("Blocklist update completed successfully")

    elif args.export:
        if args.export == 'terraform':
            print(checker.export_terraform_variables())
        elif args.export == 'json':
            combined = checker.combine_blocklists()
            print(json.dumps(
                {
                    'timestamp': datetime.now().isoformat(),
                    'total_ips': len(combined),
                    'ips': sorted(list(combined))
                },
                indent=2
            ))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
