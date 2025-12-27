"""
Django template tags for CDN asset URLs

Usage in templates:
    {% load cdn_tags %}

    <!-- Static assets with CDN support -->
    <link rel="stylesheet" href="{% cdn_url 'css/style.css' %}">
    <script src="{% cdn_url 'js/app.js' %}"></script>

    <!-- Media with signed URLs -->
    <a href="{% signed_media_url document.path %}">Download</a>
"""

from django import template
from config.cdn_settings import cdn_config

register = template.Library()


@register.simple_tag
def cdn_url(path: str) -> str:
    """
    Get CDN URL for static asset.

    Usage:
        {% cdn_url 'css/style.css' %}
        {% cdn_url 'js/app.js' %}

    Args:
        path: Asset path

    Returns:
        Full CDN URL (or local path if CDN disabled)
    """
    return cdn_config.get_static_url(path)


@register.simple_tag
def signed_media_url(path: str) -> str:
    """
    Get signed CDN URL for media file.

    Ensures secure access to user-uploaded media.

    Usage:
        {% signed_media_url document.file.name %}
        {% signed_media_url user_photo.path %}

    Args:
        path: Media file path

    Returns:
        Signed CDN URL with CloudFront signature
    """
    return cdn_config.get_media_url(path, sign=True)


@register.simple_tag
def media_url(path: str) -> str:
    """
    Get unsigned CDN URL for media file.

    Usually combined with signed_media_url. Use only for public media.

    Usage:
        {% media_url public_file.path %}

    Args:
        path: Media file path

    Returns:
        CDN URL without signature
    """
    return cdn_config.get_media_url(path, sign=False)


@register.filter
def with_cdn_url(path: str) -> str:
    """
    Filter to convert asset path to CDN URL.

    Usage:
        {{ 'css/style.css'|with_cdn_url }}

    Args:
        path: Asset path

    Returns:
        Full CDN URL
    """
    return cdn_config.get_static_url(path)


@register.filter
def with_signed_url(path: str) -> str:
    """
    Filter to convert media path to signed CDN URL.

    Usage:
        {{ document.file.name|with_signed_url }}

    Args:
        path: Media file path

    Returns:
        Signed CDN URL
    """
    return cdn_config.get_media_url(path, sign=True)
