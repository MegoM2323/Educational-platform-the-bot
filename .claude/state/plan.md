# Добавление keyboard accessibility для StudentDashboard

## Статус: planning → ready for implementation

## Задача
Добавить полную keyboard accessibility и поддержку screen readers для интерактивных элементов в StudentDashboard.tsx:

1. Материалы (line 281-316): Заменить div с onClick на button с надлежащими ARIA атрибутами
2. Offline состояние: Добавить aria-disabled и aria-label к disabled контенту
3. BookingWidget: Показывать disabled состояние вместо удаления из DOM
4. Все интерактивные div элементы: role='button', tabIndex=0, onKeyDown обработчик
5. Улучшить ARIA labels для всех интерактивных элементов

## Текущие проблемы

### P1: Material items (line 281-316)
- Используется простой div с onClick
- Не keyboard accessible (нет табуляции)
- Нет aria атрибутов для screen readers
- Нужно: заменить на button или добавить role, tabIndex, onKeyDown

### P2: Offline состояние (line 231)
- Используется pointer-events-none и opacity для disabled контента
- Нет aria-disabled атрибута
- Нет aria-label объяснения
- Нужно: добавить aria-disabled и aria-label

### P3: BookingWidget (line 268-270)
- Условно удаляется из DOM при offline
- Лучше показывать disabled состояние
- Нужно: всегда рендерить с disabled пропсом

### P4: Subjects section buttons (line 354-362)
- Button элементы, но нужна проверка ARIA
- Нужна aria-label для улучшения доступности

## Параллельная группа 1: Реализация (1 независимая задача)

### T001: Добавить keyboard accessibility - coder
- Line 281-316: Заменить material div на button или добавить role/tabIndex/onKeyDown
- Line 231: Добавить aria-disabled и aria-label к disabled контенту
- Line 268-270: Сделать BookingWidget всегда видимым с disabled пропсом
- Line 354-362: Добавить aria-label к subject buttons
- Все кнопки в Quick Actions должны иметь aria-label
- Добавить функцию handleMaterialKeyDown для KeyEvent обработки (Enter/Space)

## Параллельная группа 2: Review & Testing

### T101: Code review (reviewer)
- Проверить корректность ARIA атрибутов
- Убедиться что все интерактивные элементы keyboard accessible
- Проверить что отключенное состояние явно обозначено

### T102: Testing (tester)
- Написать тесты на keyboard навигацию (Tab, Enter)
- Проверить что ARIA атрибуты правильно применены
- Тест offline состояния (aria-disabled)
- E2E тест для проверки accessibility с экран ридером

## Ожидаемый результат
✓ Material items клиентские через button с надлежащими ARIA
✓ KeyDown обработчик для Enter/Space на всех интерактивных элементах
✓ aria-disabled добавлена к offline контенту
✓ aria-label добавлены для улучшения контекста
✓ BookingWidget всегда рендерится с disabled состоянием
✓ Полная keyboard навигация (Tab, Enter, Space)
✓ Screen reader совместимость
✓ Tests pass
✓ LGTM от reviewer
