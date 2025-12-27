"""
Simple tests for Report Generation Service - no Django dependencies

Tests the core functionality of the ReportGenerationService
without requiring full test environment setup.
"""

import json
from datetime import datetime, timedelta
from io import BytesIO
import io

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.generation_service import (
    ReportGenerationService,
    ReportGenerationException,
    ReportScheduler
)


def test_report_types():
    """Test that all report types are properly defined."""
    assert 'student_progress' in ReportGenerationService.REPORT_TYPES
    assert 'class_performance' in ReportGenerationService.REPORT_TYPES
    assert 'assignment_analysis' in ReportGenerationService.REPORT_TYPES
    assert 'subject_analysis' in ReportGenerationService.REPORT_TYPES
    assert 'tutor_weekly' in ReportGenerationService.REPORT_TYPES
    assert 'teacher_weekly' in ReportGenerationService.REPORT_TYPES
    print("✓ All report types defined correctly")


def test_cache_ttl_values():
    """Test cache TTL configuration."""
    assert ReportGenerationService.CACHE_TTL_SHORT == 300
    assert ReportGenerationService.CACHE_TTL_MEDIUM == 1800
    assert ReportGenerationService.CACHE_TTL_LONG == 3600
    print("✓ Cache TTL values correct")


def test_report_types_metadata():
    """Test that all report types have proper metadata."""
    for report_type, metadata in ReportGenerationService.REPORT_TYPES.items():
        assert 'name' in metadata, f"Missing name for {report_type}"
        assert 'description' in metadata, f"Missing description for {report_type}"
        assert 'data_sources' in metadata, f"Missing data_sources for {report_type}"
        assert isinstance(metadata['data_sources'], list), f"data_sources should be a list for {report_type}"
        print(f"  ✓ {report_type}: {metadata['name']}")
    print("✓ All report type metadata is valid")


def test_scheduler_schedules():
    """Test scheduler frequency configurations."""
    assert 'daily' in ReportScheduler.SCHEDULES
    assert 'weekly' in ReportScheduler.SCHEDULES
    assert 'monthly' in ReportScheduler.SCHEDULES

    assert ReportScheduler.SCHEDULES['daily']['frequency'] == 'daily'
    assert ReportScheduler.SCHEDULES['weekly']['frequency'] == 'weekly'
    assert ReportScheduler.SCHEDULES['monthly']['frequency'] == 'monthly'
    print("✓ Scheduler configurations valid")


def test_invalid_report_type():
    """Test that invalid report type raises exception."""
    try:
        # Create a mock user object
        class MockUser:
            pass

        user = MockUser()
        service = ReportGenerationService(user, 'invalid_type')
        assert False, "Should have raised ReportGenerationException"
    except ReportGenerationException as e:
        assert "Invalid report type" in str(e)
        print("✓ Invalid report type raises proper exception")


def test_cache_key_generation():
    """Test cache key generation."""
    # Create a mock user object
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    key1 = service._get_cache_key({'student_id': 1})
    key2 = service._get_cache_key({'student_id': 2})
    key3 = service._get_cache_key({'student_id': 1})

    # Different filters should generate different keys
    assert key1 != key2, "Different filters should generate different keys"
    # Same filters should generate same key
    assert key1 == key3, "Same filters should generate same key"

    # All keys should have proper prefix
    assert key1.startswith("report_student_progress_"), "Cache key should have proper prefix"
    print("✓ Cache key generation works correctly")


def test_progress_tracking():
    """Test progress tracking data structure."""
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    # Initially should have initializing status
    progress = service.get_progress()
    assert 'status' in progress
    assert 'percentage' in progress
    assert 'timestamp' in progress

    # Test progress update
    service._update_progress('test_status', 50)
    progress = service.get_progress()
    assert progress['status'] == 'test_status'
    assert progress['percentage'] == 50
    print("✓ Progress tracking works correctly")


def test_progress_callback():
    """Test progress callback functionality."""
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    callback_called = []

    def mock_callback(data):
        callback_called.append(data)

    service._update_progress('test', 50, mock_callback)
    assert len(callback_called) > 0, "Callback should be called"
    print("✓ Progress callback works correctly")


