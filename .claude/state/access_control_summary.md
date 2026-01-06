# Анализ системы прав доступа THE_BOT Platform

## Быстрый обзор

**Дата анализа:** 2026-01-07  
**Статус:** Анализ завершен и задокументирован  
**Охват:** 6 приложений backend, 23+ permission классов, 12+ сериализаторов

## Ключевые компоненты

### Permission классы (23 шт.)

#### Accounts (/backend/accounts/permissions.py) - 10 классов
1. **IsOwnerOrReadOnly** - Владелец может редактировать, остальные читают
2. **IsOwnerProfileOrAdmin** - Владелец или админ может редактировать
3. **IsTutorOrAdmin** - Доступ только тьюторам и администраторам
4. **TutorCanManageStudentProfiles** - Тьютор управляет студентами, но НЕ может менять protected fields
5. **CanViewOwnProfileOnly** - Строгое: только свой профиль
6. **IsStudentOwner** - Студент или тьютор могут редактировать StudentProfile
7. **IsStaffOrAdmin** - Только админы (НЕ включает тьюторов)
8. **IsStudent** - Только студенты
9. **IsTeacher** - Только учителя
10. **IsTutor** / **IsParent** - Роль-специфичные

#### Materials (/backend/materials/permissions.py) - 1 класс
- **StudentEnrollmentPermission** - Доступ к материалам только зачисленных предметов

#### Reports (/backend/reports/permissions.py) - 7 классов
- **ReportAccessService** - Централизованная логика доступа к отчетам (view/share/edit)
- **ParentReportPermission** - Родители видят отчеты своих детей (read-only)
- **CanAcknowledgeReport** - Только родители могут подтверждать отчеты
- **CanAccessReport** - Комплексная проверка доступа (direct/token/sharing)
- **CanShareReport** - Только owner или admin
- **CanEditReport** - Только owner или admin
- **IsTeacherOrAdmin** - Учителя могут создавать отчеты

#### Scheduling (/backend/scheduling/permissions.py) - 2 класса
- **IsParentOfStudent** - Родитель имеет доступ к данным своих детей
- **IsTeacherOrStudent** - Учителя и студенты

#### Chat (/backend/chat/permissions.py) - 2 функции
- **check_parent_access_to_room()** - Родитель видит чаты если его ребенок участник
- **check_teacher_access_to_room()** - Учитель видит чаты по enrollment

#### Knowledge Graph (/backend/knowledge_graph/permissions.py) - 3 класса
- **IsTeacherOrAdmin** - Учителя и админы
- **IsGraphOwner** - Только создатель графа
- **IsStudentOfGraph** - Студент видит только свой граф

---

## Приватные поля по ролям

### StudentProfile (CRITICAL)
```
Приватные поля: goal, tutor, parent

Доступ:
- Student:  НЕ видит (скрыто от себя!)
- Teacher:  ВИДИТ
- Tutor:    ВИДИТ
- Parent:   НЕ видит
- Admin:    ВИДИТ

Реализация: can_view_private_fields() в permissions.py
- Студент НИКОГДА не видит свои приватные поля (бизнес-правило!)
```

### TeacherProfile (HIGH)
```
Приватные поля: bio, experience_years

Доступ:
- Teacher: НЕ видит свои (только admin)
- Student: НЕ видит
- Tutor:   НЕ видит
- Parent:  НЕ видит
- Admin:   ВИДИТ

Реализация: можно видеть только админу
```

### TutorProfile (HIGH)
```
Приватные поля: bio, experience_years

Доступ: (аналогично TeacherProfile)
- Tutor:   НЕ видит свои
- Admin:   ВИДИТ все
```

### ParentProfile
```
Приватные поля: NONE (пока нет)
PARENT_PRIVATE_FIELDS = []
```

---

## Иерархия ролей

### Уровень 1: ADMIN (is_staff=True или is_superuser=True)
- Доступ: **FULL_SYSTEM_ACCESS**
- Может видеть все приватные поля всех ролей
- Может редактировать любые профили
- Использует отдельные admin-only views

### Уровень 2: TEACHER (role=TEACHER, is_active=True)
- Доступ: **ROLE_SPECIFIC**
- Видит студентов своих предметов
- Видит материалы своих предметов
- Видит приватные поля студентов (goal, tutor, parent)
- НЕ видит bio/experience_years других teachers

### Уровень 3: TUTOR (role=TUTOR, is_active=True)
- Доступ: **STUDENT_MANAGEMENT**
- Управляет только своими студентами
- **PROTECTED FIELDS:** НЕ может менять role, email, is_active, is_superuser, is_staff
- Видит приватные поля студентов

### Уровень 4: PARENT (role=PARENT, is_active=True)
- Доступ: **CHILDREN_ONLY**
- Видит только своих детей (StudentProfile.parent == request.user)
- Видит только отчеты о своих детях
- Может подтверждать отчеты (если show_to_parent=True)

### Уровень 5: STUDENT (role=STUDENT, is_active=True)
- Доступ: **SELF_AND_ENROLLED**
- Видит только свой профиль (скрыты goal, tutor, parent!)
- Видит только материалы зачисленных предметов
- НЕ может менять protected fields

---

## Критические операции

### 1. Фильтрация приватных полей
**Файл:** `/backend/accounts/permissions.py`  
**Функция:** `can_view_private_fields(viewer_user, profile_owner_user, profile_type)`

