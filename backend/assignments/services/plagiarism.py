"""
T_ASSIGN_014: Plagiarism detection service client.

Provides abstraction for plagiarism detection services (Turnitin, Copyscape, etc.).
Handles submission, polling for results, and result retrieval.

Services:
- Turnitin: Real-time plagiarism detection with comprehensive source matching
- Copyscape: Web content comparison
- Custom: Internal/mock implementation for testing
"""
import logging
import requests
import time
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, Dict, List
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class PlagiarismServiceBase(ABC):
    """
    Abstract base class for plagiarism detection services.

    Each service implementation must provide:
    - submit_for_checking: Submit text for plagiarism detection
    - get_results: Poll/retrieve detection results
    - parse_response: Convert service response to standard format
    """

    def __init__(self, service_name: str, api_key: str = None):
        """
        Initialize plagiarism service client.

        Args:
            service_name: Name of the service (turnitin, copyscape, etc.)
            api_key: API key for the service (from settings if not provided)
        """
        self.service_name = service_name
        self.api_key = api_key or getattr(settings, f'{service_name.upper()}_API_KEY', None)
        self.timeout = 30  # seconds for API requests

    @abstractmethod
    def submit_for_checking(self, text: str, filename: str = None) -> Optional[str]:
        """
        Submit text for plagiarism checking.

        Args:
            text: The text to check for plagiarism
            filename: Optional filename for reference

        Returns:
            report_id: Unique ID from the service for tracking, or None if failed
        """
        pass

    @abstractmethod
    def get_results(self, report_id: str, max_wait_seconds: int = 86400) -> Optional[Dict]:
        """
        Get plagiarism detection results.

        Args:
            report_id: Service's report ID from submission
            max_wait_seconds: Maximum time to wait for results (default 24 hours)

        Returns:
            Dictionary with:
            - similarity_score: Decimal (0-100)
            - sources: List of dicts with source info
            - status: 'completed' or 'processing'
            Or None if check failed
        """
        pass

    def parse_response(self, response_data: Dict) -> Optional[Dict]:
        """
        Parse service response into standard format.

        Override in subclasses for service-specific formats.

        Returns:
            {
                'similarity_score': Decimal,
                'sources': [
                    {'source': str, 'match_percent': Decimal, 'matched_text': str},
                    ...
                ]
            }
        """
        return response_data


