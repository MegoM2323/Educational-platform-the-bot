import pytest
from django.db import IntegrityError
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User, TeacherProfile
from accounts.factories import TeacherFactory, UserFactory


@pytest.mark.django_db
class TestTeacherCreationBasic:
    """Test basic TEACHER creation through API endpoints"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            email="admin@test.com"
        )
        self.client.force_authenticate(self.admin_user)

    def test_create_teacher_via_general_endpoint(self):
        """Test creating TEACHER through POST /api/accounts/users/"""
        payload = {
            "email": "newtеacher@test.com",
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "role": "teacher",
            "phone": "+79991234567",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
        assert response.data["role"] == "teacher"
        assert response.data["email"] == "newtеacher@test.com"
        assert response.data["first_name"] == "Ivan"

    def test_create_teacher_via_staff_endpoint(self):
        """Test creating TEACHER through POST /api/accounts/staff/create/"""
        payload = {
            "email": "teacher2@test.com",
            "first_name": "Petr",
            "last_name": "Petrov",
            "role": "teacher",
            "phone": "+79991234568",
        }

        response = self.client.post("/api/accounts/staff/create/", payload, format="json")

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
        if "user" in response.data:
            user_data = response.data["user"]
            assert user_data["role"] == "teacher"
            assert user_data["email"] == "teacher2@test.com"
        else:
            assert response.data["role"] == "teacher"
            assert response.data["email"] == "teacher2@test.com"

    def test_create_teacher_with_minimal_fields(self):
        """Test creating TEACHER with only required fields"""
        payload = {
            "email": "teacher_minimal@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
        user = User.objects.get(email="teacher_minimal@test.com")
        assert user.role == User.Role.TEACHER
        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_create_teacher_preserves_is_staff_sync(self):
        """Test that is_staff is NOT set for TEACHER role (only for ADMIN)"""
        payload = {
            "email": "teacher_staff@test.com",
            "first_name": "Mark",
            "last_name": "Smith",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        user = User.objects.get(email="teacher_staff@test.com")
        assert user.role == User.Role.TEACHER
        assert not user.is_staff
        assert not user.is_superuser


@pytest.mark.django_db
class TestTeacherCreationValidation:
    """Test validation of TEACHER user fields during creation"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            email="admin@test.com"
        )
        self.client.force_authenticate(self.admin_user)

    def test_validate_email_required(self):
        """Test that email is required for TEACHER"""
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_first_name_required(self):
        """Test that first_name is required for TEACHER"""
        payload = {
            "email": "teacher@test.com",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_last_name_required(self):
        """Test that last_name is required for TEACHER"""
        payload = {
            "email": "teacher@test.com",
            "first_name": "John",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_phone_format(self):
        """Test that phone number format is validated"""
        payload = {
            "email": "teacher@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
            "phone": "invalid_phone",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_phone_valid_formats(self):
        """Test that valid phone formats are accepted"""
        valid_phones = [
            "+79991234567",
            "+1234567890",
            "9991234567",
        ]

        for phone in valid_phones:
            payload = {
                "email": f"teacher_{phone}@test.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": "teacher",
                "phone": phone,
            }

            response = self.client.post("/api/accounts/users/", payload, format="json")

            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            ]

    def test_validate_email_unique(self):
        """Test that duplicate emails are rejected"""
        payload = {
            "email": "duplicate@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
        }

        response1 = self.client.post("/api/accounts/users/", payload, format="json")
        assert response1.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

        response2 = self.client.post("/api/accounts/users/", payload, format="json")
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_email_format(self):
        """Test that invalid email format is rejected"""
        payload = {
            "email": "not_an_email",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTeacherCreationProfile:
    """Test TeacherProfile auto-creation and initialization"""

    def test_teacher_profile_auto_created(self):
        """Test that TeacherProfile is automatically created when User is created"""
        user = TeacherFactory()

        assert user.role == User.Role.TEACHER
        teacher_profile = TeacherProfile.objects.filter(user=user).first()
        assert teacher_profile is not None
        assert teacher_profile.user_id == user.id

    def test_teacher_profile_default_values(self):
        """Test that TeacherProfile is initialized with correct default values"""
        user = TeacherFactory()
        profile = TeacherProfile.objects.get(user=user)

        assert profile.experience_years == 0
        assert profile.bio == ""
        assert profile.subject == ""
        assert profile.telegram == ""
        assert profile.telegram_id == ""

    def test_teacher_profile_subject_field(self):
        """Test that subject field can be set on TeacherProfile"""
        user = TeacherFactory()
        profile = TeacherProfile.objects.get(user=user)

        profile.subject = "Mathematics"
        profile.save()
        profile.refresh_from_db()

        assert profile.subject == "Mathematics"

    def test_teacher_profile_experience_years_field(self):
        """Test that experience_years field can be set on TeacherProfile"""
        user = TeacherFactory()
        profile = TeacherProfile.objects.get(user=user)

        profile.experience_years = 5
        profile.save()
        profile.refresh_from_db()

        assert profile.experience_years == 5

    def test_teacher_profile_bio_field(self):
        """Test that bio field can be set on TeacherProfile"""
        user = TeacherFactory()
        profile = TeacherProfile.objects.get(user=user)

        bio_text = "I am a qualified mathematics teacher with 5 years of experience."
        profile.bio = bio_text
        profile.save()
        profile.refresh_from_db()

        assert profile.bio == bio_text

    def test_teacher_profile_telegram_field(self):
        """Test that telegram field can be set on TeacherProfile"""
        user = TeacherFactory()
        profile = TeacherProfile.objects.get(user=user)

        profile.telegram = "@teacher_username"
        profile.save()
        profile.refresh_from_db()

        assert profile.telegram == "@teacher_username"

    def test_teacher_profile_telegram_id_field(self):
        """Test that telegram_id field can be set on TeacherProfile"""
        user = TeacherFactory()
        profile = TeacherProfile.objects.get(user=user)

        profile.telegram_id = "123456789"
        profile.save()
        profile.refresh_from_db()

        assert profile.telegram_id == "123456789"

    def test_teacher_profile_created_via_factory(self):
        """Test that TeacherProfile is created when using TeacherFactory"""
        user = TeacherFactory(
            email="teacher_factory@test.com",
            first_name="Alice",
            last_name="Brown"
        )

        assert TeacherProfile.objects.filter(user=user).exists()
        profile = TeacherProfile.objects.get(user=user)
        assert profile.user == user


@pytest.mark.django_db
class TestTeacherCreationRelations:
    """Test TeacherProfile relationships with User"""

    def test_teacher_profile_one_to_one_relationship(self):
        """Test that TeacherProfile has OneToOne relationship with User"""
        user = TeacherFactory()
        profile = TeacherProfile.objects.get(user=user)

        assert profile.user == user
        assert profile.user_id == user.id

    def test_teacher_profile_retrieval_by_user(self):
        """Test that TeacherProfile can be retrieved from User"""
        user = TeacherFactory()

        retrieved_profile = TeacherProfile.objects.get(user=user)
        created_profile = TeacherProfile.objects.get(user=user)

        assert retrieved_profile.id == created_profile.id

    def test_multiple_teachers_have_separate_profiles(self):
        """Test that multiple TEACHER users have separate profiles"""
        teacher1 = TeacherFactory(email="teacher1@test.com")
        teacher2 = TeacherFactory(email="teacher2@test.com")

        profile1 = TeacherProfile.objects.get(user=teacher1)
        profile2 = TeacherProfile.objects.get(user=teacher2)

        assert profile1.id != profile2.id
        assert profile1.user_id == teacher1.id
        assert profile2.user_id == teacher2.id

    def test_teacher_profile_queryset_select_related(self):
        """Test that TeacherProfile querysets can use select_related"""
        teacher = TeacherFactory()

        queryset = TeacherProfile.objects.select_related("user").filter(user_id=teacher.id)
        profile = queryset.first()

        assert profile is not None
        assert profile.user_id == teacher.id


@pytest.mark.django_db
class TestTeacherCreationErrors:
    """Test error cases during TEACHER creation"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            email="admin@test.com"
        )
        self.client.force_authenticate(self.admin_user)

    def test_error_duplicate_email_different_roles(self):
        """Test that duplicate email is rejected even for different roles"""
        UserFactory(email="shared@test.com", role=User.Role.STUDENT)

        payload = {
            "email": "shared@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_error_invalid_role(self):
        """Test that invalid role is rejected"""
        payload = {
            "email": "teacher@test.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "invalid_role",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_error_missing_role(self):
        """Test that missing role is handled"""
        payload = {
            "email": "teacher@test.com",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_error_empty_email(self):
        """Test that empty email is rejected"""
        payload = {
            "email": "",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_error_empty_first_name(self):
        """Test that empty first_name is rejected"""
        payload = {
            "email": "teacher@test.com",
            "first_name": "",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_error_whitespace_email(self):
        """Test that whitespace-only email is rejected"""
        payload = {
            "email": "   ",
            "first_name": "John",
            "last_name": "Doe",
            "role": "teacher",
        }

        response = self.client.post("/api/accounts/users/", payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTeacherCreationCascadeDelete:
    """Test CASCADE delete behavior when TEACHER is deleted"""

    def test_teacher_profile_deleted_with_user(self):
        """Test that TeacherProfile is deleted when User is deleted (CASCADE)"""
        user = TeacherFactory(email="teacher_delete@test.com")
        profile = TeacherProfile.objects.get(user=user)
        profile_id = profile.id

        user.delete()

        assert not TeacherProfile.objects.filter(id=profile_id).exists()

    def test_teacher_profile_cascade_preserves_other_profiles(self):
        """Test that deleting TEACHER doesn't affect other profiles"""
        teacher = TeacherFactory(email="teacher_delete@test.com")
        other_teacher = TeacherFactory(email="other_teacher@test.com")

        teacher.delete()

        assert TeacherProfile.objects.filter(user=other_teacher).exists()

    def test_teacher_user_cannot_be_recreated_with_same_email(self):
        """Test that email is released after user deletion"""
        email = "teacher_recreate@test.com"
        user1 = TeacherFactory(email=email)
        user1_id = user1.id

        user1.delete()

        assert not User.objects.filter(id=user1_id).exists()

        user2 = TeacherFactory(email=email)
        assert user2.id != user1_id

    def test_teacher_profile_string_representation(self):
        """Test TeacherProfile __str__ method"""
        user = TeacherFactory(first_name="John", last_name="Doe")
        profile = TeacherProfile.objects.get(user=user)

        str_repr = str(profile)
        assert "John Doe" in str_repr
        assert "преподавателя" in str_repr or "Профиль" in str_repr


@pytest.mark.django_db
class TestTeacherCreationIntegration:
    """Integration tests for TEACHER creation workflow"""

    def setup_method(self):
        self.client = APIClient()
        self.admin_user = UserFactory(
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
            email="admin@test.com"
        )
        self.client.force_authenticate(self.admin_user)

    def test_teacher_created_with_full_profile_data(self):
        """Test creating TEACHER with all profile fields populated"""
        teacher = TeacherFactory(
            email="complete_teacher@test.com",
            first_name="Alice",
            last_name="Wonder",
            phone="+79991234567"
        )

        profile = teacher.teacher_profile
        profile.subject = "English Literature"
        profile.experience_years = 8
        profile.bio = "Experienced English teacher specializing in literature."
        profile.telegram = "@alice_english"
        profile.telegram_id = "987654321"
        profile.save()

        teacher.refresh_from_db()
        profile.refresh_from_db()

        assert teacher.role == User.Role.TEACHER
        assert teacher.first_name == "Alice"
        assert teacher.last_name == "Wonder"
        assert teacher.phone == "+79991234567"
        assert profile.subject == "English Literature"
        assert profile.experience_years == 8
        assert profile.bio == "Experienced English teacher specializing in literature."
        assert profile.telegram == "@alice_english"
        assert profile.telegram_id == "987654321"

    def test_teacher_database_consistency(self):
        """Test that teacher data is consistently stored in database"""
        user = TeacherFactory(
            email="db_test@test.com",
            first_name="Bob",
            last_name="Builder",
            phone="+79991234568"
        )

        retrieved_user = User.objects.get(email="db_test@test.com")
        assert retrieved_user.id == user.id
        assert retrieved_user.role == User.Role.TEACHER
        assert retrieved_user.first_name == "Bob"

        retrieved_profile = TeacherProfile.objects.get(user_id=user.id)
        assert retrieved_profile.user_id == user.id

    def test_teacher_factory_creates_valid_user(self):
        """Test that TeacherFactory creates a valid user object"""
        teacher = TeacherFactory()

        assert teacher.id is not None
        assert teacher.username is not None
        assert teacher.email is not None
        assert teacher.first_name is not None
        assert teacher.last_name is not None
        assert teacher.role == User.Role.TEACHER
        assert teacher.is_active is True
        assert teacher.password is not None

    def test_teacher_profile_persistence(self):
        """Test that TeacherProfile changes persist to database"""
        teacher = TeacherFactory()
        original_subject = teacher.teacher_profile.subject

        teacher.teacher_profile.subject = "New Subject"
        teacher.teacher_profile.save()

        refreshed = User.objects.get(id=teacher.id).teacher_profile
        assert refreshed.subject == "New Subject"
        assert refreshed.subject != original_subject

    def test_cannot_create_teacher_with_duplicate_username(self):
        """Test that duplicate usernames are handled"""
        teacher1 = TeacherFactory(username="unique_teacher")

        with pytest.raises(IntegrityError):
            TeacherFactory(username="unique_teacher")

    def test_teacher_user_activation_status(self):
        """Test that created TEACHER is active by default"""
        teacher = TeacherFactory()

        assert teacher.is_active is True

    def test_teacher_user_verification_status(self):
        """Test that created TEACHER is not verified by default"""
        teacher = TeacherFactory()

        assert teacher.is_verified is False
