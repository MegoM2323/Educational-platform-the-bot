"""
T_ASSIGN_013: Assignment caching module.

Provides cache management for:
- Assignment statistics (T_ASSIGN_013)
- Cache invalidation signals
- Cache warming strategies
"""

from .stats import AssignmentStatsCache

__all__ = ['AssignmentStatsCache']
