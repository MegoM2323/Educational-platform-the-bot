"""
Account factories for test data generation
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances"""
    class Meta:
        model = User

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
