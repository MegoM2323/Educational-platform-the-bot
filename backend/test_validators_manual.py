"""
Manual test script for validators (can be run without Django setup)
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers
from materials.validators import (
    validate_file_type,
    validate_file_size,
    validate_title_length,
    validate_description_length,
    MaterialFileValidator
)

def test_validators():
    print("Testing Material Form Validators...")
    print("=" * 60)

    # Test 1: File type validation - allowed
    print("\n1. Testing file type validation - allowed extensions:")
    for ext in ['pdf', 'docx', 'mp4', 'mp3']:
        try:
            file_obj = SimpleUploadedFile(f"test.{ext}", b"content")
            validate_file_type(file_obj)
            print(f"   ✓ .{ext} - PASSED")
        except Exception as e:
            print(f"   ✗ .{ext} - FAILED: {e}")

    # Test 2: File type validation - disallowed
    print("\n2. Testing file type validation - disallowed extensions:")
    for ext in ['exe', 'bat']:
        try:
            file_obj = SimpleUploadedFile(f"test.{ext}", b"content")
            validate_file_type(file_obj)
            print(f"   ✗ .{ext} - FAILED: Should have raised ValidationError")
        except serializers.ValidationError as e:
            print(f"   ✓ .{ext} - PASSED (correctly rejected)")

    # Test 3: File size validation - within limit
    print("\n3. Testing file size validation - within 50MB:")
    try:
        file_obj = SimpleUploadedFile("test.pdf", b"x" * (1024 * 1024))  # 1MB
        validate_file_size(file_obj)
        print(f"   ✓ 1MB file - PASSED")
    except Exception as e:
        print(f"   ✗ 1MB file - FAILED: {e}")

    # Test 4: File size validation - over limit
    print("\n4. Testing file size validation - over 50MB:")
    try:
        file_obj = SimpleUploadedFile("test.pdf", b"x" * (51 * 1024 * 1024))  # 51MB
        validate_file_size(file_obj)
        print(f"   ✗ 51MB file - FAILED: Should have raised ValidationError")
    except serializers.ValidationError as e:
        print(f"   ✓ 51MB file - PASSED (correctly rejected)")

    # Test 5: Title length validation
    print("\n5. Testing title length validation:")
    test_cases = [
        ("Valid Title", True),
        ("a" * 200, True),
        ("a" * 201, False),
        ("ab", False),
    ]
    for title, should_pass in test_cases:
        try:
            validate_title_length(title)
            if should_pass:
                print(f"   ✓ '{title[:20]}...' ({len(title)} chars) - PASSED")
            else:
                print(f"   ✗ '{title[:20]}...' ({len(title)} chars) - FAILED: Should have raised")
        except serializers.ValidationError:
            if not should_pass:
                print(f"   ✓ '{title[:20]}...' ({len(title)} chars) - PASSED (correctly rejected)")
            else:
                print(f"   ✗ '{title[:20]}...' ({len(title)} chars) - FAILED: Unexpected error")

    # Test 6: Description length validation
    print("\n6. Testing description length validation:")
    test_cases = [
        ("Valid description", True),
        ("a" * 5000, True),
        ("a" * 5001, False),
        ("", True),  # Empty is OK
    ]
    for desc, should_pass in test_cases:
        try:
            validate_description_length(desc)
            if should_pass:
                print(f"   ✓ Description ({len(desc)} chars) - PASSED")
            else:
                print(f"   ✗ Description ({len(desc)} chars) - FAILED: Should have raised")
        except serializers.ValidationError:
            if not should_pass:
                print(f"   ✓ Description ({len(desc)} chars) - PASSED (correctly rejected)")
            else:
                print(f"   ✗ Description ({len(desc)} chars) - FAILED: Unexpected error")

    # Test 7: MaterialFileValidator
    print("\n7. Testing MaterialFileValidator class:")
    print(f"   Allowed extensions: {len(MaterialFileValidator.ALLOWED_EXTENSIONS)} types")
    print(f"   Max file size: {MaterialFileValidator.MAX_FILE_SIZE / (1024*1024):.0f}MB")

    # Test validation
    try:
        valid_file = SimpleUploadedFile("test.pdf", b"x" * (1024 * 1024))
        MaterialFileValidator.validate(valid_file)
        print(f"   ✓ Valid file (pdf, 1MB) - PASSED")
    except Exception as e:
        print(f"   ✗ Valid file - FAILED: {e}")

    print("\n" + "=" * 60)
    print("✓ All validator tests completed!")
    print("=" * 60)

if __name__ == '__main__':
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    os.environ['ENVIRONMENT'] = 'test'
    django.setup()
    test_validators()
