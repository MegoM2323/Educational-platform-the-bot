"""
T_ASSIGN_013: Assignment signals module.

Provides signal handlers for:
- Cache invalidation on submission/grade changes
- Cache invalidation on peer review changes
"""

from .cache_invalidation import register_peer_review_signals

__all__ = ['register_peer_review_signals']
