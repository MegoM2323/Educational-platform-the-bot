/**
 * GraphStatistics Examples
 * Примеры использования компонента статистики прогресса
 */
import React, { useState, useEffect } from 'react';
import { GraphStatistics, GraphStatisticsCompact } from './GraphStatistics';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ProgressData } from './progressUtils';

/**
 * Пример 1: Базовая статистика
 */
export const BasicStatistics: React.FC = () => {
  const progressData: ProgressData = {
    '1': { status: 'completed', percentage: 100, completedAt: '2025-12-01T10:00:00Z' },
    '2': { status: 'completed', percentage: 100, completedAt: '2025-12-03T15:30:00Z' },
    '3': { status: 'in_progress', percentage: 45 },
    '4': { status: 'not_started', percentage: 0 },
    '5': { status: 'locked', percentage: 0 },
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Базовая статистика</h3>
      <GraphStatistics
        progressData={progressData}
        totalTimeSpent={120}
        lastActivity={new Date().toISOString()}
      />
    </div>
  );
};

/**
 * Пример 2: Компактная статистика
 */
export const CompactStatistics: React.FC = () => {
  const progressData: ProgressData = {
    '1': { status: 'completed', percentage: 100 },
    '2': { status: 'in_progress', percentage: 67 },
    '3': { status: 'not_started', percentage: 0 },
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Компактная статистика</h3>
      <GraphStatisticsCompact progressData={progressData} />
    </div>
  );
};

/**
 * Пример 3: Статистика с динамическим обновлением
 */
export const DynamicStatistics: React.FC = () => {
  const [progress, setProgress] = useState<ProgressData>({
    '1': { status: 'completed', percentage: 100 },
    '2': { status: 'in_progress', percentage: 30 },
    '3': { status: 'not_started', percentage: 0 },
    '4': { status: 'not_started', percentage: 0 },
  });

  const [timeSpent, setTimeSpent] = useState(60);
  const [lastActivity, setLastActivity] = useState(new Date().toISOString());

  const simulateProgress = () => {
    setProgress((prev) => {
      const lesson2Percent = prev['2'].percentage;

      if (lesson2Percent < 100) {
        return {
          ...prev,
          '2': {
            status: lesson2Percent + 20 >= 100 ? 'completed' : 'in_progress',
            percentage: Math.min(100, lesson2Percent + 20),
            completedAt:
              lesson2Percent + 20 >= 100 ? new Date().toISOString() : undefined,
          },
        };
      } else if (prev['3'].status === 'not_started') {
        return {
          ...prev,
          '3': { status: 'in_progress', percentage: 10 },
        };
      }

      return prev;
    });

    setTimeSpent((prev) => prev + 15);
    setLastActivity(new Date().toISOString());
  };

  const resetProgress = () => {
    setProgress({
      '1': { status: 'completed', percentage: 100 },
      '2': { status: 'in_progress', percentage: 30 },
      '3': { status: 'not_started', percentage: 0 },
      '4': { status: 'not_started', percentage: 0 },
    });
    setTimeSpent(60);
    setLastActivity(new Date().toISOString());
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Динамическое обновление статистики</h3>
      <div className="flex gap-2">
        <Button type="button" onClick={simulateProgress}>
          Увеличить прогресс
        </Button>
        <Button type="button" variant="outline" onClick={resetProgress}>
          Сбросить
        </Button>
      </div>
      <GraphStatistics
        progressData={progress}
        totalTimeSpent={timeSpent}
        lastActivity={lastActivity}
      />
    </div>
  );
};

/**
 * Пример 4: Статистика с real-time обновлением
 */