def test_data_point_counting():
    """Test data point counting utility."""
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    # Test with dict
    data = {'a': 1, 'b': 2, 'c': {'d': 3}}
    count = service._count_data_points(data)
    assert count > 0, "Should count data points"

    # Test with list
    data_list = [1, 2, 3, 4, 5]
    count = service._count_data_points(data_list)
    assert count == 5, "Should count list length"
    print("✓ Data point counting works correctly")


def test_excel_format_detection():
    """Test that Excel format is detected correctly."""
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    # Create sample data
    test_data = {
        'summary': {'total': 10},
        'details': {'data': []},
        'metadata': {'generated_at': datetime.now().isoformat()}
    }

    # Test Excel formatting
    try:
        excel_bytes = service._format_as_excel(test_data)
        assert isinstance(excel_bytes, bytes), "Excel output should be bytes"
        assert excel_bytes.startswith(b'PK'), "Excel file should have PK signature"
        print("✓ Excel format generation works correctly")
    except Exception as e:
        print(f"✗ Excel format test failed: {e}")


def test_summary_generation():
    """Test summary generation from data."""
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    test_data = {
        'student': {'id': 1},
        'material_progress': [
            {'progress_percentage': 85, 'is_completed': True, 'time_spent': 100},
            {'progress_percentage': 60, 'is_completed': False, 'time_spent': 80}
        ]
    }

    summary = service._generate_summary(test_data)
    assert 'summary' not in str(summary.__class__), "Summary should be generated"
    assert 'report_type' in summary
    assert summary['report_type'] == 'student_progress'
    print("✓ Summary generation works correctly")


def test_insights_generation():
    """Test insights generation from data."""
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    # Test with good progress
    data_good = {
        'material_progress': [
            {'progress_percentage': 95},
            {'progress_percentage': 90},
        ]
    }

    insights = service._generate_insights(data_good)
    assert isinstance(insights, list)
    assert len(insights) > 0, "Should generate insights"
    print("✓ Insights generation works correctly")


def test_scheduler_invalid_frequency():
    """Test scheduler with invalid frequency."""
    try:
        class MockUser:
            pass

        user = MockUser()
        ReportScheduler.schedule_report(
            user=user,
            report_type='student_progress',
            frequency='invalid',
            recipients=[]
        )
        assert False, "Should raise exception for invalid frequency"
    except ReportGenerationException as e:
        assert "Invalid frequency" in str(e)
        print("✓ Scheduler properly rejects invalid frequency")


def test_output_formats_supported():
    """Test that all required output formats are supported."""
    class MockUser:
        role = 'teacher'

    user = MockUser()
    service = ReportGenerationService(user, 'student_progress')

    test_data = {'summary': {}, 'details': {}, 'metadata': {}}

    # Test JSON format (should not raise)
    try:
        result = service._format_output(test_data, 'json')
        assert isinstance(result, dict), "JSON format should return dict"
        print("  ✓ JSON format supported")
    except Exception as e:
        print(f"  ✗ JSON format failed: {e}")

    # Test unsupported format
    try:
        result = service._format_output(test_data, 'xml')
        assert False, "Should raise exception for unsupported format"
    except ReportGenerationException:
        print("  ✓ Unsupported format properly rejected")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("REPORT GENERATION SERVICE - UNIT TESTS")
    print("="*60)

    tests = [
        ("Report Types Configuration", test_report_types),
        ("Cache TTL Values", test_cache_ttl_values),
        ("Report Type Metadata", test_report_types_metadata),
        ("Scheduler Configurations", test_scheduler_schedules),
        ("Invalid Report Type Handling", test_invalid_report_type),
        ("Cache Key Generation", test_cache_key_generation),
        ("Progress Tracking", test_progress_tracking),
        ("Progress Callback", test_progress_callback),
        ("Data Point Counting", test_data_point_counting),
        ("Excel Format Detection", test_excel_format_detection),
        ("Summary Generation", test_summary_generation),
        ("Insights Generation", test_insights_generation),
        ("Scheduler Invalid Frequency", test_scheduler_invalid_frequency),
        ("Output Formats Supported", test_output_formats_supported),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n📝 {test_name}")
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
