"""
Simple security tests for Material file upload handling.

Tests without Django setup required:
- File size validation
- MIME type validation
- Path traversal prevention
- Filename sanitization
- File hash calculation
"""

import sys
from io import BytesIO

# Add backend to path for imports
sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from materials.utils import FileAuditLogger, MaterialFileValidator


def test_validate_file_size_document():
    """Test document file size validation (50MB limit)"""
    # Create file just under limit - should pass
    content = b"x" * (49 * 1024 * 1024)
    file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

    try:
        MaterialFileValidator.validate_file_size(file, file_type="document")
        print("✓ test_validate_file_size_document: PASSED")
    except Exception as e:
        print(f"✗ test_validate_file_size_document: FAILED - {e}")


def test_validate_file_size_exceeds_document_limit():
    """Test document file size exceeds limit"""
    # Create file over 50MB limit
    content = b"x" * (51 * 1024 * 1024)
    file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

    try:
        MaterialFileValidator.validate_file_size(file, file_type="document")
        print("✗ test_validate_file_size_exceeds_document_limit: FAILED - Should have raised ValidationError")
    except ValidationError as e:
        if "exceeds maximum" in str(e) and "50MB" in str(e):
            print("✓ test_validate_file_size_exceeds_document_limit: PASSED")
        else:
            print(f"✗ test_validate_file_size_exceeds_document_limit: FAILED - Wrong error: {e}")


def test_validate_file_extension_allowed():
    """Test file extension validation - allowed type"""
    try:
        ext = MaterialFileValidator.validate_file_extension("document.pdf", file_type="document")
        if ext == "pdf":
            print("✓ test_validate_file_extension_allowed: PASSED")
        else:
            print(f"✗ test_validate_file_extension_allowed: FAILED - Expected 'pdf', got '{ext}'")
    except Exception as e:
        print(f"✗ test_validate_file_extension_allowed: FAILED - {e}")


def test_validate_file_extension_not_allowed():
    """Test file extension validation - not allowed type"""
    try:
        MaterialFileValidator.validate_file_extension("script.exe", file_type="document")
        print("✗ test_validate_file_extension_not_allowed: FAILED - Should have raised ValidationError")
    except ValidationError as e:
        if "not allowed" in str(e):
            print("✓ test_validate_file_extension_not_allowed: PASSED")
        else:
            print(f"✗ test_validate_file_extension_not_allowed: FAILED - Wrong error: {e}")


def test_validate_file_extension_no_extension():
    """Test file without extension"""
    try:
        MaterialFileValidator.validate_file_extension("filewithoutext", file_type="document")
        print("✗ test_validate_file_extension_no_extension: FAILED - Should have raised ValidationError")
    except ValidationError as e:
        if "must have an extension" in str(e):
            print("✓ test_validate_file_extension_no_extension: PASSED")
        else:
            print(f"✗ test_validate_file_extension_no_extension: FAILED - Wrong error: {e}")


def test_sanitize_filename_removes_path():
    """Test filename sanitization rejects directory paths (security improvement)"""
    # Note: sanitize_filename now REJECTS path traversal attempts rather than silently removing them
    # This is more secure as it alerts the user that something is wrong with their upload
    try:
        MaterialFileValidator.sanitize_filename("../../etc/passwd.txt")
        print("✗ test_sanitize_filename_removes_path: FAILED - Should have raised ValidationError for path traversal")
    except ValidationError as e:
        if "invalid" in str(e):
            print("✓ test_sanitize_filename_removes_path: PASSED (correctly rejects path traversal)")
        else:
            print(f"✗ test_sanitize_filename_removes_path: FAILED - Wrong error: {e}")


def test_sanitize_filename_removes_special_chars():
    """Test filename sanitization removes special characters"""
    try:
        result = MaterialFileValidator.sanitize_filename("file<>:|?.txt")
        if "<" not in result and ">" not in result and ":" not in result and "|" not in result and "?" not in result:
            print("✓ test_sanitize_filename_removes_special_chars: PASSED")
        else:
            print(f"✗ test_sanitize_filename_removes_special_chars: FAILED - Result: {result}")
    except Exception as e:
        print(f"✗ test_sanitize_filename_removes_special_chars: FAILED - {e}")


