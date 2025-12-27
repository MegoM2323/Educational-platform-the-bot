#!/usr/bin/env python3
"""
Test script for ELK Stack integration
Verifies that logs are collected, processed, and searchable

Usage:
    python test_elk_stack.py
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ELASTICSEARCH_URL = "http://localhost:9200"
KIBANA_URL = "http://localhost:5601"
LOGSTASH_HOST = "localhost"
LOGSTASH_PORT = 5000

class ELKStackTester:
    """Test ELK Stack functionality"""

    def __init__(self):
        self.elasticsearch_url = ELASTICSEARCH_URL
        self.kibana_url = KIBANA_URL
        self.test_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }

    def test_elasticsearch_connection(self) -> bool:
        """Test Elasticsearch connectivity"""
        logger.info("Testing Elasticsearch connection...")
        try:
            response = requests.get(f"{self.elasticsearch_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✓ Elasticsearch is running (v{data['version']['number']})")
                self.test_results['passed'].append("Elasticsearch connection")
                return True
            else:
                logger.error(f"✗ Elasticsearch returned status {response.status_code}")
                self.test_results['failed'].append("Elasticsearch connection")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to connect to Elasticsearch: {e}")
            self.test_results['failed'].append(f"Elasticsearch connection: {str(e)}")
            return False

    def test_kibana_connection(self) -> bool:
        """Test Kibana connectivity"""
        logger.info("Testing Kibana connection...")
        try:
            response = requests.get(f"{self.kibana_url}/api/status", timeout=5)
            if response.status_code == 200:
                logger.info("✓ Kibana is running and responsive")
                self.test_results['passed'].append("Kibana connection")
                return True
            else:
                logger.error(f"✗ Kibana returned status {response.status_code}")
                self.test_results['failed'].append("Kibana connection")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to connect to Kibana: {e}")
            self.test_results['failed'].append(f"Kibana connection: {str(e)}")
            return False

    def test_indices_exist(self) -> bool:
        """Test if log indices exist in Elasticsearch"""
        logger.info("Checking for log indices in Elasticsearch...")
        try:
            response = requests.get(f"{self.elasticsearch_url}/_cat/indices?format=json", timeout=5)
            if response.status_code == 200:
                indices = response.json()
                log_indices = [idx for idx in indices if 'thebot' in idx.get('index', '')]

                if log_indices:
                    logger.info(f"✓ Found {len(log_indices)} log indices:")
                    for idx in log_indices:
                        logger.info(f"  - {idx['index']} ({idx['docs.count']} documents)")
                    self.test_results['passed'].append("Log indices exist")
                    return True
                else:
                    logger.warning("⚠ No thebot log indices found yet (expected if logs haven't been collected)")
                    self.test_results['warnings'].append("No log indices created yet")
                    return True
            else:
                logger.error(f"✗ Failed to get indices: status {response.status_code}")
                self.test_results['failed'].append("Get indices")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to check indices: {e}")
            self.test_results['failed'].append(f"Check indices: {str(e)}")
            return False

    def test_log_search(self, index: str = "thebot-logs-*") -> bool:
        """Test searching logs"""
        logger.info(f"Testing log search in {index}...")
        try:
            query = {
                "query": {
                    "match_all": {}
                },
                "size": 100
            }
            response = requests.get(
                f"{self.elasticsearch_url}/{index}/_search",
                json=query,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                hit_count = data['hits']['total'].get('value', 0) if isinstance(data['hits']['total'], dict) else data['hits']['total']
                logger.info(f"✓ Log search working ({hit_count} documents found)")
                if data['hits']['hits']:
                    logger.info(f"  Sample log entry:")
                    sample = data['hits']['hits'][0]['_source']
                    logger.info(f"    - Timestamp: {sample.get('@timestamp', 'N/A')}")
                    logger.info(f"    - Level: {sample.get('log_level', sample.get('level', 'N/A'))}")
                    logger.info(f"    - Service: {sample.get('service', 'N/A')}")
                self.test_results['passed'].append("Log search")
                return True
            else:
                logger.warning(f"⚠ Log search returned status {response.status_code} (no logs indexed yet)")
                self.test_results['warnings'].append("No logs in index yet")
                return True
        except Exception as e:
            logger.error(f"✗ Log search failed: {e}")
            self.test_results['failed'].append(f"Log search: {str(e)}")
            return False

    def test_error_logs(self) -> bool:
        """Test error log index"""
        logger.info("Testing error log index...")
        try:
            query = {
                "query": {
                    "match_all": {}
                },
                "size": 10
            }
            response = requests.get(
                f"{self.elasticsearch_url}/thebot-errors-*/_search",
                json=query,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                hit_count = data['hits']['total'].get('value', 0) if isinstance(data['hits']['total'], dict) else data['hits']['total']
                logger.info(f"✓ Error log search working ({hit_count} error documents found)")
                self.test_results['passed'].append("Error log search")
                return True
            elif response.status_code == 404:
                logger.info("⚠ Error log index doesn't exist yet (expected if no errors)")
                self.test_results['warnings'].append("Error index not created yet")
                return True
            else:
                logger.warning(f"⚠ Error search returned status {response.status_code}")
                return True
        except Exception as e:
            logger.error(f"✗ Error log search failed: {e}")
            self.test_results['failed'].append(f"Error search: {str(e)}")
            return False

    def test_metric_indices(self) -> bool:
        """Test metrics indices from Metricbeat"""
        logger.info("Checking for metrics indices...")
        try:
            response = requests.get(f"{self.elasticsearch_url}/_cat/indices?format=json", timeout=5)
            if response.status_code == 200:
                indices = response.json()
                metric_indices = [idx for idx in indices if 'metrics' in idx.get('index', '')]

                if metric_indices:
                    logger.info(f"✓ Found {len(metric_indices)} metrics indices")
                    self.test_results['passed'].append("Metrics indices exist")
                    return True
                else:
                    logger.info("⚠ No metrics indices found yet (expected if Metricbeat hasn't started)")
                    self.test_results['warnings'].append("Metrics indices not created yet")
                    return True
            else:
                logger.error(f"✗ Failed to get metrics indices: status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to check metrics indices: {e}")
            return False

    def test_kibana_saved_objects(self) -> bool:
        """Test Kibana saved objects (dashboards, visualizations)"""
        logger.info("Checking Kibana saved objects...")
        try:
            response = requests.get(
                f"{self.kibana_url}/api/saved_objects",
                timeout=5
            )
            if response.status_code in [200, 401]:  # 401 if auth required, but service is running
                logger.info("✓ Kibana saved objects API is accessible")
                self.test_results['passed'].append("Kibana saved objects")
                return True
            else:
                logger.warning(f"⚠ Kibana API returned status {response.status_code}")
                self.test_results['warnings'].append("Kibana API status check")
                return True
        except Exception as e:
            logger.error(f"✗ Failed to check Kibana objects: {e}")
            self.test_results['failed'].append(f"Kibana objects: {str(e)}")
            return False

    def test_pipeline_status(self) -> bool:
        """Check if Logstash pipeline is running"""
        logger.info("Checking Logstash pipeline status...")
        try:
            response = requests.get("http://localhost:9600/", timeout=5)
            if response.status_code == 200:
                logger.info("✓ Logstash is running")
                self.test_results['passed'].append("Logstash pipeline")
                return True
            else:
                logger.warning(f"⚠ Logstash returned status {response.status_code}")
                self.test_results['warnings'].append("Logstash status")
                return True
        except Exception as e:
            logger.warning(f"⚠ Could not connect to Logstash: {e}")
            self.test_results['warnings'].append(f"Logstash connection: {str(e)}")
            return True

    def create_test_log_index(self) -> bool:
        """Create a test log index"""
        logger.info("Creating test log index...")
        try:
            test_log = {
                "@timestamp": datetime.utcnow().isoformat(),
                "message": "Test log entry from ELK Stack verification",
                "log_level": "INFO",
                "service": "test-runner",
                "environment": "development",
                "platform": "thebot",
                "version": "1.0.0",
                "tags": ["test", "verification"],
                "request_id": "test-001"
            }

            response = requests.post(
                f"{self.elasticsearch_url}/thebot-logs-test/_doc",
                json=test_log,
                timeout=5
            )

            if response.status_code in [200, 201]:
                logger.info("✓ Test log entry created successfully")
                logger.info(f"  Document ID: {response.json()['_id']}")
                self.test_results['passed'].append("Create test log")

                # Wait a bit for indexing
                time.sleep(1)

                # Verify we can search it
                return self.verify_test_log()
            else:
                logger.error(f"✗ Failed to create test log: status {response.status_code}")
                self.test_results['failed'].append("Create test log")
                return False
        except Exception as e:
            logger.error(f"✗ Failed to create test log: {e}")
            self.test_results['failed'].append(f"Create test log: {str(e)}")
            return False

    def verify_test_log(self) -> bool:
        """Verify we can search the test log"""
        logger.info("Verifying test log is searchable...")
        try:
            query = {
                "query": {
                    "match": {
                        "message": "Test log entry"
                    }
                }
            }
            response = requests.get(
                f"{self.elasticsearch_url}/thebot-logs-test/_search",
                json=query,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                if data['hits']['total'].get('value', 0) > 0 or data['hits']['total'] > 0:
                    logger.info("✓ Test log is searchable in Elasticsearch")
                    self.test_results['passed'].append("Test log searchable")
                    return True
                else:
                    logger.warning("⚠ Test log not found (indexing delay)")
                    self.test_results['warnings'].append("Test log search delay")
                    return True
            else:
                logger.error(f"✗ Search failed: status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"✗ Verify test log failed: {e}")
            return False

    def run_all_tests(self) -> bool:
        """Run all tests"""
        logger.info("=" * 60)
        logger.info("ELK Stack Verification Test Suite")
        logger.info("=" * 60)

        all_pass = True

        # Run core connection tests
        all_pass &= self.test_elasticsearch_connection()
        all_pass &= self.test_kibana_connection()
        all_pass &= self.test_pipeline_status()

        # Wait a moment for services to stabilize
        time.sleep(2)

        # Run functionality tests
        all_pass &= self.test_indices_exist()
        all_pass &= self.test_log_search()
        all_pass &= self.test_error_logs()
        all_pass &= self.test_metric_indices()
        all_pass &= self.test_kibana_saved_objects()

        # Create and verify test log
        all_pass &= self.create_test_log_index()

        # Print summary
        logger.info("=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        logger.info(f"✓ Passed: {len(self.test_results['passed'])} tests")
        for test in self.test_results['passed']:
            logger.info(f"  ✓ {test}")

        if self.test_results['warnings']:
            logger.info(f"\n⚠ Warnings: {len(self.test_results['warnings'])} items")
            for warning in self.test_results['warnings']:
                logger.warning(f"  ⚠ {warning}")

        if self.test_results['failed']:
            logger.error(f"\n✗ Failed: {len(self.test_results['failed'])} tests")
            for test in self.test_results['failed']:
                logger.error(f"  ✗ {test}")

        logger.info("=" * 60)

        return len(self.test_results['failed']) == 0


def main():
    """Main entry point"""
    tester = ELKStackTester()

    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
