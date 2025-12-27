"""
CDN Configuration Settings for THE_BOT Platform

This module provides CloudFront CDN configuration and utilities for:
- Static asset serving (JS, CSS, images)
- Media file serving (user uploads)
- Cache invalidation
- Signed URL generation for media files
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path
from urllib.parse import urljoin

# CloudFront Configuration
CDN_ENABLED = os.getenv("CDN_ENABLED", "True").lower() == "true"
CDN_PROVIDER = os.getenv("CDN_PROVIDER", "cloudfront")

# CloudFront Distribution Settings
CLOUDFRONT_DOMAIN = os.getenv(
    "CLOUDFRONT_DOMAIN",
    "d123456.cloudfront.net"  # Replace with actual distribution domain
)
CLOUDFRONT_DISTRIBUTION_ID = os.getenv(
    "CLOUDFRONT_DISTRIBUTION_ID",
    ""
)
CLOUDFRONT_KEY_GROUP_ID = os.getenv(
    "CLOUDFRONT_KEY_GROUP_ID",
    ""
)
CLOUDFRONT_PUBLIC_KEY_ID = os.getenv(
    "CLOUDFRONT_PUBLIC_KEY_ID",
    ""
)

# CloudFront Private Key for signing URLs
CLOUDFRONT_PRIVATE_KEY_PATH = os.getenv(
    "CLOUDFRONT_PRIVATE_KEY_PATH",
    "/etc/secrets/cloudfront-private-key.pem"
)

# Origin Authentication
CLOUDFRONT_ORIGIN_VERIFY_HEADER = "X-Origin-Verify"
CLOUDFRONT_ORIGIN_VERIFY_TOKEN = os.getenv(
    "CLOUDFRONT_ORIGIN_VERIFY_TOKEN",
    ""
)

# Cache Configuration
CACHE_CONTROL_HASHED_ASSETS = "public, max-age=31536000, immutable"  # 1 year
CACHE_CONTROL_STATIC_FILES = "public, max-age=2592000, must-revalidate"  # 30 days
CACHE_CONTROL_MEDIA_FILES = "public, max-age=604800, must-revalidate"  # 7 days
CACHE_CONTROL_HTML = "public, max-age=3600, must-revalidate"  # 1 hour

# Signed URL Configuration
SIGNED_URL_ENABLED = os.getenv("SIGNED_URL_ENABLED", "True").lower() == "true"
SIGNED_URL_TTL_SECONDS = int(os.getenv("SIGNED_URL_TTL_SECONDS", "3600"))  # 1 hour

# Static Files Configuration
STATIC_URL_CDN = os.getenv(
    "STATIC_URL_CDN",
    f"https://{CLOUDFRONT_DOMAIN}/static/" if CDN_ENABLED else "/static/"
)
STATIC_ROOT_LOCAL = os.path.join(Path(__file__).resolve().parent.parent, "staticfiles")

# Media Files Configuration
MEDIA_URL_CDN = os.getenv(
    "MEDIA_URL_CDN",
    f"https://{CLOUDFRONT_DOMAIN}/media/" if CDN_ENABLED else "/media/"
)
MEDIA_ROOT_LOCAL = os.path.join(Path(__file__).resolve().parent.parent, "media")

# Asset Hash Configuration (for cache busting)
ASSET_MANIFEST_FILE = os.path.join(STATIC_ROOT_LOCAL, "manifest.json")


class CDNConfig:
    """
    CDN Configuration Manager

    Handles CloudFront configuration, signed URL generation, and cache management.
    """

    def __init__(self):
        """Initialize CDN configuration."""
        self.enabled = CDN_ENABLED
        self.provider = CDN_PROVIDER
        self.domain = CLOUDFRONT_DOMAIN
        self.distribution_id = CLOUDFRONT_DISTRIBUTION_ID
        self.key_group_id = CLOUDFRONT_KEY_GROUP_ID
        self.public_key_id = CLOUDFRONT_PUBLIC_KEY_ID

    @property
    def is_configured(self) -> bool:
        """Check if CDN is properly configured."""
        if not self.enabled:
            return False

        required_settings = [
            self.domain,
            self.distribution_id,
        ]

        # For media file signing, also check signing configuration
        if SIGNED_URL_ENABLED:
            required_settings.extend([
                self.public_key_id,
                CLOUDFRONT_PRIVATE_KEY_PATH,
            ])

        return all(required_settings)

    def get_static_url(self, path: str) -> str:
        """
        Get CDN URL for static asset.

        Args:
            path: Asset path (e.g., "js/app.js", "images/logo.png")

        Returns:
            Full CDN URL for the asset
        """
        if not self.enabled:
            return f"/static/{path.lstrip('/')}"

        return urljoin(STATIC_URL_CDN, path)

    def get_media_url(self, path: str, sign: bool = True) -> str:
        """
        Get CDN URL for media file (user upload).

        For media files, use signed URLs for security.

        Args:
            path: Media file path (e.g., "uploads/user_123/file.pdf")
            sign: Whether to generate a signed URL (default: True)

        Returns:
            Full CDN URL for the media file (signed if enabled)
        """
        if not self.enabled:
            return f"/media/{path.lstrip('/')}"

        url = urljoin(MEDIA_URL_CDN, path)

        if SIGNED_URL_ENABLED and sign:
            try:
                url = self.sign_url(url)
            except Exception as e:
                # Log error but return unsigned URL as fallback
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to sign media URL: {e}")

        return url

    def sign_url(self, url: str, expires_in: Optional[int] = None) -> str:
        """
        Generate signed URL for CloudFront media file access.

        Signed URLs ensure that only authenticated users can access media files.
        The URL includes a signature that validates:
        - The URL path
        - The expiration time
        - The CloudFront key pair ID

        Args:
            url: The URL to sign
            expires_in: Seconds until URL expires (default: SIGNED_URL_TTL_SECONDS)

        Returns:
            Signed URL with CloudFront signature query parameters

        Raises:
            ImportError: If required cryptography libraries are not installed
            ValueError: If private key cannot be loaded
            RuntimeError: If signing fails
        """
        if not SIGNED_URL_ENABLED:
            return url

        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            import base64
            import json
            from urllib.parse import urlencode
        except ImportError:
            raise ImportError(
                "Cryptography library required for signed URLs. "
                "Install: pip install cryptography"
            )

        # Load private key
        try:
            with open(CLOUDFRONT_PRIVATE_KEY_PATH, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend(),
                )
        except FileNotFoundError:
            raise ValueError(
                f"CloudFront private key not found: {CLOUDFRONT_PRIVATE_KEY_PATH}"
            )
        except Exception as e:
            raise ValueError(f"Failed to load private key: {e}")

        # Set expiration time
        if expires_in is None:
            expires_in = SIGNED_URL_TTL_SECONDS

        expires_at = int((datetime.utcnow() + timedelta(seconds=expires_in)).timestamp())

        # Create policy document
        policy = {
            "Statement": [
                {
                    "Resource": url,
                    "Condition": {
                        "DateLessThan": {
                            "AWS:EpochTime": expires_at
                        }
                    }
                }
            ]
        }

        policy_str = json.dumps(policy, separators=(',', ':'))

        # Encode policy
        policy_b64 = base64.b64encode(policy_str.encode('utf-8')).decode('utf-8')

        # Sign policy with private key
        signature = private_key.sign(
            policy_b64.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )

        # Encode signature
        signature_b64 = base64.b64encode(signature).decode('utf-8')

        # Fix URL encoding for CloudFront
        policy_b64_safe = policy_b64.replace('+', '-').replace('=', '_').replace('/', '~')
        signature_b64_safe = signature_b64.replace('+', '-').replace('=', '_').replace('/', '~')

        # Build signed URL with parameters
        params = {
            'Policy': policy_b64_safe,
            'Signature': signature_b64_safe,
            'Key-Pair-Id': self.public_key_id,
        }

        query_string = urlencode(params)
        separator = '&' if '?' in url else '?'

        return f"{url}{separator}{query_string}"

    def get_asset_hash(self, asset_path: str) -> Optional[str]:
        """
        Get hash of an asset for cache busting.

        Reads from asset manifest file generated during build.

        Args:
            asset_path: Asset path (e.g., "js/app.js")

        Returns:
            Asset hash if available, None otherwise
        """
        try:
            if not os.path.exists(ASSET_MANIFEST_FILE):
                return None

            with open(ASSET_MANIFEST_FILE, 'r') as f:
                manifest = json.load(f)

            return manifest.get(asset_path, {}).get('hash')
        except Exception:
            return None

    def invalidate_cache(
        self,
        paths: Optional[List[str]] = None,
        all_paths: bool = False
    ) -> Optional[str]:
        """
        Invalidate CloudFront cache for specified paths.

        This should typically be called after deployment to ensure users
        get the latest versions of assets.

        Args:
            paths: List of paths to invalidate (e.g., ["/static/*", "/index.html"])
            all_paths: If True, invalidate all paths (/*) - use with caution

        Returns:
            Invalidation request ID if successful, None otherwise

        Raises:
            RuntimeError: If CloudFront not properly configured
            Exception: If AWS API call fails
        """
        if not self.is_configured:
            raise RuntimeError("CloudFront not properly configured")

        if not self.distribution_id:
            raise RuntimeError("CLOUDFRONT_DISTRIBUTION_ID not set")

        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 library required for cache invalidation. "
                "Install: pip install boto3"
            )

        try:
            client = boto3.client('cloudfront')

            if all_paths:
                paths = ['/*']
            elif not paths:
                paths = ['/static/*', '/media/*']

            # AWS CloudFront limit: 3000 paths per invalidation request
            if len(paths) > 3000:
                raise ValueError(
                    f"Too many paths to invalidate: {len(paths)} > 3000 (AWS limit)"
                )

            response = client.create_invalidation(
                DistributionId=self.distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': len(paths),
                        'Items': paths,
                    },
                    'CallerReference': str(datetime.utcnow().timestamp()),
                }
            )

            return response['Invalidation']['Id']

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Cache invalidation failed: {e}")
            raise

    def get_cache_control_header(self, file_path: str) -> str:
        """
        Get appropriate Cache-Control header for file.

        Args:
            file_path: File path to determine cache strategy

        Returns:
            Cache-Control header value
        """
        # Check if file has hash in name (e.g., app-abc123.js)
        if any(f"-{c}" in file_path for c in "abcdef0123456789"):
            return CACHE_CONTROL_HASHED_ASSETS

        # HTML files - short TTL for quick updates
        if file_path.endswith('.html'):
            return CACHE_CONTROL_HTML

        # Static files - longer TTL
        if any(file_path.endswith(ext) for ext in ['.js', '.css', '.json', '.xml']):
            return CACHE_CONTROL_STATIC_FILES

        # Media files - medium TTL
        if any(file_path.endswith(ext) for ext in [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.png', '.jpg', '.jpeg', '.gif', '.svg',
            '.mp4', '.webm', '.mp3', '.wav'
        ]):
            return CACHE_CONTROL_MEDIA_FILES

        # Default
        return CACHE_CONTROL_STATIC_FILES

    @property
    def cache_hit_target(self) -> float:
        """Target cache hit rate (0-100%)."""
        return 90.0  # Aim for 90% cache hit rate

    @property
    def cost_optimization_tips(self) -> List[str]:
        """Tips for optimizing CDN costs."""
        return [
            "Use hash-based file names for automatic cache busting",
            "Enable compression (gzip/brotli) for text files",
            "Batch cache invalidations to minimize path cost",
            "Monitor cache hit rates and adjust TTLs",
            "Use CloudFront Functions instead of Lambda@Edge",
            "Combine small files to reduce number of requests",
            "Implement proper cache headers in origin",
            "Monitor data transfer costs and optimize asset sizes",
        ]


# Global CDN configuration instance
cdn_config = CDNConfig()


def get_cdn_config() -> CDNConfig:
    """Get global CDN configuration instance."""
    return cdn_config


def get_signed_media_url(path: str) -> str:
    """
    Helper function to get signed media URL.

    Usage in Django templates:
        {% load static %}
        <img src="{{ 'path/to/file.jpg'|signed_media_url }}" />

    Or in Python:
        from config.cdn_settings import get_signed_media_url
        url = get_signed_media_url('uploads/user_123/photo.jpg')

    Args:
        path: Media file path

    Returns:
        Signed media URL
    """
    return cdn_config.get_media_url(path, sign=True)


def get_static_url(path: str) -> str:
    """
    Helper function to get static asset URL.

    Args:
        path: Asset path

    Returns:
        Static asset URL (from CDN if enabled)
    """
    return cdn_config.get_static_url(path)