export const RealTimeStatistics: React.FC = () => {
  const [progress, setProgress] = useState<ProgressData>({
    '1': { status: 'completed', percentage: 100 },
    '2': { status: 'in_progress', percentage: 45 },
    '3': { status: 'not_started', percentage: 0 },
  });

  const [timeSpent, setTimeSpent] = useState(90);
  const [lastActivity] = useState(new Date().toISOString());

  // Симуляция real-time обновлений (каждые 5 секунд)
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        const lesson2Percent = prev['2'].percentage;
        if (lesson2Percent < 100) {
          return {
            ...prev,
            '2': {
              status: lesson2Percent + 5 >= 100 ? 'completed' : 'in_progress',
              percentage: Math.min(100, lesson2Percent + 5),
            },
          };
        }
        return prev;
      });

      setTimeSpent((prev) => prev + 5);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Real-time обновление (каждые 5 сек)</h3>
      <p className="text-sm text-gray-600">
        Прогресс автоматически увеличивается каждые 5 секунд
      </p>
      <GraphStatistics
        progressData={progress}
        totalTimeSpent={timeSpent}
        lastActivity={lastActivity}
      />
    </div>
  );
};

/**
 * Пример 5: Полностью завершенный курс
 */
export const CompletedCourse: React.FC = () => {
  const progressData: ProgressData = {
    '1': { status: 'completed', percentage: 100, completedAt: '2025-11-01T10:00:00Z' },
    '2': { status: 'completed', percentage: 100, completedAt: '2025-11-10T14:30:00Z' },
    '3': { status: 'completed', percentage: 100, completedAt: '2025-11-20T16:45:00Z' },
    '4': { status: 'completed', percentage: 100, completedAt: '2025-11-28T11:20:00Z' },
    '5': { status: 'completed', percentage: 100, completedAt: '2025-12-05T09:15:00Z' },
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Завершенный курс (100%)</h3>
      <GraphStatistics
        progressData={progressData}
        totalTimeSpent={450}
        lastActivity="2025-12-05T09:15:00Z"
      />
    </div>
  );
};

/**
 * Пример 6: Только начатый курс
 */
export const JustStartedCourse: React.FC = () => {
  const progressData: ProgressData = {
    '1': { status: 'in_progress', percentage: 10 },
    '2': { status: 'not_started', percentage: 0 },
    '3': { status: 'locked', percentage: 0 },
    '4': { status: 'locked', percentage: 0 },
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Только начатый курс</h3>
      <GraphStatistics
        progressData={progressData}
        totalTimeSpent={15}
        lastActivity={new Date().toISOString()}
      />
    </div>
  );
};

/**
 * Пример 7: Без дополнительных данных (только прогресс)
 */
export const MinimalStatistics: React.FC = () => {
  const progressData: ProgressData = {
    '1': { status: 'completed', percentage: 100 },
    '2': { status: 'in_progress', percentage: 50 },
    '3': { status: 'not_started', percentage: 0 },
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Минимальная статистика</h3>
      <GraphStatistics progressData={progressData} />
    </div>
  );
};

/**
 * Пример 8: Использование с графом
 */
export const IntegratedWithGraph: React.FC = () => {
  const progressData: ProgressData = {
    '1': { status: 'completed', percentage: 100 },
    '2': { status: 'completed', percentage: 100 },
    '3': { status: 'in_progress', percentage: 75 },
    '4': { status: 'not_started', percentage: 0 },
    '5': { status: 'locked', percentage: 0 },
    '6': { status: 'locked', percentage: 0 },
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Интеграция с графом знаний</h3>
      <p className="text-sm text-gray-600">
        Статистика отображается над графом для общего обзора прогресса
      </p>

      {/* Статистика над графом */}
      <GraphStatistics
        progressData={progressData}
        totalTimeSpent={180}
        lastActivity={new Date().toISOString()}
      />

      {/* Здесь будет граф */}
      <Card className="p-8 bg-gray-50">
        <p className="text-center text-gray-500">
          [Здесь отображается GraphVisualization с progressData]
        </p>
      </Card>
    </div>
  );
};

/**
 * Демо всех примеров
 */
export const GraphStatisticsDemo: React.FC = () => {
  return (
    <div className="space-y-8 p-8 max-w-6xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold mb-2">GraphStatistics Examples</h1>
        <p className="text-gray-600 mb-8">
          Примеры использования компонента статистики прогресса
        </p>
      </div>

      <BasicStatistics />
      <CompactStatistics />
      <DynamicStatistics />
      <RealTimeStatistics />
      <CompletedCourse />
      <JustStartedCourse />
      <MinimalStatistics />
      <IntegratedWithGraph />
    </div>
  );
};

export default GraphStatisticsDemo;
