# План: Финальная исправка 6 критических проблем архитектуры

## Фаза 0: Предварительная подготовка
- ✓ Проверка состояния проекта
- [ ] Анализ текущих ошибок

## Параллельная группа 1: Исправки User imports и пагинации (независимые)
- [ ] Task 1: Исправить User import в serializers.py (CRITICAL - 5 мин)
  - Файл: `/backend/chat/serializers.py` строка 2
  - Текущий: `from django.contrib.auth.models import User`
  - Требуемый: `from django.contrib.auth import get_user_model; User = get_user_model()`
  - Зависимостей: нет

- [ ] Task 2: Переделать пагинацию в chat_service.py и views.py (HIGH - 20 мин)
  - Файл: `/backend/chat/services/chat_service.py`
  - Файл: `/backend/chat/views.py` list()
  - Проблема: get_user_chats() возвращает QuerySet без пагинации, слайсинг на view уровне неоптимален
  - Решение: service возвращает raw QuerySet, view делает пагинацию через QuerySet slicing
  - Зависимостей: нет

- [ ] Task 3: Добавить error handling для query параметров (MEDIUM - 15 мин)
  - Файл: `/backend/chat/views.py`
  - Проблема: page, limit, before_id парсятся без обработки ошибок
  - Решение: try/except для всех int() конверсий, валидация границ
  - Зависимостей: нет

## Параллельная группа 2: REST routing для сообщений (HIGH - 30 мин)
- [ ] Task 4: Создать MessageViewSet для правильного routing (HIGH - 30 мин)
  - Файл: `/backend/chat/views.py` - добавить новый ViewSet
  - Требуемые endpoints:
    - PATCH /api/chat/{room_id}/messages/{message_id}/ - редактировать
    - DELETE /api/chat/{room_id}/messages/{message_id}/ - удалить
  - Обновить urls.py для path параметров
  - Зависимостей: нет

## Параллельная группа 3: Проверка и завершение (HIGH - 5 мин)
- [ ] Task 5: Проверить ChatContactsView GET /api/chat/contacts/ (MEDIUM - 5 мин)
  - Файл: `/backend/chat/views.py`
  - Требуемый endpoint: GET /api/chat/contacts/ - список доступных контактов
  - Проверить что endpoint существует и зарегистрирован в urls.py
  - Зависимостей: нет

## Фаза финального контроля: Тестирование и запуск
- [ ] Task 6: Запустить Django check и тесты (MEDIUM - 10 мин)
  - Проверка синтаксиса и импортов
  - pytest для всех chat тестов
  - Валидация что все 6 проблем исправлены

## Success Criteria
- ✓ User import исправлен во всех местах
- ✓ Пагинация оптимизирована через QuerySet slicing
- ✓ Query параметры валидируются с error handling
- ✓ MessageViewSet создан с path параметрами
- ✓ ChatContactsView существует и зарегистрирован
- ✓ Django check: 0 issues
- ✓ Все тесты pass

## Estimated Time
- Total: 85 минут (все задачи могут идти параллельно в группах)
