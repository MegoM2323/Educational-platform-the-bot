# ElementCard Component

Компонент для отображения и взаимодействия с образовательными элементами в системе Knowledge Graph.

## Структура

```
knowledge-graph/
├── ElementCard.tsx              # Основной компонент
├── ElementCard.example.tsx      # Примеры использования (dev only)
├── index.ts                     # Экспорты
├── element-types/
│   ├── TextProblem.tsx         # Текстовые задачи
│   ├── QuickQuestion.tsx       # Быстрые вопросы (тесты)
│   ├── Theory.tsx              # Теоретический материал
│   └── Video.tsx               # Видео контент
└── README.md                    # Документация
```

## Использование

### Базовый пример

```tsx
import { ElementCard } from '@/components/knowledge-graph';

const MyComponent = () => {
  const handleSubmit = async (answer) => {
    await api.submitAnswer(element.id, answer);
  };

  return (
    <ElementCard
      element={element}
      onSubmit={handleSubmit}
    />
  );
};
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| element | Element | ✅ | - | Объект элемента |
| progress | ElementProgress | ❌ | undefined | Прогресс студента |
| onSubmit | (answer) => Promise<void> | ✅ | - | Callback для отправки ответа |
| onError | (error) => void | ❌ | undefined | Callback для обработки ошибок |
| isLoading | boolean | ❌ | false | Состояние загрузки |
| readOnly | boolean | ❌ | false | Режим только для чтения |

## Типы элементов

1. **Text Problem** - текстовые задачи с textarea
2. **Quick Question** - тесты с выбором ответа
3. **Theory** - теоретический материал с HTML
4. **Video** - видео (YouTube, Vimeo, файлы)

Полная документация в файле.
