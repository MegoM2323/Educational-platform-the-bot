# Отчёт о багах: Провалы тестов T025 и T026

**Дата**: 2025-11-26
**QA Engineer**: @qa-code-tester
**Задачи**: T025 (Profile API Tests), T026 (Scheduling API Tests)
**Всего тестов**: 56
**Пройдено**: 26 (46%)
**Провалено**: 18 (32%)
**Ошибки**: 12 (22%)

---

## Bug #1: Фикстуры не устанавливают данные профилей

**Локация**: `backend/tests/unit/accounts/test_profile_views.py:44-111`
**Тесты**:
- `test_student_can_get_own_profile` (line 174)
- `test_teacher_can_get_own_profile` (line 398)
- `test_tutor_can_get_own_profile` (line 642)

**Severity**: high

### Expected Behavior
Фикстуры `student_with_profile`, `teacher_with_profile`, `tutor_with_profile` должны создавать пользователей с заполненными данными профилей:
- StudentProfile: `grade='10'`, `goal='Подготовка к ЕГЭ'`, `telegram='@ivanov'`
- TeacherProfile: `experience_years=5`, `bio='Преподаватель математики'`, `telegram='@petrova'`
- TutorProfile: `experience_years=3`, `bio='Опытный тьютор'`, `specialization='Тьютор по математике'`

### Actual Behavior
Профили создаются через signal `auto_create_user_profile`, который автоматически создаёт профили со значениями по умолчанию:
- StudentProfile: `grade=''`, `goal=''`, `telegram=None`
- TeacherProfile: `experience_years=0`, `bio=''`, `telegram=None`
- TutorProfile: `experience_years=0`, `bio=''`, `specialization=''`

Данные, переданные в `defaults={}` методу `get_or_create()`, игнорируются, т.к. профиль уже существует.

### Test Output
```
tests/unit/accounts/test_profile_views.py:174: in test_student_can_get_own_profile
    assert profile_data['grade'] == '10'
E   AssertionError: assert '' == '10'
```

### Root Cause Analysis
В фикстурах используется `StudentProfile.objects.get_or_create(user=user, defaults={...})`, но профиль уже создан через signal. Метод `get_or_create()` возвращает существующий профиль без применения `defaults`.

### Impact
12 тестов провалены. Невозможно тестировать корректность возврата данных профиля через API.

### Recommendation
**Option 1 (Preferred)**: Обновить профили после создания:
```python
@pytest.fixture
def student_with_profile(db):
    user = User.objects.create_user(
        username='student_test',
        email='student@test.com',
        password='TestPass123!',
        role=User.Role.STUDENT,
        first_name='Иван',
        last_name='Иванов',
        phone='+79001234567'
    )
    # Signal создаёт профиль автоматически
    profile = user.student_profile
    profile.grade = '10'
    profile.goal = 'Подготовка к ЕГЭ'
    profile.telegram = '@ivanov'
    profile.save()
    return user
```

**Option 2**: Отключить signals в тестах и создавать профили вручную.

---

## Bug #2: API возвращает 403 вместо 401 для неавторизованных запросов

**Локация**: `backend/accounts/profile_views.py` (all views)
**Тесты**:
- `test_get_student_profile_unauthenticated` (line 186)
- `test_patch_student_profile_unauthenticated` (line 350)
- `test_get_teacher_profile_unauthenticated` (line 409)
- `test_patch_teacher_profile_unauthenticated` (line 594)
- `test_get_tutor_profile_unauthenticated` (line 654)
- `test_patch_tutor_profile_unauthenticated` (line 811)

**Severity**: medium

### Expected Behavior
Неавторизованные запросы должны возвращать `HTTP 401 Unauthorized`.

### Actual Behavior
API возвращает `HTTP 403 Forbidden`.

### Test Output
```
tests/unit/accounts/test_profile_views.py:186: in test_get_student_profile_unauthenticated
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
E   assert 403 == 401
```