def test_sanitize_filename_removes_hidden_file():
    """Test filename sanitization rejects hidden files"""
    try:
        MaterialFileValidator.sanitize_filename(".bashrc")
        print("✗ test_sanitize_filename_removes_hidden_file: FAILED - Should have raised ValidationError")
    except ValidationError as e:
        if "invalid" in str(e):
            print("✓ test_sanitize_filename_removes_hidden_file: PASSED")
        else:
            print(f"✗ test_sanitize_filename_removes_hidden_file: FAILED - Wrong error: {e}")


def test_sanitize_filename_windows_reserved():
    """Test filename sanitization rejects Windows reserved names"""
    try:
        MaterialFileValidator.sanitize_filename("CON.txt")
        print("✗ test_sanitize_filename_windows_reserved (CON): FAILED - Should have raised ValidationError")
    except ValidationError:
        print("✓ test_sanitize_filename_windows_reserved (CON): PASSED")

    try:
        MaterialFileValidator.sanitize_filename("PRN.pdf")
        print("✗ test_sanitize_filename_windows_reserved (PRN): FAILED - Should have raised ValidationError")
    except ValidationError:
        print("✓ test_sanitize_filename_windows_reserved (PRN): PASSED")


def test_generate_safe_filename_contains_timestamp():
    """Test safe filename generation includes timestamp"""
    try:
        filename = MaterialFileValidator.generate_safe_filename("document.pdf")
        if "_" in filename and ".pdf" in filename and len(filename) > 10:
            print("✓ test_generate_safe_filename_contains_timestamp: PASSED")
        else:
            print(f"✗ test_generate_safe_filename_contains_timestamp: FAILED - Result: {filename}")
    except Exception as e:
        print(f"✗ test_generate_safe_filename_contains_timestamp: FAILED - {e}")


def test_generate_safe_filename_unique():
    """Test safe filename generation creates unique names"""
    try:
        filename1 = MaterialFileValidator.generate_safe_filename("document.pdf")
        filename2 = MaterialFileValidator.generate_safe_filename("document.pdf")

        if filename1 != filename2:
            print("✓ test_generate_safe_filename_unique: PASSED")
        else:
            print(f"✗ test_generate_safe_filename_unique: FAILED - Names are the same: {filename1}")
    except Exception as e:
        print(f"✗ test_generate_safe_filename_unique: FAILED - {e}")


def test_generate_safe_filename_length():
    """Test safe filename generation respects length limits"""
    try:
        long_name = "a" * 300 + ".pdf"
        filename = MaterialFileValidator.generate_safe_filename(long_name)

        if len(filename) <= 255:
            print("✓ test_generate_safe_filename_length: PASSED")
        else:
            print(f"✗ test_generate_safe_filename_length: FAILED - Length {len(filename)} > 255")
    except Exception as e:
        print(f"✗ test_generate_safe_filename_length: FAILED - {e}")


def test_scan_file_signature_executable():
    """Test file signature scanning detects executables"""
    try:
        content = b"MZ" + b"x" * 100
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        MaterialFileValidator.scan_file_signature(file)
        print("✗ test_scan_file_signature_executable: FAILED - Should have raised ValidationError")
    except ValidationError as e:
        if "executable" in str(e).lower():
            print("✓ test_scan_file_signature_executable: PASSED")
        else:
            print(f"✗ test_scan_file_signature_executable: FAILED - Wrong error: {e}")


def test_scan_file_signature_shell_script():
    """Test file signature scanning detects shell scripts"""
    try:
        content = b"#!/bin/bash" + b"x" * 100
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        MaterialFileValidator.scan_file_signature(file)
        print("✗ test_scan_file_signature_shell_script: FAILED - Should have raised ValidationError")
    except ValidationError as e:
        if "executable or script" in str(e).lower():
            print("✓ test_scan_file_signature_shell_script: PASSED")
        else:
            print(f"✗ test_scan_file_signature_shell_script: FAILED - Wrong error: {e}")


def test_scan_file_signature_safe_file():
    """Test file signature scanning allows safe files"""
    try:
        content = b"%PDF-1.4" + b"x" * 100
        file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")

        result = MaterialFileValidator.scan_file_signature(file)
        if result is True:
            print("✓ test_scan_file_signature_safe_file: PASSED")
        else:
            print(f"✗ test_scan_file_signature_safe_file: FAILED - Result: {result}")
    except Exception as e:
        print(f"✗ test_scan_file_signature_safe_file: FAILED - {e}")


