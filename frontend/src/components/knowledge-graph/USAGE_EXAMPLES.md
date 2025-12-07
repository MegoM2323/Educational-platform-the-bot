# GraphVisualization - Usage Examples

## Примеры использования компонента визуализации графа знаний

### 1. Минимальный пример

```tsx
import { GraphVisualization } from '@/components/knowledge-graph';

function SimpleGraph() {
  const data = {
    nodes: [
      { id: '1', title: 'Урок 1', status: 'completed' },
      { id: '2', title: 'Урок 2', status: 'in_progress' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
    ],
  };

  return <GraphVisualization data={data} />;
}
```

### 2. С обработчиками событий

```tsx
import { GraphVisualization } from '@/components/knowledge-graph';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

function InteractiveGraph() {
  const navigate = useNavigate();

  const handleNodeClick = (nodeId: string) => {
    navigate(`/lessons/${nodeId}`);
  };

  const handleNodeHover = (nodeId: string | null) => {
    if (nodeId) {
      toast.info(`Урок ${nodeId}`);
    }
  };

  return (
    <GraphVisualization
      data={graphData}
      onNodeClick={handleNodeClick}
      onNodeHover={handleNodeHover}
    />
  );
}
```

### 3. С API интеграцией

```tsx
import { useQuery } from '@tanstack/react-query';
import { GraphVisualization } from '@/components/knowledge-graph';
import { knowledgeGraphAPI } from '@/integrations/api/knowledgeGraphAPI';
import { LoadingSpinner } from '@/components/LoadingSpinner';

function KnowledgeGraphPage({ graphId }: { graphId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['knowledge-graph', graphId],
    queryFn: () => knowledgeGraphAPI.getGraph(graphId),
  });

  if (isLoading) {
    return <LoadingSpinner text="Загрузка графа..." />;
  }

  if (error) {
    return <div>Ошибка загрузки графа</div>;
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Граф знаний</h1>
      <GraphVisualization
        data={data}
        onNodeClick={(id) => window.location.href = `/lessons/${id}`}
        height={800}
      />
    </div>
  );
}
```

### 4. С кастомными размерами

```tsx
import { GraphVisualization } from '@/components/knowledge-graph';

function CustomSizeGraph() {
  return (
    <GraphVisualization
      data={graphData}
      width={1200}
      height={800}
      className="shadow-lg rounded-lg"
    />
  );
}
```

### 5. Режим редактирования

```tsx
import { useState } from 'react';
import { GraphVisualization } from '@/components/knowledge-graph';
import { Button } from '@/components/ui/button';

function EditableGraph() {
  const [isEditing, setIsEditing] = useState(false);

  return (
    <div>
      <div className="mb-4">
        <Button
          type="button"
          onClick={() => setIsEditing(!isEditing)}
        >
          {isEditing ? 'Сохранить' : 'Редактировать'}
        </Button>
      </div>

      <GraphVisualization
        data={graphData}
        isEditable={isEditing}
      />
    </div>
  );
}
```

### 6. С валидацией данных

```tsx
import { GraphVisualization, validateGraphData } from '@/components/knowledge-graph';
import { toast } from 'sonner';
import { useEffect } from 'react';

function ValidatedGraph({ data }: { data: GraphData }) {
  useEffect(() => {
    const { valid, errors } = validateGraphData(data);

    if (!valid) {
      console.error('Graph validation errors:', errors);
      toast.error('Граф содержит ошибки');
    }
  }, [data]);

  return <GraphVisualization data={data} />;
}
```

### 7. С локальным state для выбранного узла

```tsx
import { useState } from 'react';
import { GraphVisualization } from '@/components/knowledge-graph';
import { Card } from '@/components/ui/card';

function GraphWithSelection() {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const selectedLesson = graphData.nodes.find(n => n.id === selectedNode);

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="col-span-2">
        <GraphVisualization
          data={graphData}
          onNodeClick={setSelectedNode}
        />
      </div>

      <div className="col-span-1">
        {selectedLesson ? (
          <Card className="p-4">
            <h3 className="font-bold">{selectedLesson.title}</h3>
            <p className="text-sm text-muted-foreground">
              Статус: {selectedLesson.status}
            </p>
          </Card>
        ) : (
          <Card className="p-4">
            <p className="text-muted-foreground">
              Выберите урок на графе
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
```

### 8. С фильтрацией по статусу

