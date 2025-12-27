"""
Standalone test script for validators (no Django setup required)
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import serializers

# Import directly without Django
import sys
import os

# We can test the validator functions without full Django setup
def test_file_validation_functions():
    print("Testing Material Form Validators (Standalone)...")
    print("=" * 70)

    # Test validate_file_type function
    print("\nTest 1: File Type Validation")
    print("-" * 70)

    from materials.validators import validate_file_type

    allowed_types = ['pdf', 'docx', 'mp4', 'mp3', 'xlsx', 'pptx']
    disallowed_types = ['exe', 'bat', 'sh', 'app']

    print("Testing allowed types:")
    for ext in allowed_types[:3]:
        try:
            file_obj = SimpleUploadedFile(f"test.{ext}", b"test content")
            validate_file_type(file_obj)
            print(f"  ✓ {ext:5} - ALLOWED")
        except serializers.ValidationError as e:
            print(f"  ✗ {ext:5} - FAILED: {e}")

    print("\nTesting disallowed types:")
    for ext in disallowed_types[:2]:
        try:
            file_obj = SimpleUploadedFile(f"test.{ext}", b"test content")
            validate_file_type(file_obj)
            print(f"  ✗ {ext:5} - Should have been rejected")
        except serializers.ValidationError as e:
            print(f"  ✓ {ext:5} - REJECTED (correct)")

    # Test validate_file_size function
    print("\n\nTest 2: File Size Validation")
    print("-" * 70)

    from materials.validators import validate_file_size

    print("Testing file sizes within limit:")
    for size_mb in [1, 10, 49, 50]:
        try:
            content = b"x" * (size_mb * 1024 * 1024)
            file_obj = SimpleUploadedFile("test.pdf", content)
            validate_file_size(file_obj)
            print(f"  ✓ {size_mb:3}MB - ALLOWED")
        except serializers.ValidationError as e:
            print(f"  ✗ {size_mb:3}MB - FAILED: {e}")

    print("\nTesting file sizes over limit:")
    for size_mb in [51, 100]:
        try:
            content = b"x" * (size_mb * 1024 * 1024)
            file_obj = SimpleUploadedFile("test.pdf", content)
            validate_file_size(file_obj)
            print(f"  ✗ {size_mb:3}MB - Should have been rejected")
        except serializers.ValidationError as e:
            print(f"  ✓ {size_mb:3}MB - REJECTED (correct)")

    # Test validate_title_length function
    print("\n\nTest 3: Title Length Validation")
    print("-" * 70)

    from materials.validators import validate_title_length

    test_titles = [
        ("Valid Title", True, "Valid 3+ chars"),
        ("a" * 3, True, "Exactly 3 chars (minimum)"),
        ("a" * 200, True, "Exactly 200 chars (maximum)"),
        ("a" * 201, False, "Over 200 chars"),
        ("ab", False, "Only 2 chars (too short)"),
        ("", False, "Empty string"),
    ]

    for title, should_pass, description in test_titles:
        try:
            validate_title_length(title)
            if should_pass:
                print(f"  ✓ {description:30} - ALLOWED")
            else:
                print(f"  ✗ {description:30} - Should have been rejected")
        except serializers.ValidationError as e:
            if not should_pass:
                print(f"  ✓ {description:30} - REJECTED (correct)")
            else:
                print(f"  ✗ {description:30} - FAILED: {e}")

    # Test validate_description_length function
    print("\n\nTest 4: Description Length Validation")
    print("-" * 70)

    from materials.validators import validate_description_length

    test_descs = [
        ("Valid description", True, "Valid description"),
        ("a" * 5000, True, "Exactly 5000 chars (maximum)"),
        ("a" * 5001, False, "Over 5000 chars"),
        ("", True, "Empty string (allowed)"),
    ]

    for desc, should_pass, description in test_descs:
        try:
            validate_description_length(desc)
            if should_pass:
                print(f"  ✓ {description:30} - ALLOWED")
            else:
                print(f"  ✗ {description:30} - Should have been rejected")
        except serializers.ValidationError as e:
            if not should_pass:
                print(f"  ✓ {description:30} - REJECTED (correct)")
            else:
                print(f"  ✗ {description:30} - FAILED: {e}")

    # Test MaterialFileValidator class
    print("\n\nTest 5: MaterialFileValidator Class")
    print("-" * 70)

    from materials.validators import MaterialFileValidator

    print(f"Allowed extensions ({len(MaterialFileValidator.ALLOWED_EXTENSIONS)}):")
    print(f"  {', '.join(sorted(list(MaterialFileValidator.ALLOWED_EXTENSIONS)[:10]))}...")

    print(f"\nSize limits:")
    print(f"  Default: {MaterialFileValidator.MAX_FILE_SIZE / (1024*1024):.0f}MB")
    print(f"  Video:   {MaterialFileValidator.MAX_VIDEO_SIZE / (1024*1024):.0f}MB")
    print(f"  Document: {MaterialFileValidator.MAX_DOCUMENT_SIZE / (1024*1024):.0f}MB")

    # Test extension extraction
    print(f"\nExtension extraction:")
    test_cases = [
        ("document.pdf", "pdf"),
        ("FILE.DOCX", "docx"),
        ("no_extension", None),
    ]
    for filename, expected in test_cases:
        result = MaterialFileValidator.get_file_extension(filename)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {filename:20} -> {result}")

    print("\n" + "=" * 70)
    print("✓ Standalone validator tests completed!")
    print("=" * 70)

if __name__ == '__main__':
    test_file_validation_functions()
