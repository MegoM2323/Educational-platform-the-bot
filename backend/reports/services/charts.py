"""
Chart generation service for reports.

Supports multiple chart types (bar, line, pie, histogram, box plot)
with various output formats (PNG, SVG, JSON).

Features:
- Base64 encoded image output for embedding in emails/PDFs
- Configurable sizes and themes
- Accessibility features (alt text, color contrast)
- Response caching (5 minutes)
- Async generation for large datasets (Celery)
"""

import base64
import io
import json
import logging
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
from django.core.cache import cache
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


class ChartGenerationService:
    """Service for generating various types of charts for reports."""

    # Predefined sizes (width, height)
    SIZES = {
        'small': (6, 4),
        'medium': (10, 6),
        'large': (14, 8),
    }

    # Color schemes for light/dark themes
    THEMES = {
        'light': {
            'background': '#ffffff',
            'text': '#000000',
            'grid': '#e0e0e0',
            'colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
        },
        'dark': {
            'background': '#1a1a1a',
            'text': '#ffffff',
            'grid': '#333333',
            'colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
        },
    }

    @staticmethod
    def _get_cache_key(chart_type: str, data_hash: str) -> str:
        """Generate cache key for chart data."""
        return f"chart_{chart_type}_{data_hash}"

    @staticmethod
    def _hash_data(data: Dict[str, Any]) -> str:
        """Create hash of chart data for caching."""
        import hashlib
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()

    @staticmethod
    def _apply_theme(fig: Figure, ax: Any, theme: str = 'light') -> None:
        """Apply theme styling to figure and axes."""
        theme_config = ChartGenerationService.THEMES.get(theme, ChartGenerationService.THEMES['light'])

        fig.patch.set_facecolor(theme_config['background'])
        ax.patch.set_facecolor(theme_config['background'])
        ax.spines['bottom'].set_color(theme_config['text'])
        ax.spines['left'].set_color(theme_config['text'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        ax.tick_params(colors=theme_config['text'])
        ax.xaxis.label.set_color(theme_config['text'])
        ax.yaxis.label.set_color(theme_config['text'])
        ax.title.set_color(theme_config['text'])

        ax.grid(True, alpha=0.3, color=theme_config['grid'], linestyle='--')

    @classmethod
    def generate_bar_chart(
        cls,
        labels: List[str],
        data: List[float],
        title: str = "Bar Chart",
        xlabel: str = "Categories",
        ylabel: str = "Values",
        size: str = 'medium',
        theme: str = 'light',
        colors: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a bar chart.

        Args:
            labels: Category labels
            data: Data values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            size: Chart size ('small', 'medium', 'large')
            theme: Color theme ('light', 'dark')
            colors: Custom color list

        Returns:
            Dictionary with 'png_base64', 'svg', and 'json' formats
        """
        if len(labels) != len(data):
            raise ValueError("Labels and data must have the same length")

        if not labels or not data:
            raise ValueError("Labels and data cannot be empty")

        # Check cache
        cache_key = cls._get_cache_key('bar', cls._hash_data({'labels': labels, 'data': data}))
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        fig_size = cls.SIZES.get(size, cls.SIZES['medium'])
        fig, ax = plt.subplots(figsize=fig_size)

        # Use theme colors if not provided
        if colors is None:
            colors = cls.THEMES[theme]['colors'][:len(labels)]

        bars = ax.bar(labels, data, color=colors, alpha=0.7, edgecolor='black', linewidth=1.2)

        ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height >= 0:
                ax.text(bar.get_x() + bar.get_width() / 2., height,
                        f'{height:.2f}',
                        ha='center', va='bottom', fontsize=10)

        cls._apply_theme(fig, ax, theme)
        plt.tight_layout()

        result = cls._export_chart(fig, title)

        # Cache for 5 minutes
        cache.set(cache_key, result, 300)

        plt.close(fig)
        return result

    @classmethod
    def generate_line_chart(
        cls,
        labels: List[str],
        data: Dict[str, List[float]],
        title: str = "Line Chart",
        xlabel: str = "Time",
        ylabel: str = "Values",
        size: str = 'medium',
        theme: str = 'light',
    ) -> Dict[str, Any]:
        """
        Generate a line chart (supports multiple lines).

        Args:
            labels: X-axis labels (e.g., dates, periods)
            data: Dictionary with {series_name: [values]}
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            size: Chart size
            theme: Color theme

        Returns:
            Dictionary with chart formats
        """
        if not labels or not data:
            raise ValueError("Labels and data cannot be empty")

        for series_data in data.values():
            if len(series_data) != len(labels):
                raise ValueError("All data series must match labels length")

        # Check cache
        cache_key = cls._get_cache_key('line', cls._hash_data({'labels': labels, 'data': data}))
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        fig_size = cls.SIZES.get(size, cls.SIZES['medium'])
        fig, ax = plt.subplots(figsize=fig_size)

        theme_config = cls.THEMES.get(theme, cls.THEMES['light'])
        x_pos = np.arange(len(labels))

        # Plot multiple lines
        for i, (series_name, values) in enumerate(data.items()):
            color = theme_config['colors'][i % len(theme_config['colors'])]
            ax.plot(x_pos, values, marker='o', label=series_name, linewidth=2,
                   color=color, markersize=8, alpha=0.8)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='best', framealpha=0.9)

        cls._apply_theme(fig, ax, theme)
        plt.tight_layout()

        result = cls._export_chart(fig, title)

        # Cache for 5 minutes
        cache.set(cache_key, result, 300)

        plt.close(fig)
        return result

    @classmethod
    def generate_pie_chart(
        cls,
        labels: List[str],
        data: List[float],
        title: str = "Pie Chart",
        size: str = 'medium',
        theme: str = 'light',
    ) -> Dict[str, Any]:
        """
        Generate a pie chart.

        Args:
            labels: Category labels
            data: Data values
            title: Chart title
            size: Chart size
            theme: Color theme

        Returns:
            Dictionary with chart formats
        """
        if len(labels) != len(data):
            raise ValueError("Labels and data must have the same length")

        if not labels or not data or sum(data) <= 0:
            raise ValueError("Valid labels and positive data required")

        # Check cache
        cache_key = cls._get_cache_key('pie', cls._hash_data({'labels': labels, 'data': data}))
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        fig_size = cls.SIZES.get(size, cls.SIZES['medium'])
        fig, ax = plt.subplots(figsize=fig_size)

        theme_config = cls.THEMES.get(theme, cls.THEMES['light'])

        wedges, texts, autotexts = ax.pie(
            data,
            labels=labels,
            autopct='%1.1f%%',
            colors=theme_config['colors'][:len(labels)],
            startangle=90,
            textprops={'color': theme_config['text'], 'fontsize': 10}
        )

        # Format percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(10)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=20,
                    color=theme_config['text'])

        cls._apply_theme(fig, ax, theme)
        plt.tight_layout()

        result = cls._export_chart(fig, title)

        # Cache for 5 minutes
        cache.set(cache_key, result, 300)

        plt.close(fig)
        return result

    @classmethod
    def generate_histogram(
        cls,
        data: List[float],
        title: str = "Histogram",
        xlabel: str = "Values",
        ylabel: str = "Frequency",
        bins: int = 10,
        size: str = 'medium',
        theme: str = 'light',
    ) -> Dict[str, Any]:
        """
        Generate a histogram.

        Args:
            data: Data values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            bins: Number of bins
            size: Chart size
            theme: Color theme

        Returns:
            Dictionary with chart formats
        """
        if not data or len(data) == 0:
            raise ValueError("Data cannot be empty")

        # Check cache
        cache_key = cls._get_cache_key('histogram', cls._hash_data({'data': data, 'bins': bins}))
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        fig_size = cls.SIZES.get(size, cls.SIZES['medium'])
        fig, ax = plt.subplots(figsize=fig_size)

        theme_config = cls.THEMES.get(theme, cls.THEMES['light'])
        color = theme_config['colors'][0]

        ax.hist(data, bins=bins, color=color, alpha=0.7, edgecolor='black', linewidth=1.2)

        ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

        cls._apply_theme(fig, ax, theme)
        plt.tight_layout()

        result = cls._export_chart(fig, title)

        # Cache for 5 minutes
        cache.set(cache_key, result, 300)

        plt.close(fig)
        return result

    @classmethod
    def generate_box_plot(
        cls,
        data: Dict[str, List[float]],
        title: str = "Box Plot",
        ylabel: str = "Values",
        size: str = 'medium',
        theme: str = 'light',
    ) -> Dict[str, Any]:
        """
        Generate a box plot showing quartile distribution.

        Args:
            data: Dictionary with {series_name: [values]}
            title: Chart title
            ylabel: Y-axis label
            size: Chart size
            theme: Color theme

        Returns:
            Dictionary with chart formats
        """
        if not data or len(data) == 0:
            raise ValueError("Data cannot be empty")

        # Check cache
        cache_key = cls._get_cache_key('boxplot', cls._hash_data({'data': {k: len(v) for k, v in data.items()}}))
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        fig_size = cls.SIZES.get(size, cls.SIZES['medium'])
        fig, ax = plt.subplots(figsize=fig_size)

        theme_config = cls.THEMES.get(theme, cls.THEMES['light'])

        labels = list(data.keys())
        values = list(data.values())

        bp = ax.boxplot(values, labels=labels, patch_artist=True,
                       medianprops=dict(color='red', linewidth=2))

        # Color boxes
        for patch, color in zip(bp['boxes'], theme_config['colors'][:len(labels)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

        cls._apply_theme(fig, ax, theme)
        plt.tight_layout()

        result = cls._export_chart(fig, title)

        # Cache for 5 minutes
        cache.set(cache_key, result, 300)

        plt.close(fig)
        return result

    @staticmethod
    def _export_chart(fig: Figure, title: str) -> Dict[str, Any]:
        """
        Export chart to multiple formats.

        Args:
            fig: Matplotlib figure
            title: Chart title (for accessibility)

        Returns:
            Dictionary with 'png_base64', 'svg', and 'json' keys
        """
        # PNG base64
        png_buffer = io.BytesIO()
        fig.savefig(png_buffer, format='png', dpi=100, bbox_inches='tight')
        png_buffer.seek(0)
        png_base64 = base64.b64encode(png_buffer.read()).decode('utf-8')

        # SVG
        svg_buffer = io.BytesIO()
        fig.savefig(svg_buffer, format='svg', bbox_inches='tight')
        svg_buffer.seek(0)
        svg_data = svg_buffer.getvalue().decode('utf-8')

        # JSON representation
        json_data = {
            'title': title,
            'type': 'chart',
            'formats': ['png_base64', 'svg'],
        }

        return {
            'png_base64': f'data:image/png;base64,{png_base64}',
            'svg': svg_data,
            'json': json_data,
            'title': title,
            'alt_text': f'{title} - Chart visualization',
        }

    @staticmethod
    def validate_chart_request(chart_type: str, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate chart generation request.

        Args:
            chart_type: Type of chart
            data: Chart data

        Returns:
            Tuple of (is_valid, error_message)
        """
        valid_types = ['bar', 'line', 'pie', 'histogram', 'box_plot']

        if chart_type not in valid_types:
            return False, f"Invalid chart type: {chart_type}. Valid types: {', '.join(valid_types)}"

        if not data:
            return False, "Chart data cannot be empty"

        # Validate specific chart types
        if chart_type in ['bar', 'pie']:
            if 'labels' not in data or 'values' not in data:
                return False, f"{chart_type} chart requires 'labels' and 'values'"
            if not isinstance(data['labels'], list) or not isinstance(data['values'], list):
                return False, "'labels' and 'values' must be lists"
            if len(data['labels']) != len(data['values']):
                return False, "'labels' and 'values' must have equal length"

        elif chart_type == 'line':
            if 'labels' not in data or 'data' not in data:
                return False, "line chart requires 'labels' and 'data'"
            if not isinstance(data['data'], dict):
                return False, "'data' must be a dictionary"

        elif chart_type == 'histogram':
            if 'data' not in data:
                return False, "histogram requires 'data'"
            if not isinstance(data['data'], list):
                return False, "'data' must be a list"

        elif chart_type == 'box_plot':
            if 'data' not in data:
                return False, "box_plot requires 'data'"
            if not isinstance(data['data'], dict):
                return False, "'data' must be a dictionary"

        return True, None
