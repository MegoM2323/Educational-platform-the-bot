"""
Simple tests for chart generation service (no Django DB required).

These tests verify the core chart generation functionality without needing
a fully configured Django database.
"""

import base64
import json

import pytest

from reports.services.charts import ChartGenerationService


class TestChartGenerationServiceSimple:
    """Tests for ChartGenerationService without Django database."""

    def test_bar_chart_generation(self):
        """Test basic bar chart generation."""
        labels = ['Q1', 'Q2', 'Q3', 'Q4']
        data = [65, 75, 80, 70]

        result = ChartGenerationService.generate_bar_chart(
            labels=labels,
            data=data,
            title='Quarterly Performance',
        )

        assert 'png_base64' in result
        assert 'svg' in result
        assert 'json' in result
        assert 'title' in result
        assert 'alt_text' in result
        assert result['title'] == 'Quarterly Performance'
        assert result['png_base64'].startswith('data:image/png;base64,')

    def test_bar_chart_png_is_valid(self):
        """Test that PNG base64 output is valid."""
        labels = ['A', 'B', 'C']
        data = [10, 20, 30]

        result = ChartGenerationService.generate_bar_chart(
            labels=labels,
            data=data,
            title='Valid PNG',
        )

        # Extract base64 data
        png_data = result['png_base64'].replace('data:image/png;base64,', '')

        # Decode and verify it's a valid PNG
        decoded = base64.b64decode(png_data)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'  # PNG magic number

    def test_bar_chart_invalid_labels_data_mismatch(self):
        """Test bar chart with mismatched labels and data."""
        labels = ['A', 'B', 'C']
        data = [10, 20]  # Mismatch

        with pytest.raises(ValueError, match="must have the same length"):
            ChartGenerationService.generate_bar_chart(
                labels=labels,
                data=data,
                title='Invalid',
            )

    def test_bar_chart_empty_data(self):
        """Test bar chart with empty data."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChartGenerationService.generate_bar_chart(
                labels=[],
                data=[],
                title='Empty',
            )

    def test_line_chart_generation(self):
        """Test line chart with single series."""
        labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        data = {
            'Student A': [60, 70, 75, 80],
        }

        result = ChartGenerationService.generate_line_chart(
            labels=labels,
            data=data,
            title='Progress Over Time',
        )

        assert 'png_base64' in result
        assert 'svg' in result
        assert result['title'] == 'Progress Over Time'

    def test_line_chart_multiple_series(self):
        """Test line chart with multiple series."""
        labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
        data = {
            'Student A': [60, 70, 75, 80],
            'Student B': [50, 60, 70, 75],
            'Student C': [55, 65, 80, 85],
        }

        result = ChartGenerationService.generate_line_chart(
            labels=labels,
            data=data,
            title='Class Progress',
        )

        assert 'png_base64' in result

    def test_line_chart_mismatched_data(self):
        """Test line chart with mismatched data length."""
        labels = ['Week 1', 'Week 2', 'Week 3']
        data = {
            'Student A': [60, 70, 75, 80],  # Mismatch
        }

        with pytest.raises(ValueError):
            ChartGenerationService.generate_line_chart(
                labels=labels,
                data=data,
                title='Invalid',
            )

    def test_pie_chart_generation(self):
        """Test pie chart generation."""
        labels = ['A', 'B', 'C', 'D', 'F']
        data = [25, 30, 20, 15, 10]

        result = ChartGenerationService.generate_pie_chart(
            labels=labels,
            data=data,
            title='Grade Distribution',
        )

        assert 'png_base64' in result
        assert 'svg' in result
        assert result['title'] == 'Grade Distribution'

    def test_pie_chart_zero_sum(self):
        """Test pie chart with zero sum data."""
        labels = ['A', 'B', 'C']
        data = [0, 0, 0]

        with pytest.raises(ValueError):
            ChartGenerationService.generate_pie_chart(
                labels=labels,
                data=data,
                title='Invalid',
            )

    def test_histogram_generation(self):
        """Test histogram generation."""
        data = [60, 65, 70, 75, 75, 80, 80, 80, 85, 90]

        result = ChartGenerationService.generate_histogram(
            data=data,
            title='Score Distribution',
            bins=5,
        )

        assert 'png_base64' in result
        assert 'svg' in result

    def test_histogram_empty_data(self):
        """Test histogram with empty data."""
        with pytest.raises(ValueError):
            ChartGenerationService.generate_histogram(
                data=[],
                title='Empty',
            )

    def test_histogram_custom_bins(self):
        """Test histogram with custom bins."""
        data = list(range(1, 101))

        for bins in [5, 10, 20]:
            result = ChartGenerationService.generate_histogram(
                data=data,
                title=f'Histogram {bins} bins',
                bins=bins,
            )
            assert 'png_base64' in result

    def test_box_plot_generation(self):
        """Test box plot generation."""
        data = {
            'Class A': [60, 65, 70, 75, 80],
            'Class B': [55, 70, 75, 80, 95],
        }

        result = ChartGenerationService.generate_box_plot(
            data=data,
            title='Score Distribution by Class',
        )

        assert 'png_base64' in result
        assert 'svg' in result

    def test_box_plot_empty_data(self):
        """Test box plot with empty data."""
        with pytest.raises(ValueError):
            ChartGenerationService.generate_box_plot(
                data={},
                title='Empty',
            )

    def test_bar_chart_with_custom_colors(self):
        """Test bar chart with custom colors."""
        labels = ['A', 'B', 'C']
        data = [10, 20, 30]
        colors = ['#FF0000', '#00FF00', '#0000FF']

        result = ChartGenerationService.generate_bar_chart(
            labels=labels,
            data=data,
            title='Custom Colors',
            colors=colors,
        )

        assert result['png_base64'].startswith('data:image/png;base64,')

    def test_bar_chart_different_sizes(self):
        """Test bar chart with different sizes."""
        labels = ['A', 'B']
        data = [10, 20]

        for size in ['small', 'medium', 'large']:
            result = ChartGenerationService.generate_bar_chart(
                labels=labels,
                data=data,
                title=f'Chart {size}',
                size=size,
            )
            assert 'png_base64' in result

    def test_bar_chart_themes(self):
        """Test bar chart with different themes."""
        labels = ['A', 'B']
        data = [10, 20]

        for theme in ['light', 'dark']:
            result = ChartGenerationService.generate_bar_chart(
                labels=labels,
                data=data,
                title=f'Chart {theme}',
                theme=theme,
            )
            assert 'png_base64' in result

    def test_validate_chart_request_invalid_type(self):
        """Test validation with invalid chart type."""
        is_valid, error = ChartGenerationService.validate_chart_request(
            'invalid_type',
            {'labels': [], 'values': []}
        )

        assert not is_valid
        assert 'Invalid chart type' in error

    def test_validate_chart_request_bar_missing_labels(self):
        """Test validation for bar chart missing labels."""
        is_valid, error = ChartGenerationService.validate_chart_request(
            'bar',
            {'values': [1, 2, 3]}
        )

        assert not is_valid
        assert 'labels' in error.lower()

    def test_validate_chart_request_bar_mismatched_lengths(self):
        """Test validation for bar chart with mismatched lengths."""
        is_valid, error = ChartGenerationService.validate_chart_request(
            'bar',
            {'labels': ['A', 'B'], 'values': [1, 2, 3]}
        )

        assert not is_valid
        assert 'equal length' in error.lower()

    def test_validate_chart_request_line_invalid_data_type(self):
        """Test validation for line chart with invalid data type."""
        is_valid, error = ChartGenerationService.validate_chart_request(
            'line',
            {'labels': ['A', 'B'], 'data': [1, 2]}  # Should be dict
        )

        assert not is_valid
        assert 'dictionary' in error.lower()

    def test_validate_chart_request_histogram_missing_data(self):
        """Test validation for histogram missing data."""
        is_valid, error = ChartGenerationService.validate_chart_request(
            'histogram',
            {'title': 'Test'}
        )

        assert not is_valid
        assert 'data' in error.lower()

    def test_validate_chart_request_box_plot_valid(self):
        """Test validation for valid box plot request."""
        is_valid, error = ChartGenerationService.validate_chart_request(
            'box_plot',
            {'data': {'A': [1, 2, 3], 'B': [4, 5, 6]}}
        )

        assert is_valid
        assert error is None

    def test_validate_chart_request_empty_data(self):
        """Test validation with empty data."""
        is_valid, error = ChartGenerationService.validate_chart_request(
            'bar',
            {}
        )

        assert not is_valid

    def test_chart_has_accessibility_features(self):
        """Test that generated charts have accessibility features."""
        labels = ['A', 'B', 'C']
        data = [10, 20, 30]

        result = ChartGenerationService.generate_bar_chart(
            labels=labels,
            data=data,
            title='Accessible Chart',
        )

        # Should have alt text
        assert 'alt_text' in result
        assert 'Chart visualization' in result['alt_text']

    def test_chart_output_formats(self):
        """Test that charts output multiple formats."""
        labels = ['A', 'B', 'C']
        data = [10, 20, 30]

        result = ChartGenerationService.generate_bar_chart(
            labels=labels,
            data=data,
            title='Multi-format Chart',
        )

        # Should have PNG base64
        assert result['png_base64'].startswith('data:image/png;base64,')

        # Should have SVG
        assert '<svg' in result['svg']
        assert '</svg>' in result['svg']

        # Should have JSON
        assert isinstance(result['json'], dict)
        assert 'title' in result['json']
