# GraphVisualization Component

Интерактивный компонент для визуализации графа знаний с использованием D3.js. Поддерживает отображение зависимостей между уроками, интерактивное взаимодействие и настройку внешнего вида.

## Возможности

- ✅ D3.js force simulation для динамической расстановки узлов
- ✅ Интерактивные узлы с поддержкой клика и наведения
- ✅ Визуализация зависимостей стрелками
- ✅ Zoom и pan (колесико мыши, кнопки управления)
- ✅ Цветовая индикация статуса урока (не начат, в процессе, завершен, заблокирован)
- ✅ Drag & drop для перестановки узлов
- ✅ Подсветка связанных узлов при наведении
- ✅ Автоматическое масштабирование под размер контейнера
- ✅ Оптимизация производительности (60fps)
- ✅ Адаптивная верстка для мобильных устройств
- ✅ Легенда и элементы управления

## Установка

Компонент требует установки D3.js:

```bash
npm install d3 @types/d3
```

## Использование

### Базовый пример

```tsx
import { GraphVisualization } from '@/components/knowledge-graph';
import { GraphData } from '@/components/knowledge-graph/graph-types';

const MyComponent = () => {
  const graphData: GraphData = {
    nodes: [
      { id: '1', title: 'Урок 1', status: 'completed' },
      { id: '2', title: 'Урок 2', status: 'in_progress' },
      { id: '3', title: 'Урок 3', status: 'not_started' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
    ],
  };

  return (
    <GraphVisualization
      data={graphData}
      onNodeClick={(nodeId) => console.log('Clicked:', nodeId)}
    />
  );
};
```

## API

### GraphVisualizationProps

| Prop | Тип | Обязательный | По умолчанию | Описание |
|------|-----|--------------|--------------|----------|
| `data` | `GraphData` | ✅ | - | Данные графа (узлы и связи) |
| `onNodeClick` | `(nodeId: string) => void` | ❌ | - | Callback при клике на узел |
| `onNodeHover` | `(nodeId: string \| null) => void` | ❌ | - | Callback при наведении на узел |
| `isEditable` | `boolean` | ❌ | `false` | Сохранять позицию узла после перетаскивания |
| `width` | `number` | ❌ | auto | Ширина компонента в пикселях |
| `height` | `number` | ❌ | auto | Высота компонента в пикселях |
| `className` | `string` | ❌ | `''` | CSS класс для контейнера |

### GraphData

```typescript
interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

interface GraphNode {
  id: string;                    // Уникальный ID урока
  title: string;                 // Название урока
  status: 'not_started' | 'in_progress' | 'completed' | 'locked';
  x?: number;                    // Начальная позиция X
  y?: number;                    // Начальная позиция Y
}

interface GraphLink {
  source: string | GraphNode;    // ID или объект узла-источника
  target: string | GraphNode;    // ID или объект узла-цели
  type: 'prerequisite' | 'suggested';  // Тип зависимости
}
```

## Взаимодействие

### Навигация

- **Zoom in/out**: Колесико мыши или кнопки + / -
- **Pan**: Клик и перетаскивание фона
- **Reset zoom**: Кнопка "Сбросить зум"

### Узлы

- **Hover**: Подсветка узла и его соседей
- **Click**: Вызов `onNodeClick` с ID узла
- **Drag**: Перемещение узла (позиция фиксируется если `isEditable=true`)

## Производительность

Компонент оптимизирован для работы с большими графами:

- ✅ Использует `useCallback` для предотвращения лишних рендеров
- ✅ Debounce для обработки resize событий (250ms)
- ✅ Мемоизация SVG элементов через D3 selection
- ✅ Force simulation автоматически останавливается при достижении стабильности
- ✅ Поддерживает 60fps анимацию при перетаскивании

## Тестирование

```bash
# Запуск тестов компонента
npm test -- src/components/knowledge-graph/GraphVisualization.test.tsx
```

## Демо

См. `GraphVisualizationDemo.tsx` для полного примера использования.
