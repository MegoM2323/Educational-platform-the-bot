"""
Signal handlers for cache invalidation.

Automatically invalidates caches when models are saved or deleted to ensure
data consistency across the application. Supports:
- Model-level invalidation (when specific models change)
- User-level invalidation (when user data changes)
- Global invalidation (for system-wide changes)
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class CacheInvalidationStrategy:
    """Define cache invalidation strategies for different model types."""

    @staticmethod
    def invalidate_material_cache(material_id: int):
        """Invalidate caches when a material is modified."""
        from config.cache import CacheKeyBuilder

        keys_to_delete = [
            CacheKeyBuilder.make_key('materials', 'list'),
            CacheKeyBuilder.make_key('material', material_id),
            CacheKeyBuilder.make_key('material_detail', material_id),
            CacheKeyBuilder.make_key('material', 'progress', material_id),
        ]

        for key in keys_to_delete:
            try:
                cache.delete(key)
                logger.debug(f'Invalidated cache key: {key}')
            except Exception as e:
                logger.warning(f'Error deleting cache key {key}: {e}')

    @staticmethod
    def invalidate_subject_cache(subject_id: int):
        """Invalidate caches when a subject is modified."""
        from config.cache import CacheKeyBuilder

        keys_to_delete = [
            CacheKeyBuilder.make_key('subjects', 'list'),
            CacheKeyBuilder.make_key('subject', subject_id),
        ]

        for key in keys_to_delete:
            try:
                cache.delete(key)
                logger.debug(f'Invalidated cache key: {key}')
            except Exception as e:
                logger.warning(f'Error deleting cache key {key}: {e}')

    @staticmethod
    def invalidate_user_dashboard_cache(user_id: int):
        """Invalidate user dashboard cache."""
        from config.cache import CacheKeyBuilder

        keys_to_delete = [
            CacheKeyBuilder.user_key('dashboard', user_id),
            CacheKeyBuilder.user_key('notifications', user_id),
            CacheKeyBuilder.user_key('progress', user_id),
        ]

        for key in keys_to_delete:
            try:
                cache.delete(key)
                logger.debug(f'Invalidated user cache key: {key}')
            except Exception as e:
                logger.warning(f'Error deleting cache key {key}: {e}')

    @staticmethod
    def invalidate_assignment_cache(assignment_id: int):
        """Invalidate caches when an assignment is modified."""
        from config.cache import CacheKeyBuilder

        keys_to_delete = [
            CacheKeyBuilder.make_key('assignments', 'list'),
            CacheKeyBuilder.make_key('assignment', assignment_id),
            CacheKeyBuilder.make_key('assignment', 'submissions', assignment_id),
        ]

        for key in keys_to_delete:
            try:
                cache.delete(key)
                logger.debug(f'Invalidated cache key: {key}')
            except Exception as e:
                logger.warning(f'Error deleting cache key {key}: {e}')

    @staticmethod
    def invalidate_chat_cache():
        """Invalidate chat-related caches."""
        from config.cache import CacheKeyBuilder

        keys_to_delete = [
            CacheKeyBuilder.make_key('chat', 'rooms'),
            CacheKeyBuilder.make_key('chat', 'messages'),
        ]

        for key in keys_to_delete:
            try:
                cache.delete(key)
                logger.debug(f'Invalidated cache key: {key}')
            except Exception as e:
                logger.warning(f'Error deleting cache key {key}: {e}')


# ============================================================================
# Django Signals for Cache Invalidation
# ============================================================================


def connect_cache_invalidation_signals():
    """
    Register all cache invalidation signals.

    This should be called in the AppConfig.ready() method of each app.
    """
    pass  # Signals are registered below using decorators


# Materials signals
try:
    from materials.models import Material, Subject

    @receiver(post_save, sender=Material)
    def invalidate_material_on_save(sender, instance, created, **kwargs):
        """Invalidate material cache when saved."""
        try:
            CacheInvalidationStrategy.invalidate_material_cache(instance.id)
            if instance.subject:
                CacheInvalidationStrategy.invalidate_subject_cache(instance.subject.id)
        except Exception as e:
            logger.warning(f'Error in invalidate_material_on_save: {e}')

    @receiver(post_delete, sender=Material)
    def invalidate_material_on_delete(sender, instance, **kwargs):
        """Invalidate material cache when deleted."""
        try:
            CacheInvalidationStrategy.invalidate_material_cache(instance.id)
            if instance.subject:
                CacheInvalidationStrategy.invalidate_subject_cache(instance.subject.id)
        except Exception as e:
            logger.warning(f'Error in invalidate_material_on_delete: {e}')

    @receiver(post_save, sender=Subject)
    def invalidate_subject_on_save(sender, instance, created, **kwargs):
        """Invalidate subject cache when saved."""
        try:
            CacheInvalidationStrategy.invalidate_subject_cache(instance.id)
        except Exception as e:
            logger.warning(f'Error in invalidate_subject_on_save: {e}')

    @receiver(post_delete, sender=Subject)
    def invalidate_subject_on_delete(sender, instance, **kwargs):
        """Invalidate subject cache when deleted."""
        try:
            CacheInvalidationStrategy.invalidate_subject_cache(instance.id)
        except Exception as e:
            logger.warning(f'Error in invalidate_subject_on_delete: {e}')

except ImportError:
    logger.debug('Materials app not available for signal registration')


# User signals
try:
    from django.contrib.auth import get_user_model

    User = get_user_model()

    @receiver(post_save, sender=User)
    def invalidate_user_cache_on_save(sender, instance, created, **kwargs):
        """Invalidate user cache when user is updated."""
        try:
            CacheInvalidationStrategy.invalidate_user_dashboard_cache(instance.id)
        except Exception as e:
            logger.warning(f'Error in invalidate_user_cache_on_save: {e}')

except ImportError:
    logger.debug('User model not available for signal registration')


# Assignments signals
try:
    from assignments.models import Assignment

    @receiver(post_save, sender=Assignment)
    def invalidate_assignment_on_save(sender, instance, created, **kwargs):
        """Invalidate assignment cache when saved."""
        try:
            CacheInvalidationStrategy.invalidate_assignment_cache(instance.id)
        except Exception as e:
            logger.warning(f'Error in invalidate_assignment_on_save: {e}')

    @receiver(post_delete, sender=Assignment)
    def invalidate_assignment_on_delete(sender, instance, **kwargs):
        """Invalidate assignment cache when deleted."""
        try:
            CacheInvalidationStrategy.invalidate_assignment_cache(instance.id)
        except Exception as e:
            logger.warning(f'Error in invalidate_assignment_on_delete: {e}')

except ImportError:
    logger.debug('Assignments app not available for signal registration')


# Chat signals
try:
    from chat.models import ChatRoom, Message

    @receiver(post_save, sender=ChatRoom)
    def invalidate_chat_on_room_save(sender, instance, created, **kwargs):
        """Invalidate chat cache when room is modified."""
        try:
            CacheInvalidationStrategy.invalidate_chat_cache()
        except Exception as e:
            logger.warning(f'Error in invalidate_chat_on_room_save: {e}')

    @receiver(post_save, sender=Message)
    def invalidate_chat_on_message_save(sender, instance, created, **kwargs):
        """Invalidate chat cache when message is created."""
        try:
            CacheInvalidationStrategy.invalidate_chat_cache()
        except Exception as e:
            logger.warning(f'Error in invalidate_chat_on_message_save: {e}')

except ImportError:
    logger.debug('Chat app not available for signal registration')
