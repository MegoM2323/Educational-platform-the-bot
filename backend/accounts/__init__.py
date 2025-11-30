"""
Приложение accounts для управления пользователями и профилями.

Модули:
- models.py: User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
- signals.py: Django signals для аудит-логирования (инициализируется в apps.py)
- retry_logic.py: Retry логика для Supabase sync операций
- staff_views.py: API endpoints для управления пользователями (admin)
"""

default_app_config = 'accounts.apps.AccountsConfig'
