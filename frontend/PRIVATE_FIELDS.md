# Документация: Приватные поля профилей

## Обзор

В THE_BOT_platform реализована система приватных полей профилей, которые видны только определенным ролям пользователей. Backend автоматически фильтрует эти поля в зависимости от прав пользователя.

## Приватные поля по ролям

### StudentProfile

**Приватные поля** (студент НЕ видит, видят teacher/tutor/admin):
- `goal` - Цель обучения
- `tutor` - ID тьютора
- `parent` - ID родителя
- `tutor_info` - Информация о тьюторе (вложенный объект)
- `parent_info` - Информация о родителе (вложенный объект)

**Публичные поля**:
- `grade` - Класс
- `progress_percentage` - Процент прогресса
- `streak_days` - Дни подряд
- `total_points` - Всего баллов
- `accuracy_percentage` - Точность

### TeacherProfile

**Приватные поля** (преподаватель НЕ видит, видит только admin):
- `bio` - Биография
- `experience_years` - Опыт работы (лет)

**Публичные поля**:
- `subject` - Основной предмет
- `subjects` - Список предметов (массив)

### TutorProfile

**Приватные поля** (тьютор НЕ видит, видит только admin):
- `bio` - Биография
- `experience_years` - Опыт работы (лет)

**Публичные поля**:
- `specialization` - Специализация

### ParentProfile

Нет приватных полей (пока нет полей вообще).

## Как работает система

### Backend

Backend использует DRF сериализаторы с условной логикой:

```python
class StudentProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = request.user if request else None

        # Студент не видит приватные поля
        if user and user.role == 'student' and user.id == instance.user.id:
            data.pop('goal', None)
            data.pop('tutor', None)
            data.pop('parent', None)
            data.pop('tutor_info', None)
            data.pop('parent_info', None)

        return data
```

### Frontend

#### 1. TypeScript типы

Все приватные поля помечены как **опциональные** (`field?: type`):

**Файл:** `frontend/src/integrations/api/adminAPI.ts`

```typescript
export interface StudentProfileData {
  grade?: string;
  goal?: string; // ПРИВАТНОЕ: студент не видит
  tutor_id?: number | null; // ПРИВАТНОЕ: студент не видит
  parent_id?: number | null; // ПРИВАТНОЕ: студент не видит
}

export interface TeacherProfileData {
  experience_years?: number; // ПРИВАТНОЕ: только для admin
  bio?: string; // ПРИВАТНОЕ: только для admin
}

export interface TutorProfileData {
  specialization?: string;
  experience_years?: number; // ПРИВАТНОЕ: только для admin
  bio?: string; // ПРИВАТНОЕ: только для admin
}
```

#### 2. Optional chaining в компонентах

Всегда используйте optional chaining (`?.`) и проверки на существование:

**Правильно:**
```tsx
// Проверка через условный рендеринг
{profile?.goal && (
  <div>
    <Label>Цель обучения</Label>
    <p>{profile.goal}</p>
  </div>
)}

// Проверка с fallback значением
<p>{profile?.bio || 'Не указана'}</p>

// Тернарный оператор
{student.goal ? (
  <div className="text-sm text-muted-foreground mb-1">Цель: {student.goal}</div>
) : null}
```

**Неправильно:**
```tsx
// ❌ Прямой доступ без проверки
<p>{profile.goal}</p>

// ❌ Предполагаем, что поле всегда есть
<div>Цель: {profile.goal}</div>
```

#### 3. Визуальная индикация в админке

Для админских форм используется компонент `PrivateFieldTooltip`:

**Файл:** `frontend/src/components/admin/PrivateFieldTooltip.tsx`

```tsx
import { PrivateFieldTooltip } from '@/components/admin/PrivateFieldTooltip';

// В форме
<div className="flex items-center gap-2">
  <Label htmlFor="goal">Цель обучения</Label>
  <Badge variant="outline" className="text-xs">
    Приватное
  </Badge>
  <PrivateFieldTooltip role="student" field="goal" />
</div>
<Textarea id="goal" ... />
<p className="text-xs text-muted-foreground">
  Видят: преподаватели, тьюторы, администраторы. Студент не видит это поле.
</p>
```

## Примеры использования в дашбордах

### StudentDashboard

Студент **НЕ видит** свои приватные поля - они просто не приходят с сервера.

```tsx
// В StudentDashboard нет кода, который отображает goal/tutor/parent
// Эти данные отфильтрованы backend'ом
```

### TeacherDashboard

Преподаватель **НЕ видит** свои bio/experience_years - они отфильтрованы backend'ом.

```tsx
// TeacherDashboard не отображает профиль самого преподавателя
// Отображаются только студенты и материалы
```

### TutorDashboard

Тьютор **видит** цель студента (это правильно):

```tsx
{(students ?? []).map((s) => (
  <Card key={s.id}>
    <div className="font-medium">{s.full_name}</div>
    <Badge variant="outline">{s.grade || '-'} класс</Badge>
    {s.goal ? (
      <div className="text-sm text-muted-foreground mb-1">
        Цель: {s.goal}
      </div>
    ) : null}
  </Card>
))}
```

