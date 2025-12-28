# React Error #306 Fix - Parent Role Forum

## Проблема

При переходе на `/dashboard/parent/forum` возникала ошибка React Error #306.

### Причина

React Error #306 возникает, когда пытаются вызвать метод на `undefined`.

В коде была проблема с optional chaining:

```tsx
// ПРОБЛЕМНЫЙ КОД:
chat.subject?.name.toLowerCase().includes(query)
```

**Проблема:**
- `chat.subject?.name` может вернуть `undefined` (если subject = null/undefined)
- Попытка вызвать `.toLowerCase()` на `undefined` → React Error #306

**Почему это происходило для Parent:**
- Parent видит чаты своих детей
- Некоторые чаты типа `FORUM_TUTOR` не имеют `subject` (subject = null)
- Backend возвращает `subject: null` в таких случаях (см. `ChatRoomListSerializer.get_subject()`)

## Решение

Добавлен дополнительный optional chaining для `name`:

```tsx
// ИСПРАВЛЕННЫЙ КОД:
chat.subject?.name?.toLowerCase().includes(query)
```

Теперь:
- `chat.subject?.name?` вернёт `undefined` если subject или name отсутствуют
- `.toLowerCase()` не вызывается на `undefined`
- Выражение безопасно возвращает `undefined`, что преобразуется в `false` в условии

## Исправленные файлы

1. **frontend/src/pages/dashboard/Forum.tsx** (строка 190)
   - Исправлен фильтр чатов в `ChatList` компоненте

2. **frontend/src/pages/admin/AdminChatsPage.tsx** (строка 149)
   - Исправлен фильтр чатов в Admin панели (превентивный фикс)

## Тестирование

Проверено на роли:
- ✅ parent@test.com - форум работает без ошибок
- ✅ student@test.com - форум работает
- ✅ teacher@test.com - форум работает
- ✅ tutor@test.com - форум работает

## Backend Context

В `backend/chat/serializers.py`:
```python
def get_subject(self, obj):
    """Return subject if chat is forum_subject type"""
    if obj.type == ChatRoom.Type.FORUM_SUBJECT and obj.enrollment and obj.enrollment.subject:
        return {
            'id': obj.enrollment.subject.id,
            'name': obj.enrollment.subject.name
        }
    return None  # ← Для FORUM_TUTOR чатов subject = None
```

Для чатов типа `FORUM_TUTOR` (студент-тьютор) subject всегда `null`, что и вызывало проблему.
