"""
Tests for chart generation service and API endpoints.

Covers:
- Chart generation for all types (bar, line, pie, histogram, box_plot)
- Base64 PNG output validation
- JSON endpoint for frontend rendering
- Caching behavior
- Error handling (no data, invalid type)
- Input validation
"""

import base64
import json
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from PIL import Image
from rest_framework.test import APIClient

from reports.services.charts import ChartGenerationService

User = get_user_model()


@pytest.mark.django_db
class TestChartGenerationService:
    """Tests for ChartGenerationService."""

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

    def test_caching_bar_chart(self):
        """Test chart caching."""
        labels = ['A', 'B', 'C']
        data = [10, 20, 30]

        cache.clear()

        # Generate chart first time
        result1 = ChartGenerationService.generate_bar_chart(
            labels=labels,
            data=data,
            title='Cached Chart',
        )

        # Generate same chart again (should use cache)
        result2 = ChartGenerationService.generate_bar_chart(
            labels=labels,
            data=data,
            title='Cached Chart',
        )

        # Results should be identical
        assert result1['png_base64'] == result2['png_base64']

    def test_cache_invalidation_on_data_change(self):
        """Test that cache invalidates when data changes."""
        cache.clear()

        # Generate chart with data set 1
        result1 = ChartGenerationService.generate_bar_chart(
            labels=['A', 'B'],
            data=[10, 20],
            title='Chart',
        )

        # Generate chart with data set 2
        result2 = ChartGenerationService.generate_bar_chart(
            labels=['A', 'B'],
            data=[15, 25],
            title='Chart',
        )

        # Results should be different
        assert result1['png_base64'] != result2['png_base64']

    def test_png_base64_is_valid(self):
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


@pytest.mark.django_db
class TestChartViewSet:
    """Tests for ChartViewSet API."""

    @pytest.fixture
    def client(self):
        """Create API client."""
        return APIClient()

    @pytest.fixture
    def user(self):
        """Create test user."""
        return User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='teacher'
        )

    def test_charts_list_endpoint(self, client, user):
        """Test charts list endpoint."""
        client.force_authenticate(user=user)
        response = client.get('/api/reports/charts/')

        assert response.status_code == 200
        data = response.json()
        assert 'available_charts' in data
        assert 'bar' in data['available_charts']
        assert 'line' in data['available_charts']
        assert 'pie' in data['available_charts']
        assert 'histogram' in data['available_charts']
        assert 'box_plot' in data['available_charts']
        assert 'sizes' in data
        assert 'themes' in data

    def test_generate_bar_chart_endpoint(self, client, user):
        """Test generate bar chart endpoint."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'bar',
            'labels': ['Q1', 'Q2', 'Q3', 'Q4'],
            'values': [65, 75, 80, 70],
            'title': 'Quarterly Performance',
            'size': 'medium',
            'theme': 'light',
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert 'chart' in data
        assert 'png_base64' in data['chart']
        assert 'svg' in data['chart']
        assert data['chart']['title'] == 'Quarterly Performance'

    def test_generate_line_chart_endpoint(self, client, user):
        """Test generate line chart endpoint."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'line',
            'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
            'data': {
                'Student A': [60, 70, 75, 80],
                'Student B': [50, 60, 70, 75],
            },
            'title': 'Progress Over Time',
            'size': 'medium',
            'theme': 'light',
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert 'chart' in data

    def test_generate_pie_chart_endpoint(self, client, user):
        """Test generate pie chart endpoint."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'pie',
            'labels': ['A', 'B', 'C', 'D', 'F'],
            'values': [25, 30, 20, 15, 10],
            'title': 'Grade Distribution',
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True

    def test_generate_histogram_endpoint(self, client, user):
        """Test generate histogram endpoint."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'histogram',
            'data': [60, 65, 70, 75, 75, 80, 80, 80, 85, 90],
            'title': 'Score Distribution',
            'bins': 5,
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201

    def test_generate_box_plot_endpoint(self, client, user):
        """Test generate box plot endpoint."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'box_plot',
            'data': {
                'Class A': [60, 65, 70, 75, 80],
                'Class B': [55, 70, 75, 80, 95],
            },
            'title': 'Score Distribution by Class',
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201

    def test_invalid_chart_type_endpoint(self, client, user):
        """Test endpoint with invalid chart type."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'invalid_type',
            'labels': [],
            'values': [],
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'error' in data

    def test_missing_chart_type_endpoint(self, client, user):
        """Test endpoint with missing chart type."""
        client.force_authenticate(user=user)

        payload = {
            'labels': [],
            'values': [],
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 400

    def test_authentication_required(self, client):
        """Test that authentication is required."""
        response = client.get('/api/reports/charts/')

        assert response.status_code == 401

    def test_chart_with_empty_labels(self, client, user):
        """Test chart generation with empty labels."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'bar',
            'labels': [],
            'values': [],
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 400

    def test_bar_chart_custom_labels(self, client, user):
        """Test bar chart with custom axis labels."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'bar',
            'labels': ['Jan', 'Feb', 'Mar'],
            'values': [100, 150, 200],
            'xlabel': 'Months',
            'ylabel': 'Revenue ($)',
            'title': 'Monthly Revenue',
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True

    def test_bar_chart_dark_theme(self, client, user):
        """Test bar chart with dark theme."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'bar',
            'labels': ['A', 'B', 'C'],
            'values': [10, 20, 30],
            'theme': 'dark',
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201

    def test_bar_chart_large_size(self, client, user):
        """Test bar chart with large size."""
        client.force_authenticate(user=user)

        payload = {
            'type': 'bar',
            'labels': ['A', 'B'],
            'values': [10, 20],
            'size': 'large',
        }

        response = client.post('/api/reports/charts/', payload, format='json')

        assert response.status_code == 201
        data = response.json()
        assert 'chart' in data
        assert 'png_base64' in data['chart']
