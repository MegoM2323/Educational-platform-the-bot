/**
 * ProgressVisualization Examples
 * Примеры использования прогресс-визуализации в графе знаний
 */
import React, { useState } from 'react';
import { GraphVisualization } from './GraphVisualization';
import { GraphStatistics } from './GraphStatistics';
import { GraphData, ProgressNodeData } from './graph-types';
import { ProgressData } from './progressUtils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

/**
 * Пример 1: Базовая прогресс-визуализация
 */
export const BasicProgressVisualization: React.FC = () => {
  const graphData: GraphData = {
    nodes: [
      { id: '1', title: 'Введение', status: 'completed' },
      { id: '2', title: 'Основы', status: 'in_progress' },
      { id: '3', title: 'Практика', status: 'not_started' },
      { id: '4', title: 'Тестирование', status: 'locked' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
      { source: '3', target: '4', type: 'prerequisite' },
    ],
  };

  const progressData: { [key: string]: ProgressNodeData } = {
    '1': { status: 'completed', percentage: 100, completedAt: '2025-12-01' },
    '2': { status: 'in_progress', percentage: 45 },
    '3': { status: 'not_started', percentage: 0 },
    '4': { status: 'locked', percentage: 0 },
  };

  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">Базовая прогресс-визуализация</h3>
      <GraphVisualization
        data={graphData}
        progressData={progressData}
        height={400}
        showLegend={true}
      />
    </Card>
  );
};

/**
 * Пример 2: С текущим уроком
 */
export const WithCurrentLesson: React.FC = () => {
  const [currentLesson, setCurrentLesson] = useState<string>('2');

  const graphData: GraphData = {
    nodes: [
      { id: '1', title: 'Урок 1', status: 'completed' },
      { id: '2', title: 'Урок 2 (текущий)', status: 'in_progress' },
      { id: '3', title: 'Урок 3', status: 'not_started' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
    ],
  };

  const progressData: { [key: string]: ProgressNodeData } = {
    '1': { status: 'completed', percentage: 100 },
    '2': { status: 'in_progress', percentage: 67 },
    '3': { status: 'not_started', percentage: 0 },
  };

  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">Подсветка текущего урока</h3>
      <div className="mb-4 flex gap-2">
        {['1', '2', '3'].map((id) => (
          <Button
            key={id}
            type="button"
            variant={currentLesson === id ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCurrentLesson(id)}
          >
            Урок {id}
          </Button>
        ))}
      </div>
      <GraphVisualization
        data={graphData}
        progressData={progressData}
        currentLessonId={currentLesson}
        height={400}
        showLegend={true}
      />
    </Card>
  );
};

/**
 * Пример 3: Динамическое обновление прогресса
 */
export const DynamicProgress: React.FC = () => {
  const [progress, setProgress] = useState<{ [key: string]: ProgressNodeData }>({
    '1': { status: 'in_progress', percentage: 30 },
    '2': { status: 'not_started', percentage: 0 },
    '3': { status: 'locked', percentage: 0 },
  });

  const graphData: GraphData = {
    nodes: [
      { id: '1', title: 'Модуль 1', status: 'in_progress' },
      { id: '2', title: 'Модуль 2', status: 'not_started' },
      { id: '3', title: 'Модуль 3', status: 'locked' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
    ],
  };

  const simulateProgress = () => {
    setProgress((prev) => {
      const lesson1Percent = prev['1'].percentage;

      if (lesson1Percent < 100) {
        // Увеличиваем прогресс первого урока
        return {
          ...prev,
          '1': {
            ...prev['1'],
            percentage: Math.min(100, lesson1Percent + 10),
            status: lesson1Percent + 10 >= 100 ? 'completed' : 'in_progress',
          },
        };
      } else if (prev['2'].status === 'not_started') {
        // Разблокируем второй урок
        return {
          ...prev,
          '2': { status: 'in_progress', percentage: 0 },
        };
      } else if (prev['2'].percentage < 100) {
        // Увеличиваем прогресс второго урока
        const lesson2Percent = prev['2'].percentage;
        return {
          ...prev,
          '2': {
            ...prev['2'],
            percentage: Math.min(100, lesson2Percent + 10),
            status: lesson2Percent + 10 >= 100 ? 'completed' : 'in_progress',
          },
        };
      } else if (prev['3'].status === 'locked') {
        // Разблокируем третий урок
        return {
          ...prev,
          '3': { status: 'not_started', percentage: 0 },
        };
      }

      return prev;
    });
  };

  const resetProgress = () => {
    setProgress({
      '1': { status: 'in_progress', percentage: 30 },
      '2': { status: 'not_started', percentage: 0 },
      '3': { status: 'locked', percentage: 0 },
    });
  };

  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">Динамическое обновление</h3>
      <div className="mb-4 flex gap-2">
        <Button type="button" onClick={simulateProgress}>
          Увеличить прогресс
        </Button>
        <Button type="button" variant="outline" onClick={resetProgress}>
          Сбросить
        </Button>
      </div>
      <div className="mb-4 flex gap-2 flex-wrap">
        {Object.entries(progress).map(([id, data]) => (
          <Badge key={id} variant="outline">
            Модуль {id}: {data.percentage}%
          </Badge>
        ))}
      </div>
      <GraphVisualization
        data={graphData}
        progressData={progress}
        height={400}
        showLegend={true}
        animationDuration={800}
      />
    </Card>
  );
};

