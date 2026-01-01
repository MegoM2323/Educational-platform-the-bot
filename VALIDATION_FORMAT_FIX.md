# Исправление H1: Унификация формата ошибок валидации

## Проблема
Ошибки валидации возвращали разные форматы:
- DRF стандарт: `{"password": ["This field may not be blank."]}`
- Требуемый: `{"success": false, "error": "Пароль не может быть пустым"}`

## Решение

### 1. Сериализатор UserLoginSerializer (serializers.py)

Добавлены отдельные методы валидации для каждого поля:

```python
class UserLoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        if value and isinstance(value, str):
            value = value.strip()
        return value

    def validate_username(self, value):
        if value and isinstance(value, str):
            value = value.strip()
        return value

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError('Пароль не может быть пустым')
        return value

    def validate(self, attrs):
        email = attrs.get('email')
        username = attrs.get('username')
        password = attrs.get('password')

        if not email and not username:
            raise serializers.ValidationError('Необходимо указать email или имя пользователя')

        return attrs
```

### 2. Вспомогательная функция _format_validation_error (views.py)

```python
def _format_validation_error(errors):
    """
    Преобразует ошибки валидации DRF в единый формат.
    Собирает первую ошибку в одной строке.
    """
    if isinstance(errors, dict):
        for field, messages in errors.items():
            if isinstance(messages, list) and messages:
                return str(messages[0])
            elif isinstance(messages, str):
                return messages
            elif isinstance(messages, dict):
                return _format_validation_error(messages)
    elif isinstance(errors, list) and errors:
        return str(errors[0])
    return "Ошибка валидации данных"
```

### 3. Обновленные endpoints

#### login_view
```python
if not serializer.is_valid():
    error_msg = _format_validation_error(serializer.errors)
    return Response(
        {"success": False, "error": error_msg},
        status=status.HTTP_400_BAD_REQUEST
    )
```

#### update_profile
```python
error_msg = _format_validation_error(user_serializer.errors)
return Response(
    {"success": False, "error": error_msg},
    status=status.HTTP_400_BAD_REQUEST
)
```

#### change_password
```python
error_msg = _format_validation_error(serializer.errors)
return Response(
    {"success": False, "error": error_msg},
    status=status.HTTP_400_BAD_REQUEST
)
```

## Примеры тестирования

### Тест 1: Пустой пароль
```bash
curl -X POST "http://localhost:8000/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":""}'
```

**Ответ:**
```json
{
    "success": false,
    "error": "Пароль не может быть пустым"
}
```

### Тест 2: Пустой email и username
```bash
curl -X POST "http://localhost:8000/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"","username":"","password":"test123"}'
```

**Ответ:**
```json
{
    "success": false,
    "error": "Необходимо указать email или имя пользователя"
}
```

### Тест 3: Оба поля пусты
```bash
curl -X POST "http://localhost:8000/api/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"","password":""}'
```

**Ответ:**
```json
{
    "success": false,
    "error": "Пароль не может быть пустым"
}
```

## Изменены файлы

1. `/backend/accounts/serializers.py` - Переработан UserLoginSerializer
2. `/backend/accounts/views.py` - Добавлена функция _format_validation_error, обновлены endpoints

## Статус

✓ Реализовано
✓ Синтаксис проверен
✓ Форматирование применено (Black)
✓ Готово к тестированию