def test_calculate_file_hash():
    """Test file hash calculation"""
    try:
        content = b"test file content"
        file = SimpleUploadedFile("test.txt", content)

        hash_value = FileAuditLogger.calculate_file_hash(file)

        # Should be SHA256 hex (64 chars)
        if len(hash_value) == 64 and all(c in "0123456789abcdef" for c in hash_value):
            print("✓ test_calculate_file_hash: PASSED")
        else:
            print(f"✗ test_calculate_file_hash: FAILED - Invalid hash: {hash_value}")
    except Exception as e:
        print(f"✗ test_calculate_file_hash: FAILED - {e}")


def test_calculate_file_hash_consistent():
    """Test file hash is consistent"""
    try:
        content = b"test file content"
        file1 = SimpleUploadedFile("test.txt", content)
        file2 = SimpleUploadedFile("test.txt", content)

        hash1 = FileAuditLogger.calculate_file_hash(file1)
        hash2 = FileAuditLogger.calculate_file_hash(file2)

        if hash1 == hash2:
            print("✓ test_calculate_file_hash_consistent: PASSED")
        else:
            print(f"✗ test_calculate_file_hash_consistent: FAILED - Different hashes: {hash1} vs {hash2}")
    except Exception as e:
        print(f"✗ test_calculate_file_hash_consistent: FAILED - {e}")


def test_calculate_file_hash_different_content():
    """Test file hash differs for different content"""
    try:
        file1 = SimpleUploadedFile("test.txt", b"content1")
        file2 = SimpleUploadedFile("test.txt", b"content2")

        hash1 = FileAuditLogger.calculate_file_hash(file1)
        hash2 = FileAuditLogger.calculate_file_hash(file2)

        if hash1 != hash2:
            print("✓ test_calculate_file_hash_different_content: PASSED")
        else:
            print(f"✗ test_calculate_file_hash_different_content: FAILED - Same hash for different content")
    except Exception as e:
        print(f"✗ test_calculate_file_hash_different_content: FAILED - {e}")


def test_path_traversal_attack_double_dot():
    """Test prevention of ../ path traversal"""
    try:
        MaterialFileValidator.sanitize_filename("../../../etc/passwd.txt")
        print("✗ test_path_traversal_attack_double_dot: FAILED - Should have raised ValidationError")
    except ValidationError:
        print("✓ test_path_traversal_attack_double_dot: PASSED")


def test_path_traversal_attack_backslash():
    """Test prevention of backslash traversal"""
    try:
        MaterialFileValidator.sanitize_filename("..\\..\\windows\\system32.txt")
        print("✗ test_path_traversal_attack_backslash: FAILED - Should have raised ValidationError")
    except ValidationError:
        print("✓ test_path_traversal_attack_backslash: PASSED")


def test_path_traversal_attack_absolute():
    """Test prevention of absolute path attacks"""
    try:
        MaterialFileValidator.sanitize_filename("/etc/passwd.txt")
        print("✗ test_path_traversal_attack_absolute: FAILED - Should have raised ValidationError")
    except ValidationError:
        print("✓ test_path_traversal_attack_absolute: PASSED")


def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("MATERIAL FILE UPLOAD SECURITY TESTS")
    print("=" * 70)

    # File size tests
    print("\n[File Size Validation]")
    test_validate_file_size_document()
    test_validate_file_size_exceeds_document_limit()

    # Extension tests
    print("\n[File Extension Validation]")
    test_validate_file_extension_allowed()
    test_validate_file_extension_not_allowed()
    test_validate_file_extension_no_extension()

    # Filename sanitization tests
    print("\n[Filename Sanitization]")
    test_sanitize_filename_removes_path()
    test_sanitize_filename_removes_special_chars()
    test_sanitize_filename_removes_hidden_file()
    test_sanitize_filename_windows_reserved()

    # Safe filename generation tests
    print("\n[Safe Filename Generation]")
    test_generate_safe_filename_contains_timestamp()
    test_generate_safe_filename_unique()
    test_generate_safe_filename_length()

    # File signature scanning tests
    print("\n[File Signature Scanning]")
    test_scan_file_signature_executable()
    test_scan_file_signature_shell_script()
    test_scan_file_signature_safe_file()

    # File hashing tests
    print("\n[File Hashing]")
    test_calculate_file_hash()
    test_calculate_file_hash_consistent()
    test_calculate_file_hash_different_content()

    # Path traversal tests
    print("\n[Path Traversal Prevention]")
    test_path_traversal_attack_double_dot()
    test_path_traversal_attack_backslash()
    test_path_traversal_attack_absolute()

    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    import django
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    run_all_tests()