```tsx
import { useState } from 'react';
import { GraphVisualization } from '@/components/knowledge-graph';
import { Button } from '@/components/ui/button';

function FilterableGraph({ originalData }: { originalData: GraphData }) {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const filteredData = statusFilter
    ? {
        nodes: originalData.nodes.filter(n => n.status === statusFilter),
        links: originalData.links.filter(l => {
          const source = originalData.nodes.find(n => n.id === l.source);
          const target = originalData.nodes.find(n => n.id === l.target);
          return source?.status === statusFilter && target?.status === statusFilter;
        }),
      }
    : originalData;

  return (
    <div>
      <div className="mb-4 flex gap-2">
        <Button
          type="button"
          variant={statusFilter === null ? 'default' : 'outline'}
          onClick={() => setStatusFilter(null)}
        >
          Все
        </Button>
        <Button
          type="button"
          variant={statusFilter === 'completed' ? 'default' : 'outline'}
          onClick={() => setStatusFilter('completed')}
        >
          Завершенные
        </Button>
        <Button
          type="button"
          variant={statusFilter === 'in_progress' ? 'default' : 'outline'}
          onClick={() => setStatusFilter('in_progress')}
        >
          В процессе
        </Button>
      </div>

      <GraphVisualization data={filteredData} />
    </div>
  );
}
```

### 9. С прогресс-баром

```tsx
import { GraphVisualization } from '@/components/knowledge-graph';
import { Progress } from '@/components/ui/progress';

function GraphWithProgress({ data }: { data: GraphData }) {
  const totalLessons = data.nodes.length;
  const completedLessons = data.nodes.filter(n => n.status === 'completed').length;
  const progressPercentage = (completedLessons / totalLessons) * 100;

  return (
    <div>
      <div className="mb-4">
        <p className="text-sm text-muted-foreground mb-2">
          Прогресс: {completedLessons} из {totalLessons} уроков
        </p>
        <Progress value={progressPercentage} />
      </div>

      <GraphVisualization data={data} />
    </div>
  );
}
```

### 10. Полный пример с dashboard

```tsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { GraphVisualization } from '@/components/knowledge-graph';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { knowledgeGraphAPI } from '@/integrations/api/knowledgeGraphAPI';

function KnowledgeGraphDashboard({ courseId }: { courseId: string }) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['knowledge-graph', courseId],
    queryFn: () => knowledgeGraphAPI.getGraph(courseId),
  });

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!data) {
    return <div>Граф не найден</div>;
  }

  const stats = {
    total: data.nodes.length,
    completed: data.nodes.filter(n => n.status === 'completed').length,
    inProgress: data.nodes.filter(n => n.status === 'in_progress').length,
    notStarted: data.nodes.filter(n => n.status === 'not_started').length,
    locked: data.nodes.filter(n => n.status === 'locked').length,
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Статистика */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Завершено</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-600">{stats.completed}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">В процессе</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-600">{stats.inProgress}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Не начато</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-gray-600">{stats.notStarted}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Заблокировано</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-red-600">{stats.locked}</p>
          </CardContent>
        </Card>
      </div>

      {/* Граф */}
      <Card>
        <CardHeader>
          <CardTitle>Граф знаний</CardTitle>
          <CardDescription>
            Кликните на урок для просмотра деталей
          </CardDescription>
        </CardHeader>
        <CardContent>
          <GraphVisualization
            data={data}
            onNodeClick={setSelectedNode}
            height={700}
          />
        </CardContent>
      </Card>

      {/* Детали выбранного урока */}
      {selectedNode && (
        <Card>
          <CardHeader>
            <CardTitle>Детали урока</CardTitle>
          </CardHeader>
          <CardContent>
            <p>ID: {selectedNode}</p>
            <Button
              type="button"
              className="mt-4"
              onClick={() => window.location.href = `/lessons/${selectedNode}`}
            >
              Открыть урок
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

## Типы данных

### GraphData

```typescript
interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}
```

### GraphNode

```typescript
interface GraphNode {
  id: string;                    // Уникальный ID урока
  title: string;                 // Название урока
  status: 'not_started' | 'in_progress' | 'completed' | 'locked';
  x?: number;                    // Начальная позиция X (опционально)
  y?: number;                    // Начальная позиция Y (опционально)
}
```

### GraphLink

```typescript
interface GraphLink {
  source: string | GraphNode;    // ID или объект узла-источника
  target: string | GraphNode;    // ID или объект узла-цели
  type: 'prerequisite' | 'suggested';  // Тип зависимости
}
```

## API Reference

### Props

- `data: GraphData` - данные графа (обязательно)
- `onNodeClick?: (nodeId: string) => void` - callback при клике на узел
- `onNodeHover?: (nodeId: string | null) => void` - callback при наведении
- `isEditable?: boolean` - сохранять позицию после драга (по умолчанию `false`)
- `width?: number` - ширина в пикселях (по умолчанию auto)
- `height?: number` - высота в пикселях (по умолчанию auto)
- `className?: string` - CSS класс для контейнера

## Взаимодействие

- **Zoom**: Колесико мыши или кнопки +/-
- **Pan**: Клик + перетаскивание фона
- **Click**: Клик на узел вызывает `onNodeClick`
- **Hover**: Наведение подсвечивает узел и связи
- **Drag**: Перетаскивание узла меняет его позицию

## Полное демо

См. `GraphVisualizationDemo.tsx` для полного рабочего примера.
