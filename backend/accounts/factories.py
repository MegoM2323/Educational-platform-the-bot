"""
Account factories for test data generation
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

def _get_user_model():
    return get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances"""
    class Meta:
        model = _get_user_model

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = 'testpass123!'
    role = 'student'
    is_active = True
    is_verified = False
    phone = '+79991234567'
    telegram_id = None
    created_by_tutor = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default _create to handle password hashing"""
        manager = cls._get_manager(model_class)
        password = kwargs.pop('password', None)
        obj = manager.create(*args, **kwargs)
        if password:
            obj.set_password(password)
            obj.save(update_fields=['password'])
        return obj


class StudentFactory(DjangoModelFactory):
    """Factory for creating Student User instances"""
    class Meta:
        model = _get_user_model

    username = factory.Sequence(lambda n: f'student{n}')
    email = factory.Sequence(lambda n: f'student{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = 'testpass123!'
    role = 'student'
    is_active = True
    is_verified = False
    phone = '+79991234567'
    telegram_id = None
    created_by_tutor = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        password = kwargs.pop('password', None)
        obj = manager.create(*args, **kwargs)
        if password:
            obj.set_password(password)
            obj.save(update_fields=['password'])
        return obj


class TeacherFactory(DjangoModelFactory):
    """Factory for creating Teacher User instances"""
    class Meta:
        model = _get_user_model

    username = factory.Sequence(lambda n: f'teacher{n}')
    email = factory.Sequence(lambda n: f'teacher{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = 'testpass123!'
    role = 'teacher'
    is_active = True
    is_verified = False
    phone = '+79991234567'
    telegram_id = None
    created_by_tutor = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        password = kwargs.pop('password', None)
        obj = manager.create(*args, **kwargs)
        if password:
            obj.set_password(password)
            obj.save(update_fields=['password'])
        return obj


class TutorFactory(DjangoModelFactory):
    """Factory for creating Tutor User instances"""
    class Meta:
        model = _get_user_model

    username = factory.Sequence(lambda n: f'tutor{n}')
    email = factory.Sequence(lambda n: f'tutor{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = 'testpass123!'
    role = 'tutor'
    is_active = True
    is_verified = False
    phone = '+79991234567'
    telegram_id = None
    created_by_tutor = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        password = kwargs.pop('password', None)
        obj = manager.create(*args, **kwargs)
        if password:
            obj.set_password(password)
            obj.save(update_fields=['password'])
        return obj


class ParentFactory(DjangoModelFactory):
    """Factory for creating Parent User instances"""
    class Meta:
        model = _get_user_model

    username = factory.Sequence(lambda n: f'parent{n}')
    email = factory.Sequence(lambda n: f'parent{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = 'testpass123!'
    role = 'parent'
    is_active = True
    is_verified = False
    phone = '+79991234567'
    telegram_id = None
    created_by_tutor = None

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        password = kwargs.pop('password', None)
        obj = manager.create(*args, **kwargs)
        if password:
            obj.set_password(password)
            obj.save(update_fields=['password'])
        return obj


def _get_student_profile_model():
    from accounts.models import StudentProfile
    return StudentProfile


def _get_teacher_profile_model():
    from accounts.models import TeacherProfile
    return TeacherProfile


def _get_tutor_profile_model():
    from accounts.models import TutorProfile
    return TutorProfile


def _get_parent_profile_model():
    from accounts.models import ParentProfile
    return ParentProfile


class StudentProfileFactory(DjangoModelFactory):
    """Factory for creating StudentProfile instances"""
    class Meta:
        model = _get_student_profile_model

    user = factory.SubFactory(StudentFactory)
    grade = 10
    goal = factory.Faker('text', max_nb_chars=200)
    tutor = None
    parent = None
    progress_percentage = 0
    streak_days = 0
    total_points = 0
    accuracy_percentage = 0


class TeacherProfileFactory(DjangoModelFactory):
    """Factory for creating TeacherProfile instances"""
    class Meta:
        model = _get_teacher_profile_model

    user = factory.SubFactory(TeacherFactory)
    subject = factory.Faker('word')
    experience_years = 5
    bio = factory.Faker('text', max_nb_chars=200)


class TutorProfileFactory(DjangoModelFactory):
    """Factory for creating TutorProfile instances"""
    class Meta:
        model = _get_tutor_profile_model

    user = factory.SubFactory(TutorFactory)
    specialization = factory.Faker('word')
    hourly_rate = 50.00
    bio = factory.Faker('text', max_nb_chars=200)


class ParentProfileFactory(DjangoModelFactory):
    """Factory for creating ParentProfile instances"""
    class Meta:
        model = _get_parent_profile_model

    user = factory.SubFactory(ParentFactory)
    phone = factory.Faker('phone_number')
    children_count = 1
