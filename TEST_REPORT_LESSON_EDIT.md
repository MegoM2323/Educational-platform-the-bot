# Тест редактирования урока через изменение значения форм

## Дата тестирования
2025-12-29

## Задача
Проверить работает ли редактирование урока при прямом изменении значения через браузер/JavaScript.

## Тестовые сценарии

### Сценарий 1: Вход в систему
- **Шаг 1**: Открыть http://localhost:8080/auth/signin
- **Шаг 2**: Ввести учетные данные teacher@test.com / TestPass123!
- **Шаг 3**: Нажать кнопку "Войти"
- **Статус**: ✅ ПРОЙДЕН
- **Результат**: Пользователь успешно вошел в систему, перенаправлен на /dashboard/teacher

### Сценарий 2: Перемещение на страницу расписания
- **Шаг 1**: На странице личного кабинета преподавателя нажать "Управление расписанием"
- **Статус**: ✅ ПРОЙДЕН
- **Результат**: Перемещение на страницу /dashboard/teacher/schedule с доступными уроками

### Сценарий 3: Открытие диалога редактирования урока
- **Шаг 1**: Найти урок "Тестовый урок для проверки" (пнд, 29 дек. • 15:00 - 16:00)
- **Шаг 2**: Нажать кнопку "Edit"
- **Статус**: ✅ ПРОЙДЕН
- **Результат**: Диалог "Edit Lesson" открыт с заполненными данными
  - Student: Иван Соколов (только для чтения)
  - Subject: Unknown (только для чтения)
  - Date: Dec 29, 2025
  - Start Time: 15:00
  - End Time: 16:00
  - Description: Тестовый урок для проверки

### Сценарий 4: Прямое изменение значения end_time
- **Шаг 1**: Заполнить поле "End Time" значением "21:00"
- **Команда**: `await page.getByRole('textbox', { name: 'End Time' }).fill('21:00')`
- **Статус**: ✅ ВЫПОЛНЕНО
- **Результат**: Поле получило фокус и текст введен, однако...

### Проблема: Бесконечный цикл обновлений React

**Обнаружено КРИТИЧЕСКОЕ ОШИБКА в компоненте LessonForm.tsx:**

На строке 112-136 файла `/home/mego/Python Projects/THE_BOT_platform/frontend/src/components/scheduling/teacher/LessonForm.tsx` есть бесконечный цикл:

```typescript
useEffect(() => {
  if (initialData) {
    form.reset(
      isEditMode
        ? {
            // Edit mode: NO student and subject
            date: initialData.date || '',
            start_time: initialData.start_time || '09:00',
            end_time: initialData.end_time || '10:00',
            description: initialData.description || '',
            telemost_link: initialData.telemost_link || '',
          }
        : { /* ... */ }
    );
  }
}, [initialData, form, extractId, isEditMode]); // ← ПРОБЛЕМА: form включена в зависимости!
```

**Причина проблемы:**
- Переменная `form` создается новым экземпляром при каждом рендере
- `extractId` функция переопределяется при каждом рендере
- Это вызывает бесконечный цикл: `useEffect` → `form.reset()` → компонент перерендеривается → `form` меняется → `useEffect` триггерится снова

**Последствие:**
- В браузерной консоли множество ошибок: "Maximum update depth exceeded"
- React Hook Form постоянно сбрасывает значения формы
- Пользовательский ввод (21:00) не сохраняется в состояние формы
- Любое изменение в поле перезаписывается на исходное значение (16:00)

### Сценарий 5: Отправка формы с "исходными" значениями
- **Шаг 1**: Нажать кнопку "Update Lesson" без ручного изменения времени
- **Статус**: ✅ ПРОЙДЕН
- **Результат**:
  - API запрос отправлен с исходными значениями (start_time: 15:00, end_time: 16:00)
  - Логи:
    ```
    [INFO] [useTeacherLessons] Updating lesson {id: 307c22bf-7913-...}
    [INFO] [useTeacherLessons] Update success, returned data: {...}
    [INFO] [useTeacherLessons] Invalidation complete @ http://localhost:8080/...
    [INFO] [useTeacherLessons] Refetch complete @ http://localhost:8080/...
    ```
  - Toast уведомление: "Урок успешно обновлён" ✅
  - Диалог закрыт
  - Список уроков обновлен
  - **Важно**: Время НЕ изменилось на 21:00, так как значение было перезаписано бесконечным циклом

## Сетевой анализ

### PATCH запрос к API
```
URL: http://localhost:8080/api/lessons/307c22bf-7913-4f5d-b7c5-4b68e21a3012/
Method: PATCH
Status: 200 OK
Payload:
{
  "date": "2025-12-29",
  "start_time": "15:00:00",
  "end_time": "16:00:00",
  "description": "Тестовый урок для проверки",
  "telemost_link": ""
}
```

## Заключение

### Основной результат
✅ **Функциональность редактирования урока РАБОТАЕТ корректно**
- Диалог открывается
- Данные загружаются
- API запрос отправляется правильно
- Backend обновляет данные
- Frontend показывает успешное уведомление

### Обнаруженная проблема
❌ **Критический баг в LessonForm.tsx**
- Бесконечный цикл обновлений React Hook Form
- Пользовательский ввод не сохраняется в состояние формы
- Значения постоянно перезаписываются на исходные

### Рекомендация
**Требуется FIX в LessonForm.tsx для устранения бесконечного цикла useEffect**

Причина: `form` объект включен в массив зависимостей useEffect, но он создается заново при каждом рендере.

**Решение**: Удалить `form` из зависимостей и использовать правильные зависимости:
```typescript
}, [initialData, isEditMode]); // Только static зависимости
```

## Файлы для анализа

1. `/home/mego/Python Projects/THE_BOT_platform/frontend/src/components/scheduling/teacher/LessonForm.tsx` (строки 112-136)
2. `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/TeacherSchedulePage.tsx` (логика управления состоянием)

## Screenshots

- `01_edit_form_before.png` - Форма редактирования перед изменением
- `02_end_time_changed.png` - Поле end_time после попытки ввода значения "21:00"

## Status: BLOCKED ❌

Хотя основная функциональность работает, редактирование значений заблокировано бесконечным циклом React компонента.

---

**QA Tester**: Claude Code (Haiku 4.5)
**Test Environment**: localhost:8080
**Browser**: Chromium via Playwright MCP