Логика:
- Админы видят всё (is_staff/is_superuser)
- Для студентов: teacher и tutor видят приватные поля
- Владелец профиля НЕ видит свои приватные поля
- Неактивные пользователи НЕ видят приватные поля

Реализация в сериализаторах:
```python
# В __init__() каждого сериализатора:
if self.instance and request:
    if not can_view_private_fields(viewer, owner, role):
        self.fields.pop("goal", None)
        self.fields.pop("tutor", None)
        # и т.д.
```

### 2. Защита Tutor от редактирования protected fields
**Файл:** `/backend/accounts/permissions.py`  
**Класс:** `TutorCanManageStudentProfiles`

Protected fields:
- role
- email
- is_active
- is_superuser
- is_staff

Попытки изменения логируются: `audit_logger.warning()`

### 3. Parent доступ к чатам
**Файл:** `/backend/chat/permissions.py`  
**Функция:** `check_parent_access_to_room()`

Логика:
- Родитель имеет доступ если его ребенок в participants
- Автоматически добавляется в participants
- Операция транзакционна (atomic)

### 4. Material доступ через enrollment
**Файл:** `/backend/materials/permissions.py`  
**Класс:** `StudentEnrollmentPermission`

Логика:
- Студент видит материал только если SubjectEnrollment.is_active=True
- Проверяется свежесть зачисления (дата не истекла)
- Публичные материалы (is_public=True) доступны всем

### 5. Report доступ и sharing
**Файл:** `/backend/reports/permissions.py`  
**Класс:** `ReportAccessService`

Методы доступа:
1. Direct - по ролям (student -> own reports, parent -> children reports)
2. Token - временный доступ по токену
3. Sharing - явная выдача доступа (ReportSharing model)

Все обращения логируются в ReportAccessAuditLog

### 6. Race condition в создании пользователя
**Файл:** `/backend/accounts/staff_views.py`

Защита:
```python
with transaction.atomic():
    # Email uniqueness check
    # IntegrityError catch -> 400 Bad Request
```

Сохраняет от параллельного создания дубликатов

---

## Сериализаторы с фильтрацией полей

### StudentProfileSerializer
- Исключает: goal, tutor, parent (если viewer не может видеть)
- Условные: все 3 приватных поля

### TeacherProfileSerializer
- Исключает: bio, experience_years (если viewer не может видеть)
- Условные: оба приватных поля

### TutorProfileSerializer
- Исключает: bio, experience_years (если viewer не может видеть)
- Условные: оба приватных поля

### StudentProfileDetailSerializer
- Полная фильтрация в `to_representation()`
- read_only: progress_percentage, streak_days, total_points, accuracy_percentage

### ParentProfileListSerializer
- Оптимизирована для list view (без children details для N+1)
- Calculated field: children_count

---

## Views с permission_classes

```
Views                           Permissions
=========================================================
StudentProfileView              IsAuthenticated, IsStudent
TeacherProfileView              IsAuthenticated, IsTeacher
TutorProfileView                IsAuthenticated, IsTutor
ParentProfileView               IsAuthenticated, IsParent

AdminTeacherProfileEditView      IsAuthenticated, IsStaffOrAdmin
AdminTutorProfileEditView        IsAuthenticated, IsStaffOrAdmin
AdminUserProfileView             IsAuthenticated, IsStaffOrAdmin
AdminUserFullInfoView            IsAuthenticated, IsStaffOrAdmin

CurrentUserProfileView           IsAuthenticated
TeacherListView                  IsAuthenticated
TeacherDetailView                IsAuthenticated
NotificationSettingsView         IsAuthenticated
```

---

## Требования к is_active

**Критичная проверка:** Все permission классы требуют `is_active=True`

- Неактивные пользователи: полностью заблокированы даже от чтения
- Исключение: `IsAuthenticated` default permission НЕ проверяет `is_active`
- Это обеспечивает возможность временного отключения пользователя

---

## Аудит и логирование

### Audit Logger
**Файл:** `/backend/logs/audit.log`

Логируемые операции:
1. Создание пользователей
2. Обновление профилей (field-level changes)
3. Попытки несанкционированного доступа
4. Попытки менять protected fields

Функция: `log_object_changes()` в staff_views.py

### Report Access Audit
**Файл:** ReportAccessAuditLog model

Логируемые:
- IP address
- User agent
- Session ID
- Access type (view, download, share, print, export)
- Access method (direct, token_link, shared_access, role_based)
- Duration

---

## REST Framework Settings

```python
DEFAULT_AUTHENTICATION_CLASSES = [
    "rest_framework.authentication.TokenAuthentication",  # Приоритет 1
    "rest_framework.authentication.SessionAuthentication", # Приоритет 2
]

DEFAULT_PERMISSION_CLASSES = [
    "rest_framework.permissions.IsAuthenticated",
]
```

TokenAuth используется для API, SessionAuth для CSRF защиты

---

## Файл результатов

Полный анализ сохранен в:
`/home/mego/Python Projects/THE_BOT_platform/.claude/state/admin_access_control.json`

Структура JSON:
- permissions (23 класса с проверками)
- privateFields (все приватные поля по ролям)
- roleTables (полная матрица доступа)
- serializers (12+ сериализаторов с фильтрацией)
- views_with_permissions (12 views)
- authentication_config
- sensitive_operations
- critical_security_notes
- role_hierarchy