### Root Cause Analysis
Django REST Framework с `permission_classes = [IsAuthenticated]` возвращает 403 для анонимных пользователей, если не настроена аутентификация через Token в `DEFAULT_AUTHENTICATION_CLASSES`.

**Проверка settings.py**:
Возможно, в `REST_FRAMEWORK` настройках отсутствует `TokenAuthentication` или порядок аутентификации некорректен.

### Impact
6 тестов провалены. Клиентское приложение может некорректно обрабатывать ошибки авторизации.

### Recommendation
**Option 1**: Обновить тесты - ожидать 403 вместо 401:
```python
assert response.status_code == status.HTTP_403_FORBIDDEN
```

**Option 2**: Добавить в `config/settings.py`:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    # ...
}
```

**Рекомендация**: Option 1 (изменить тесты). DRF convention: 403 для анонимных, 401 для невалидных credentials.

---

## Bug #3: Email field не обновляется через PATCH API

**Локация**: `backend/accounts/profile_views.py:96-110`
**Тест**: `test_student_can_update_user_fields` (line 244)
**Severity**: medium

### Expected Behavior
PATCH запрос с `email='petrov@test.com'` должен обновить email пользователя.

### Actual Behavior
Email не обновляется. После PATCH остаётся `student@test.com`.

### Test Output
```
tests/unit/accounts/test_profile_views.py:244: in test_student_can_update_user_fields
    assert student_with_profile.email == 'petrov@test.com'
E   AssertionError: assert 'student@test.com' == 'petrov@test.com'
```

### Root Cause Analysis
Возможно, в `UserProfileUpdateSerializer` поле `email` помечено как `read_only=True` или отсутствует в `fields`.

Проверить в `backend/accounts/profile_serializers.py`.

### Impact
1 тест провален. Пользователи не могут изменить email через профиль.

### Recommendation
Проверить сериализатор `UserProfileUpdateSerializer`:
```python
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']  # email должно быть здесь
        # read_only_fields = []  # email НЕ должно быть в read_only
```

Если изменение email должно быть запрещено по бизнес-логике, обновить тест.

---

## Bug #4: Invalid email не вызывает validation error

**Локация**: `backend/accounts/profile_serializers.py` (UserProfileUpdateSerializer)
**Тест**: `test_student_update_invalid_email` (line 327)
**Severity**: medium

### Expected Behavior
PATCH с `email='not-an-email'` должен вернуть `HTTP 400 Bad Request` с validation error.

### Actual Behavior
API возвращает `HTTP 200 OK`, invalid email принимается.

### Test Output
```
tests/unit/accounts/test_profile_views.py:327: in test_student_update_invalid_email
    assert response.status_code == status.HTTP_400_BAD_REQUEST
E   assert 200 == 400
```

### Root Cause Analysis
Сериализатор не валидирует email или email field вообще игнорируется (см. Bug #3).

### Impact
1 тест провален. Возможна запись некорректных email адресов в БД, что нарушит отправку уведомлений.

### Recommendation
Добавить валидацию email в `UserProfileUpdateSerializer`:
```python
from django.core.validators import EmailValidator

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, validators=[EmailValidator()])
    # ...