### AdminDashboard

Админ **видит всё** - приватные поля отображаются с индикацией:

```tsx
// В формах редактирования используется PrivateFieldTooltip
<EditProfileDialog user={user} profile={profile} />
```

## Безопасность на клиенте

### Важно понимать:

1. **Backend - источник истины**: Приватные поля фильтруются на сервере, а не на клиенте.
2. **Frontend проверки - для UX**: Проверки на фронтенде нужны для правильного отображения, но НЕ для безопасности.
3. **Never trust client**: Никогда не полагайтесь только на клиентские проверки для контроля доступа.

### Правило безопасности:

```typescript
// Если поле undefined/null - значит backend его скрыл
const renderPrivateField = (field: any, fieldName: string) => {
  if (field === undefined || field === null) {
    return null; // Не рендерим
  }
  return <div>{field}</div>;
};
```

## Тестирование

При тестировании приватных полей:

1. **Проверьте API ответы** для каждой роли:
   ```bash
   # Как студент
   curl -H "Authorization: Bearer STUDENT_TOKEN" /api/dashboard/student/

   # Как преподаватель
   curl -H "Authorization: Bearer TEACHER_TOKEN" /api/dashboard/teacher/
   ```

2. **Mock тесты** должны корректно имитировать отсутствие полей:
   ```typescript
   // В тестах для студента НЕ включать приватные поля
   const mockStudentProfile = {
     id: 1,
     grade: "10",
     // goal: "Test goal", // ❌ НЕ включаем
     progress_percentage: 75,
   };
   ```

3. **E2E тесты** должны проверять:
   - Студент НЕ видит goal/tutor/parent в своем дашборде
   - Преподаватель НЕ видит bio/experience_years в своем профиле
   - Тьютор ВИДИТ goal студента
   - Админ ВИДИТ все поля

## Частые ошибки

### ❌ Ошибка 1: Предполагать, что поле всегда есть

```tsx
// Неправильно
<div>Цель: {profile.goal}</div>

// Правильно
{profile?.goal && <div>Цель: {profile.goal}</div>}
```

### ❌ Ошибка 2: Забыть про optional в типах

```typescript
// Неправильно
interface StudentProfile {
  goal: string; // Обязательное поле
}

// Правильно
interface StudentProfile {
  goal?: string; // Опциональное поле
}
```

### ❌ Ошибка 3: Не добавить индикацию в админке

```tsx
// Неправильно - пользователь не знает, что поле приватное
<Label>Цель обучения</Label>
<Textarea id="goal" />

// Правильно - ясно видно, что поле приватное
<div className="flex items-center gap-2">
  <Label>Цель обучения</Label>
  <Badge variant="outline" className="text-xs">Приватное</Badge>
  <PrivateFieldTooltip role="student" field="goal" />
</div>
<Textarea id="goal" />
<p className="text-xs text-muted-foreground">
  Студент не видит это поле.
</p>
```

## Добавление новых приватных полей

Если нужно добавить новое приватное поле:

### 1. Backend (Django)

```python
# В сериализаторе
class StudentProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = request.user if request else None

        if user and user.role == 'student' and user.id == instance.user.id:
            data.pop('goal', None)
            data.pop('new_private_field', None)  # Добавить сюда

        return data
```

### 2. Frontend типы

```typescript
// В adminAPI.ts
export interface StudentProfileData {
  grade?: string;
  goal?: string; // ПРИВАТНОЕ: студент не видит
  new_private_field?: string; // ПРИВАТНОЕ: студент не видит
}
```

### 3. Обновить PrivateFieldTooltip

```typescript
// В PrivateFieldTooltip.tsx
const getTooltipText = () => {
  if (role === 'student') {
    if (['goal', 'tutor', 'parent', 'new_private_field'].includes(field)) {
      return 'Студент не видит это поле...';
    }
  }
  // ...
};
```

### 4. Обновить форму редактирования

```tsx
// В EditProfileDialog.tsx
<div className="space-y-2">
  <div className="flex items-center gap-2">
    <Label htmlFor="new_private_field">Новое поле</Label>
    <Badge variant="outline" className="text-xs">Приватное</Badge>
    <PrivateFieldTooltip role="student" field="new_private_field" />
  </div>
  <Input id="new_private_field" ... />
  <p className="text-xs text-muted-foreground">
    Студент не видит это поле.
  </p>
</div>
```

### 5. Обновить дашборды (если нужно)

```tsx
// Всегда с optional chaining
{profile?.new_private_field && (
  <div>Новое поле: {profile.new_private_field}</div>
)}
```

## Контакты

Если возникли вопросы или нужна помощь с приватными полями, обратитесь к:
- Backend разработчику (система фильтрации полей)
- Frontend lead (UI/UX приватных полей)

## Changelog

- **2025-11-22**: Создана документация системы приватных полей
