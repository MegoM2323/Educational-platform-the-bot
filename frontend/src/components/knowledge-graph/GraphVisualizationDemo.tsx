import React, { useState } from 'react';
import { GraphVisualization } from './GraphVisualization';
import { GraphData } from './graph-types';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

/**
 * Демонстрационный компонент для GraphVisualization
 * Показывает пример использования с реальными данными
 */
export const GraphVisualizationDemo: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Пример данных: граф зависимостей уроков
  const sampleData: GraphData = {
    nodes: [
      { id: '1', title: 'Введение в Python', status: 'completed' },
      { id: '2', title: 'Переменные и типы данных', status: 'completed' },
      { id: '3', title: 'Условные операторы', status: 'in_progress' },
      { id: '4', title: 'Циклы', status: 'not_started' },
      { id: '5', title: 'Функции', status: 'locked' },
      { id: '6', title: 'Списки и кортежи', status: 'not_started' },
      { id: '7', title: 'Словари', status: 'locked' },
      { id: '8', title: 'Файлы и исключения', status: 'locked' },
      { id: '9', title: 'ООП: Классы', status: 'locked' },
      { id: '10', title: 'ООП: Наследование', status: 'locked' },
      { id: '11', title: 'Модули и пакеты', status: 'locked' },
      { id: '12', title: 'Итоговый проект', status: 'locked' },
    ],
    links: [
      // Основная цепочка
      { source: '1', target: '2', type: 'prerequisite' },
      { source: '2', target: '3', type: 'prerequisite' },
      { source: '3', target: '4', type: 'prerequisite' },
      { source: '4', target: '5', type: 'prerequisite' },

      // Параллельная ветка
      { source: '2', target: '6', type: 'prerequisite' },
      { source: '6', target: '7', type: 'prerequisite' },

      // Продвинутые темы
      { source: '5', target: '9', type: 'prerequisite' },
      { source: '9', target: '10', type: 'prerequisite' },
      { source: '7', target: '8', type: 'prerequisite' },
      { source: '5', target: '11', type: 'prerequisite' },

      // Финальный проект требует всего
      { source: '10', target: '12', type: 'prerequisite' },
      { source: '8', target: '12', type: 'prerequisite' },
      { source: '11', target: '12', type: 'prerequisite' },

      // Рекомендованные связи
      { source: '4', target: '6', type: 'suggested' },
      { source: '8', target: '11', type: 'suggested' },
    ],
  };

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode(nodeId);
    const node = sampleData.nodes.find(n => n.id === nodeId);
    if (node) {
      toast.info(`Выбран урок: ${node.title}`, {
        description: `Статус: ${getStatusText(node.status)}`,
      });
    }
  };

  const handleNodeHover = (nodeId: string | null) => {
    // Можно добавить логику для отображения тултипа
    console.log('Hovered node:', nodeId);
  };

  const getStatusText = (status: string): string => {
    const statusMap: Record<string, string> = {
      not_started: 'Не начат',
      in_progress: 'В процессе',
      completed: 'Завершен',
      locked: 'Заблокирован',
    };
    return statusMap[status] || status;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Граф знаний: Курс Python</CardTitle>
          <CardDescription>
            Интерактивная визуализация зависимостей между уроками.
            Кликните на узел для просмотра деталей, перетащите для изменения позиции.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Информация о выбранном узле */}
            {selectedNode && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="font-medium">Выбранный урок:</p>
                <p className="text-lg">
                  {sampleData.nodes.find(n => n.id === selectedNode)?.title}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  Статус: {getStatusText(
                    sampleData.nodes.find(n => n.id === selectedNode)?.status || ''
                  )}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => setSelectedNode(null)}
                >
                  Очистить выбор
                </Button>
              </div>
            )}

            {/* График */}
            <GraphVisualization
              data={sampleData}
              onNodeClick={handleNodeClick}
              onNodeHover={handleNodeHover}
              isEditable={false}
              height={700}
            />

            {/* Инструкции */}
            <Card className="bg-gray-50">
              <CardHeader>
                <CardTitle className="text-base">Как использовать:</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <ul className="list-disc list-inside space-y-1">
                  <li>Наведите курсор на узел для подсветки связанных уроков</li>
                  <li>Кликните на узел для просмотра деталей</li>
                  <li>Перетащите узел для изменения его позиции</li>
                  <li>Используйте колесико мыши для масштабирования</li>
                  <li>Кликните и перетащите фон для перемещения по графу</li>
                  <li>Используйте кнопки управления для зума</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>

      {/* Статистика */}
      <Card>
        <CardHeader>
          <CardTitle>Статистика графа</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-muted-foreground">Завершено</p>
              <p className="text-2xl font-bold text-green-600">
                {sampleData.nodes.filter(n => n.status === 'completed').length}
              </p>
            </div>
            <div className="p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-muted-foreground">В процессе</p>
              <p className="text-2xl font-bold text-blue-600">
                {sampleData.nodes.filter(n => n.status === 'in_progress').length}
              </p>
            </div>
            <div className="p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-muted-foreground">Не начато</p>
              <p className="text-2xl font-bold text-gray-600">
                {sampleData.nodes.filter(n => n.status === 'not_started').length}
              </p>
            </div>
            <div className="p-4 bg-red-50 rounded-lg">
              <p className="text-sm text-muted-foreground">Заблокировано</p>
              <p className="text-2xl font-bold text-red-600">
                {sampleData.nodes.filter(n => n.status === 'locked').length}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default GraphVisualizationDemo;