class TurnitinClient(PlagiarismServiceBase):
    """
    Turnitin plagiarism detection client.

    Integrates with Turnitin API v2:
    - Submits assignments for checking
    - Polls for completion (checks every 5 seconds, timeout 24 hours)
    - Retrieves comprehensive similarity reports
    """

    def __init__(self):
        super().__init__('turnitin', settings.TURNITIN_API_KEY if hasattr(settings, 'TURNITIN_API_KEY') else None)
        self.base_url = getattr(settings, 'TURNITIN_API_URL', 'https://api.turnitin.com/v2')
        self.webhook_signature_secret = getattr(settings, 'TURNITIN_WEBHOOK_SECRET', None)

    def submit_for_checking(self, text: str, filename: str = None) -> Optional[str]:
        """
        Submit assignment to Turnitin for plagiarism checking.

        Args:
            text: Assignment text content
            filename: Optional filename

        Returns:
            report_id or None if submission failed
        """
        if not self.api_key:
            logger.error("Turnitin API key not configured")
            return None

        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            data = {
                'submission_type': 'text',
                'content': text,
                'title': filename or 'Assignment Submission',
                'pdf_report': True,
            }

            response = requests.post(
                f'{self.base_url}/submissions',
                json=data,
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code == 201:
                result = response.json()
                report_id = result.get('id')
                logger.info(f"Turnitin submission created: {report_id}")
                return report_id
            else:
                logger.error(f"Turnitin submission failed: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"Turnitin submission error: {e}")
            return None

    def get_results(self, report_id: str, max_wait_seconds: int = 86400) -> Optional[Dict]:
        """
        Poll Turnitin for plagiarism detection results.

        Checks every 5 seconds until completion or timeout.

        Args:
            report_id: Turnitin submission ID
            max_wait_seconds: Maximum wait time (default 24 hours)

        Returns:
            Parsed results or None if failed
        """
        if not self.api_key:
            logger.error("Turnitin API key not configured")
            return None

        start_time = time.time()
        poll_interval = 5  # seconds between polls
        max_polls = max_wait_seconds // poll_interval

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        for attempt in range(max_polls):
            try:
                response = requests.get(
                    f'{self.base_url}/submissions/{report_id}',
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')

                    if status == 'COMPLETE':
                        # Fetch detailed similarity report
                        report_data = self._get_detailed_report(report_id, headers)
                        return report_data

                    elif status == 'ERROR':
                        logger.error(f"Turnitin processing error: {data.get('error')}")
                        return None

                    # Still processing, wait and retry
                    time.sleep(poll_interval)

            except requests.RequestException as e:
                logger.error(f"Turnitin polling error: {e}")
                if attempt < max_polls - 1:
                    time.sleep(poll_interval)
                continue

        logger.warning(f"Turnitin check timeout for report {report_id}")
        return None

    def _get_detailed_report(self, report_id: str, headers: Dict) -> Optional[Dict]:
        """
        Fetch detailed similarity report from Turnitin.

        Returns parsed similarity score and sources.
        """
        try:
            response = requests.get(
                f'{self.base_url}/submissions/{report_id}/similarity',
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return self.parse_response(data)
            else:
                logger.error(f"Failed to get similarity report: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"Error fetching detailed report: {e}")
            return None

    def parse_response(self, response_data: Dict) -> Optional[Dict]:
        """
        Parse Turnitin similarity response.

        Turnitin response format:
        {
            'overall_match_percentage': 25,
            'internet_match_percentage': 10,
            'publication_match_percentage': 5,
            'student_match_percentage': 10,
            'similarity_by_source': [
                {'name': 'source.com', 'similarity_percentage': 25, ...}
            ]
        }
        """
        try:
            similarity = Decimal(str(response_data.get('overall_match_percentage', 0)))
            sources = []

            for source in response_data.get('similarity_by_source', []):
                sources.append({
                    'source': source.get('name', 'Unknown'),
                    'match_percent': Decimal(str(source.get('similarity_percentage', 0))),
                    'matched_text': source.get('excluded_match_text', '')
                })

            return {
                'similarity_score': similarity,
                'sources': sources
            }
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Turnitin response: {e}")
            return None


class CopyscapeClient(PlagiarismServiceBase):
    """
    Copyscape plagiarism detection client (API format placeholder).

    In a real implementation, would integrate with Copyscape API.
    Current version shows expected interface.
    """

    def __init__(self):
        super().__init__('copyscape', settings.COPYSCAPE_API_KEY if hasattr(settings, 'COPYSCAPE_API_KEY') else None)
        self.base_url = getattr(settings, 'COPYSCAPE_API_URL', 'https://www.copyscape.com/api/')

    def submit_for_checking(self, text: str, filename: str = None) -> Optional[str]:
        """Submit to Copyscape for web content plagiarism check."""
        if not self.api_key:
            logger.error("Copyscape API key not configured")
            return None

        # Copyscape API integration would go here
        logger.info("Copyscape submission - not fully implemented")
        return None

    def get_results(self, report_id: str, max_wait_seconds: int = 86400) -> Optional[Dict]:
        """Poll Copyscape for results."""
        logger.info("Copyscape polling - not fully implemented")
        return None


class CustomPlagiarismClient(PlagiarismServiceBase):
    """
    Custom/Mock plagiarism detection client for testing and development.

    Simulates plagiarism detection with configurable results.
    Used when external services are unavailable.
    """

    def __init__(self):
        super().__init__('custom')

    def submit_for_checking(self, text: str, filename: str = None) -> Optional[str]:
        """
        Create mock plagiarism check in cache.

        For development/testing: returns a mock report ID.
        In production, would use internal plagiarism detection.
        """
        import uuid
        report_id = str(uuid.uuid4())

        # Simulate processing with mock results
        # In real implementation, would calculate actual similarity
        mock_results = {
            'similarity_score': Decimal('15.5'),
            'sources': [
                {
                    'source': 'https://example.com/article-1',
                    'match_percent': Decimal('8.2'),
                    'matched_text': 'Some matching text from source'
                },
                {
                    'source': 'https://example.com/article-2',
                    'match_percent': Decimal('7.3'),
                    'matched_text': 'More matching text'
                }
            ]
        }

        cache.set(f'plagiarism_check_{report_id}', mock_results, 86400)  # 24 hours
        logger.info(f"Custom plagiarism check created: {report_id}")
        return report_id

    def get_results(self, report_id: str, max_wait_seconds: int = 86400) -> Optional[Dict]:
        """
        Retrieve mock plagiarism check results from cache.

        Simulates 100% completion (no polling needed).
        """
        results = cache.get(f'plagiarism_check_{report_id}')
        if results:
            logger.info(f"Custom plagiarism check results retrieved: {report_id}")
            return results
        else:
            logger.warning(f"Custom plagiarism check not found: {report_id}")
            return None


class PlagiarismDetectionFactory:
    """
    Factory for creating plagiarism detection service clients.

    Selects appropriate service based on configuration.
    """

    _services = {
        'turnitin': TurnitinClient,
        'copyscape': CopyscapeClient,
        'custom': CustomPlagiarismClient,
    }

    @classmethod
    def get_client(cls, service_name: str = None) -> PlagiarismServiceBase:
        """
        Get plagiarism detection client.

        Args:
            service_name: Service to use (default from settings)

        Returns:
            PlagiarismServiceBase implementation
        """
        if service_name is None:
            service_name = getattr(settings, 'PLAGIARISM_SERVICE', 'custom').lower()

        service_class = cls._services.get(service_name, CustomPlagiarismClient)
        return service_class()

    @classmethod
    def register_service(cls, name: str, service_class: type):
        """Register a custom plagiarism service."""
        cls._services[name] = service_class
        logger.info(f"Registered plagiarism service: {name}")