```

---

## Bug #5: Booking.save() вызывает DoesNotExist для новых объектов

**Локация**: `backend/scheduling/models.py:326`
**Тесты**: 12 тестов с ERROR status (все тесты, использующие `pending_booking` или `confirmed_booking` фикстуры)
**Severity**: critical

### Expected Behavior
Создание нового Booking через `Booking.objects.create()` должно успешно сохраняться в БД.

### Actual Behavior
При создании нового Booking возникает exception:
```
scheduling.models.Booking.DoesNotExist: Booking matching query does not exist.
```

### Test Output
```
tests/unit/scheduling/test_booking_flow.py:111: in pending_booking
    return Booking.objects.create(
scheduling/models.py:326: in save
    old_booking = Booking.objects.get(pk=self.pk)
E   scheduling.models.Booking.DoesNotExist: Booking matching query does not exist.
```

### Reproduction Steps
1. Попытаться создать Booking: `Booking.objects.create(...)`
2. Вызывается `Booking.save()`
3. На line 326: `if not is_new: old_booking = Booking.objects.get(pk=self.pk)`
4. Но проверка `is_new` происходит на line 322, ПОСЛЕ чего на line 326 для новых объектов всё равно происходит вызов `get(pk=None)`

### Affected Code
```python
# backend/scheduling/models.py:320-327
def save(self, *args, **kwargs):
    """Сохранение с обновлением счетчика студентов."""
    is_new = self.pk is None
    old_status = None

    if not is_new:  # <-- Эта проверка корректна
        old_booking = Booking.objects.get(pk=self.pk)  # <-- НО line 326 всё равно выполняется для новых
        old_status = old_booking.status
```

**ОШИБКА**: Код после `if not is_new:` выполняется только для существующих объектов, НО в action fixture происходит что-то другое.

**ПЕРЕОЦЕНКА**: Вероятно, проблема в том, что в фикстуре `pending_booking` и `confirmed_booking` используется `Booking.objects.create()` напрямую, минуя `BookingService`, который должен использоваться для создания бронирований.

### Root Cause Analysis
**Реальная причина**: Логика в `Booking.save()` некорректна или фикстуры должны использовать `BookingService.create_booking()` вместо прямого `Booking.objects.create()`.

**Проверить**:
1. Что делает `BookingService.create_booking()`?
2. Используется ли там другой способ создания?

### Impact
12 тестов с ERROR. Невозможно протестировать booking workflow: confirm, cancel, reschedule.

### Recommendation
**Option 1 (Quick Fix)**: Исправить фикстуры - использовать `BookingService`:
```python
@pytest.fixture
def pending_booking(db, available_time_slot, student_user, subject_math, booking_service):
    """Create pending booking via BookingService"""
    return booking_service.create_booking(
        time_slot=available_time_slot,
        student=student_user,
        subject_id=subject_math.id,
        lesson_topic='Тест урока',
        lesson_notes='Тестовые заметки'
    )
```

**Option 2 (Code Fix)**: Если `Booking.objects.create()` должно работать, исправить логику в `Booking.save()`:
```python
def save(self, *args, **kwargs):
    is_new = self.pk is None
    old_status = None

    if not is_new:
        try:
            old_booking = Booking.objects.get(pk=self.pk)
            old_status = old_booking.status
        except Booking.DoesNotExist:
            # Объект с pk существует, но не найден - странная ситуация
            pass

    super().save(*args, **kwargs)
    # ... rest of code
```

**Рекомендация**: Option 1 (использовать BookingService в тестах).

---

## Summary

### Критические баги (блокируют тесты)
1. **Bug #5**: Booking.save() DoesNotExist - **12 ERROR** тестов
2. **Bug #1**: Фикстуры профилей пустые - **12 FAILED** тестов

### Средние баги (влияют на функциональность)
3. **Bug #2**: 403 вместо 401 - **6 FAILED** тестов (низкий приоритет, можно обновить тесты)
4. **Bug #3**: Email не обновляется - **1 FAILED** тест
5. **Bug #4**: Invalid email принимается - **1 FAILED** тест

### Итоговая статистика
- **Критичные**: 2 бага (24 теста заблокированы)
- **Средние**: 3 бага (8 тестов провалены)
- **Coverage**: 28% (из-за большого количества непротестированного кода)

### Блокирует задачи
- **T026**: Blocked - нельзя протестировать BookingService до исправления Bug #5
- **T025**: Blocked - нельзя протестировать Profile API до исправления Bug #1, #3, #4

### Действия
1. **Немедленно**: Исправить Bug #1 и Bug #5 (критичные)
2. **В следующем спринте**: Исправить Bug #3 и Bug #4 (валидация)
3. **Обсудить с командой**: Bug #2 (401 vs 403 - соглашение DRF)

---

**Отчёт подготовлен**: @qa-code-tester
**Статус**: BLOCKED - ожидание исправлений от @py-backend-dev
