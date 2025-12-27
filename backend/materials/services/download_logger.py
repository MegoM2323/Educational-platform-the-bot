"""
Material Download Logging Service

Handles download tracking, deduplication, rate limiting, and statistics.
"""

from datetime import timedelta
from typing import Optional, Dict, Any

from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from django.core.cache import cache

from materials.models import MaterialDownloadLog, Material


class DownloadLogger:
    """
    Service for tracking material downloads with deduplication and rate limiting.
    """

    # Rate limiting: max downloads per IP per hour
    RATE_LIMIT_PER_HOUR = 100
    DEDUP_WINDOW_MINUTES = 60

    @staticmethod
    def get_client_ip(request) -> str:
        """
        Extract client IP address from request.

        Checks X-Forwarded-For header first (for proxies), then REMOTE_ADDR.

        Args:
            request: HTTP request object

        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def check_rate_limit(ip_address: str) -> bool:
        """
        Check if IP has exceeded download rate limit.

        Uses cache to track downloads per IP per hour.
        Limit: 100 downloads per IP per hour

        Args:
            ip_address: Client IP address

        Returns:
            bool: True if within limit, False if exceeded
        """
        cache_key = f"download_rate_limit_{ip_address}"
        current_count = cache.get(cache_key, 0)

        if current_count >= DownloadLogger.RATE_LIMIT_PER_HOUR:
            return False

        cache.set(cache_key, current_count + 1, 3600)  # 1 hour TTL
        return True

    @staticmethod
    def should_log_download(
        material_id: int,
        user_id: int,
        minutes: int = DEDUP_WINDOW_MINUTES
    ) -> bool:
        """
        Check if this download should be logged (deduplication).

        Returns False if user downloaded same material within N minutes
        (prevents double-counting accidental double-clicks, etc.)

        Args:
            material_id: Material ID
            user_id: User ID
            minutes: Deduplication window (default 60 minutes)

        Returns:
            bool: True if should log, False if duplicate
        """
        return MaterialDownloadLog.should_log(
            material_id=material_id,
            user_id=user_id,
            minutes=minutes
        )

    @staticmethod
    def log_download(
        material: Material,
        user: Any,
        request: Any,
        file_size: Optional[int] = None
    ) -> MaterialDownloadLog:
        """
        Log a material download with metadata.

        Args:
            material: Material instance
            user: User instance
            request: HTTP request object
            file_size: File size in bytes (optional)

        Returns:
            MaterialDownloadLog: Created log entry

        Raises:
            ValueError: If file_size is negative
        """
        if file_size is not None and file_size < 0:
            raise ValueError("File size cannot be negative")

        ip_address = DownloadLogger.get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]  # Limit to 500 chars

        log_entry = MaterialDownloadLog.objects.create(
            material=material,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            file_size=file_size,
        )

        return log_entry

    @staticmethod
    def get_material_download_stats(material_id: int) -> Dict[str, Any]:
        """
        Get download statistics for a material.

        Returns total downloads and per-user data.

        Args:
            material_id: Material ID

        Returns:
            dict: Statistics including:
                - total_downloads: Total log entries
                - unique_users: Count of unique users
                - total_data_transferred: Sum of file sizes (bytes)
                - latest_download: Timestamp of last download
        """
        logs = MaterialDownloadLog.objects.filter(material_id=material_id)

        stats = {
            "total_downloads": logs.count(),
            "unique_users": logs.values("user_id").distinct().count(),
            "total_data_transferred": logs.aggregate(
                total=Sum("file_size")
            )["total"] or 0,
            "latest_download": logs.values_list("timestamp", flat=True).first(),
        }

        return stats

    @staticmethod
    def get_user_download_stats(user_id: int) -> Dict[str, Any]:
        """
        Get download statistics for a user.

        Returns download count and data transferred.

        Args:
            user_id: User ID

        Returns:
            dict: Statistics including:
                - total_downloads: Total downloads by user
                - total_data_transferred: Total data downloaded (bytes)
                - materials_downloaded: Count of unique materials
                - latest_download: Timestamp of last download
        """
        logs = MaterialDownloadLog.objects.filter(user_id=user_id)

        stats = {
            "total_downloads": logs.count(),
            "total_data_transferred": logs.aggregate(
                total=Sum("file_size")
            )["total"] or 0,
            "materials_downloaded": logs.values("material_id").distinct().count(),
            "latest_download": logs.values_list("timestamp", flat=True).first(),
        }

        return stats

    @staticmethod
    def get_downloads_by_period(
        material_id: Optional[int] = None,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, int]:
        """
        Get download count by day for last N days.

        Args:
            material_id: Filter by material (optional)
            user_id: Filter by user (optional)
            days: Number of days to include (default 30)

        Returns:
            dict: Date -> download count mapping
        """
        from django.db.models.functions import TruncDate

        cutoff_date = timezone.now() - timedelta(days=days)

        query = MaterialDownloadLog.objects.filter(
            timestamp__gte=cutoff_date
        )

        if material_id:
            query = query.filter(material_id=material_id)

        if user_id:
            query = query.filter(user_id=user_id)

        daily_counts = query.annotate(
            date=TruncDate("timestamp")
        ).values("date").annotate(
            count=Count("id")
        ).order_by("date")

        return {
            str(item["date"]): item["count"]
            for item in daily_counts
        }

    @staticmethod
    def get_top_materials(limit: int = 10, days: int = 30) -> list:
        """
        Get most downloaded materials in last N days.

        Args:
            limit: Number of materials to return (default 10)
            days: Time period (default 30 days)

        Returns:
            list: List of dicts with material and download count
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        materials = MaterialDownloadLog.objects.filter(
            timestamp__gte=cutoff_date
        ).values(
            "material_id",
            "material__title"
        ).annotate(
            download_count=Count("id")
        ).order_by("-download_count")[:limit]

        return list(materials)

    @staticmethod
    def cleanup_old_logs(days: int = 180) -> tuple:
        """
        Delete download logs older than N days.

        Args:
            days: Age threshold in days (default 180 = 6 months)

        Returns:
            tuple: (count, {'app.model': count}) from delete
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count, details = MaterialDownloadLog.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()

        return (deleted_count, details)
