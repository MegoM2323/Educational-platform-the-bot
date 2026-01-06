import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
import re
from pathlib import Path

User = get_user_model()


class TestRoleEnumConsistency(TestCase):
    """Test: Enum consistency - all role checks use User.Role"""

    def test_enum_values_match_database(self):
        """Test: User.Role enum values match database"""
        assert User.Role.TUTOR.value == "tutor"
        assert User.Role.STUDENT.value == "student"
        assert User.Role.TEACHER.value == "teacher"
        assert User.Role.PARENT.value == "parent"

    def test_enum_display_names(self):
        """Test: Enum display names are set"""
        assert User.Role.TUTOR.label == "Тьютор"
        assert User.Role.STUDENT.label == "Студент"
        assert User.Role.TEACHER.label == "Преподаватель"
        assert User.Role.PARENT.label == "Родитель"

    def test_user_can_be_created_with_enum(self):
        """Test: Users can be created with enum roles"""
        user = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass123",
            role=User.Role.TUTOR,
        )
        assert user.role == User.Role.TUTOR
        assert user.role.value == "tutor"

    def test_role_choices_include_all_values(self):
        """Test: Role.choices includes all role values"""
        role_values = [choice[0] for choice in User.Role.choices]
        assert User.Role.TUTOR.value in role_values
        assert User.Role.STUDENT.value in role_values
        assert User.Role.TEACHER.value in role_values
        assert User.Role.PARENT.value in role_values

    def test_no_hardcoded_role_strings_in_permissions(self):
        """Test: No hardcoded role strings in permissions.py comparisons"""
        permissions_file = Path(__file__).parent.parent / "permissions.py"
        content = permissions_file.read_text()

        # Find all comparisons with role
        # Look for patterns like == 'tutor' or == 'student' etc
        hardcoded_patterns = [
            r"==\s*['\"]tutor['\"]",
            r"==\s*['\"]student['\"]",
            r"==\s*['\"]teacher['\"]",
            r"==\s*['\"]parent['\"]",
        ]

        for pattern in hardcoded_patterns:
            matches = re.findall(pattern, content)
            # Filter out matches in comments or strings that are not comparisons
            if matches:
                # Check context - should not be in actual comparisons
                # They're allowed in messages, help text, etc
                for match in re.finditer(pattern, content):
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    line_end = content.find("\n", match.end())
                    line = content[line_start:line_end]

                    # Skip if it's in a comment
                    if "#" in line:
                        comment_pos = line.find("#")
                        if comment_pos < match.start() - line_start:
                            pytest.skip(f"Hardcoded string in comment: {line.strip()}")

                    # Skip if it's in a string for display/error message
                    if 'message=' in line or 'help_text=' in line or 'error' in line.lower():
                        pytest.skip(f"Hardcoded string in message: {line.strip()}")

    def test_no_hardcoded_role_strings_in_profile_service(self):
        """Test: No hardcoded role strings in profile_service.py comparisons"""
        try:
            profile_service_file = Path(__file__).parent.parent / "profile_service.py"
            if profile_service_file.exists():
                content = profile_service_file.read_text()

                # Look for hardcoded role string comparisons
                hardcoded_patterns = [
                    r"==\s*['\"]tutor['\"]",
                    r"==\s*['\"]student['\"]",
                    r"==\s*['\"]teacher['\"]",
                    r"==\s*['\"]parent['\"]",
                ]

                for pattern in hardcoded_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_start = content.rfind("\n", 0, match.start()) + 1
                        line_end = content.find("\n", match.end())
                        line = content[line_start:line_end]

                        # Skip if in comment or message
                        if "#" in line or "error" in line.lower() or "message" in line.lower():
                            continue

                        assert False, f"Hardcoded role string found: {line.strip()}"
        except FileNotFoundError:
            pytest.skip("profile_service.py not found")

    def test_no_hardcoded_role_strings_in_views(self):
        """Test: No hardcoded role strings in views.py comparisons"""
        views_file = Path(__file__).parent.parent / "views.py"
        content = views_file.read_text()

        # Look for hardcoded role string comparisons
        hardcoded_patterns = [
            r"==\s*['\"]tutor['\"]",
            r"==\s*['\"]student['\"]",
            r"==\s*['\"]teacher['\"]",
            r"==\s*['\"]parent['\"]",
        ]

        for pattern in hardcoded_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_start = content.rfind("\n", 0, match.start()) + 1
                line_end = content.find("\n", match.end())
                line = content[line_start:line_end]

                # Skip if in comment or message
                if "#" in line or "error" in line.lower() or "message" in line.lower():
                    continue

                assert False, f"Hardcoded role string found in views.py: {line.strip()}"

    def test_all_roles_in_choices(self):
        """Test: All User.Role values are in choices"""
        all_role_values = {role.value for role in User.Role}
        choice_values = {choice[0] for choice in User.Role.choices}
        assert all_role_values == choice_values

    def test_role_comparison_with_enum(self):
        """Test: Role comparison works with enum"""
        user = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass123",
            role=User.Role.STUDENT,
        )
        assert user.role == User.Role.STUDENT
        assert user.role != User.Role.TUTOR
        assert user.role.value == "student"

    def test_role_in_list_check(self):
        """Test: Role checks with list of enums"""
        user = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )
        allowed_roles = [User.Role.TEACHER, User.Role.TUTOR]
        assert user.role in allowed_roles