/**
 * Пример 4: Сложный граф с множеством узлов
 */
export const ComplexGraphProgress: React.FC = () => {
  const graphData: GraphData = {
    nodes: [
      { id: '1', title: 'Введение в React', status: 'completed' },
      { id: '2', title: 'Components', status: 'completed' },
      { id: '3', title: 'State & Props', status: 'in_progress' },
      { id: '4', title: 'Hooks', status: 'not_started' },
      { id: '5', title: 'Context API', status: 'locked' },
      { id: '6', title: 'Routing', status: 'locked' },
      { id: '7', title: 'Redux', status: 'locked' },
      { id: '8', title: 'Testing', status: 'locked' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
      { source: '3', target: '4', type: 'prerequisite' },
      { source: '4', target: '5', type: 'prerequisite' },
      { source: '4', target: '6', type: 'prerequisite' },
      { source: '5', target: '7', type: 'suggested' },
      { source: '6', target: '7', type: 'suggested' },
      { source: '7', target: '8', type: 'prerequisite' },
    ],
  };

  const progressData: { [key: string]: ProgressNodeData } = {
    '1': { status: 'completed', percentage: 100, completedAt: '2025-11-15' },
    '2': { status: 'completed', percentage: 100, completedAt: '2025-11-22' },
    '3': { status: 'in_progress', percentage: 75 },
    '4': { status: 'not_started', percentage: 0 },
    '5': { status: 'locked', percentage: 0 },
    '6': { status: 'locked', percentage: 0 },
    '7': { status: 'locked', percentage: 0 },
    '8': { status: 'locked', percentage: 0 },
  };

  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">Сложный граф с прогрессом</h3>
      <p className="text-sm text-gray-600 mb-4">
        Курс React: 8 уроков, 2 завершено, 1 в процессе
      </p>
      <GraphVisualization
        data={graphData}
        progressData={progressData}
        currentLessonId="3"
        height={600}
        showLegend={true}
      />
    </Card>
  );
};

/**
 * Пример 5: Без легенды (компактный вид)
 */
export const WithoutLegend: React.FC = () => {
  const graphData: GraphData = {
    nodes: [
      { id: '1', title: 'Урок A', status: 'completed' },
      { id: '2', title: 'Урок B', status: 'in_progress' },
      { id: '3', title: 'Урок C', status: 'not_started' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
    ],
  };

  const progressData: { [key: string]: ProgressNodeData } = {
    '1': { status: 'completed', percentage: 100 },
    '2': { status: 'in_progress', percentage: 50 },
    '3': { status: 'not_started', percentage: 0 },
  };

  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">Компактный вид (без легенды)</h3>
      <GraphVisualization
        data={graphData}
        progressData={progressData}
        height={400}
        showLegend={false}
      />
    </Card>
  );
};

/**
 * Пример 6: С GraphStatistics над графом
 */
export const WithStatistics: React.FC = () => {
  const graphData: GraphData = {
    nodes: [
      { id: '1', title: 'Введение', status: 'completed' },
      { id: '2', title: 'Основы', status: 'completed' },
      { id: '3', title: 'Практика', status: 'in_progress' },
      { id: '4', title: 'Продвинутый', status: 'not_started' },
      { id: '5', title: 'Тестирование', status: 'locked' },
    ],
    links: [
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
      { source: '3', target: '4', type: 'prerequisite' },
      { source: '4', target: '5', type: 'prerequisite' },
    ],
  };

  const progressData: ProgressData = {
    '1': { status: 'completed', percentage: 100, completedAt: '2025-12-01T10:00:00Z' },
    '2': { status: 'completed', percentage: 100, completedAt: '2025-12-03T15:30:00Z' },
    '3': { status: 'in_progress', percentage: 60 },
    '4': { status: 'not_started', percentage: 0 },
    '5': { status: 'locked', percentage: 0 },
  };

  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold mb-4">С общей статистикой</h3>

      {/* Статистика над графом */}
      <div className="mb-4">
        <GraphStatistics
          progressData={progressData}
          totalTimeSpent={145}
          lastActivity={new Date().toISOString()}
        />
      </div>

      {/* Граф с прогрессом */}
      <GraphVisualization
        data={graphData}
        progressData={progressData}
        currentLessonId="3"
        height={500}
        showLegend={true}
      />
    </Card>
  );
};

/**
 * Демо всех примеров
 */
export const ProgressVisualizationDemo: React.FC = () => {
  return (
    <div className="space-y-8 p-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Progress Visualization Examples</h1>
        <p className="text-gray-600 mb-8">
          Примеры интеграции визуализации прогресса в граф знаний
        </p>
      </div>

      <BasicProgressVisualization />
      <WithCurrentLesson />
      <DynamicProgress />
      <ComplexGraphProgress />
      <WithoutLegend />
      <WithStatistics />
    </div>
  );
};

export default ProgressVisualizationDemo;
