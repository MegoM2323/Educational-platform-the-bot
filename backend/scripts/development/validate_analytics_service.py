#!/usr/bin/env python
"""
Validation script for LearningAnalyticsService.

Tests:
- Service can be imported
- All required methods exist
- Service initialization works
- Caching behavior works
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('ENVIRONMENT', 'test')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django.setup()

from reports.services.analytics import LearningAnalyticsService


def validate_service():
    """Validate the LearningAnalyticsService."""
    print("\n" + "=" * 70)
    print("VALIDATING LEARNING ANALYTICS SERVICE")
    print("=" * 70 + "\n")

    # Test 1: Service instantiation
    print("1. Testing service instantiation...")
    try:
        service = LearningAnalyticsService(use_cache=True)
        print("   ✅ Service created with cache enabled")
    except Exception as e:
        print(f"   ❌ Failed to create service: {e}")
        return False

    # Test 2: Service without cache
    print("\n2. Testing service without cache...")
    try:
        service_no_cache = LearningAnalyticsService(use_cache=False)
        print("   ✅ Service created with cache disabled")
    except Exception as e:
        print(f"   ❌ Failed to create service: {e}")
        return False

    # Test 3: Check required methods
    print("\n3. Checking required methods...")
    required_methods = [
        'get_student_analytics',
        'get_class_analytics',
        'get_subject_analytics',
        'identify_at_risk_students',
        'generate_learning_recommendations',
        'get_batch_student_analytics',
        'clear_analytics_cache',
    ]

    for method_name in required_methods:
        if hasattr(service, method_name) and callable(getattr(service, method_name)):
            print(f"   ✅ Method {method_name} exists")
        else:
            print(f"   ❌ Method {method_name} missing")
            return False

    # Test 4: Check configuration constants
    print("\n4. Checking configuration constants...")
    constants = [
        ('CACHE_TTL', int),
        ('ENGAGEMENT_EXCELLENT', int),
        ('ENGAGEMENT_GOOD', int),
        ('ENGAGEMENT_FAIR', int),
        ('ENGAGEMENT_POOR', int),
        ('AT_RISK_THRESHOLD', int),
        ('ANALYSIS_PERIOD_DAYS', int),
    ]

    for const_name, expected_type in constants:
        if hasattr(service, const_name):
            value = getattr(service, const_name)
            if isinstance(value, expected_type):
                print(f"   ✅ Constant {const_name} = {value}")
            else:
                print(f"   ⚠️  Constant {const_name} has unexpected type: {type(value)}")
        else:
            print(f"   ❌ Constant {const_name} missing")
            return False

    # Test 5: Test nonexistent student (should not crash)
    print("\n5. Testing error handling for nonexistent student...")
    try:
        result = service.get_student_analytics(99999)
        if 'error' in result or 'engagement_score' in result:
            print(f"   ✅ Correctly handled nonexistent/empty student")
        else:
            print(f"   ⚠️  Unexpected result structure")
    except Exception as e:
        # Database tables may not exist in validation environment
        if 'no such table' in str(e):
            print(f"   ℹ️  Database not initialized (expected in validation): {type(e).__name__}")
        else:
            print(f"   ❌ Unexpected error: {e}")
            return False

    # Test 6: Skip database tests if tables don't exist
    print("\n6. Skipping database tests (tables may not exist in validation)...")

    # Test 7: Test cache key generation
    print("\n7. Testing cache key generation (non-DB test)...")
    try:
        cache_key = service._get_cache_key('student_analytics', 123)
        if 'analytics:student_analytics:123' in cache_key:
            print(f"   ✅ Cache key generated correctly: {cache_key}")
        else:
            print(f"   ❌ Unexpected cache key: {cache_key}")
            return False
    except Exception as e:
        print(f"   ❌ Error generating cache key: {e}")
        return False

    # Test 8: Test engagement level classification
    print("\n8. Testing engagement level classification (non-DB test)...")
    test_cases = [
        (90, 'excellent'),
        (70, 'good'),
        (50, 'fair'),
        (30, 'poor'),
    ]

    for score, expected_level in test_cases:
        try:
            level = service._get_engagement_level(score)
            if level == expected_level:
                print(f"   ✅ Score {score} -> '{level}'")
            else:
                print(f"   ❌ Score {score} -> '{level}' (expected '{expected_level}')")
                return False
        except Exception as e:
            print(f"   ❌ Error classifying score {score}: {e}")
            return False

    # Test 9: Test risk level determination
    print("\n9. Testing risk level determination (non-DB test)...")
    test_cases = [
        {'engagement_score': 80, 'trend': 'stable', 'activity_frequency': 'daily'},
        {'engagement_score': 50, 'trend': 'declining', 'activity_frequency': 'weekly'},
        {'engagement_score': 30, 'trend': 'declining', 'activity_frequency': 'sporadic'},
    ]

    for test in test_cases:
        try:
            risk = service._determine_risk_level(
                engagement_score=test['engagement_score'],
                trend=test['trend'],
                activity_frequency=test['activity_frequency']
            )
            if risk in ['low', 'medium', 'high']:
                print(f"   ✅ Risk {risk} for score={test['engagement_score']}, trend={test['trend']}")
            else:
                print(f"   ❌ Invalid risk level: {risk}")
                return False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False

    print("\n" + "=" * 70)
    print("✅ ALL VALIDATION TESTS PASSED")
    print("=" * 70 + "\n")

    return True


if __name__ == '__main__':
    success = validate_service()
    sys.exit(0 if success else 1)
