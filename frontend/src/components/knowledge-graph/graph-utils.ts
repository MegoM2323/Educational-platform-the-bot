import { GraphData, GraphNode, GraphLink, D3Node, D3Link } from './graph-types';

// Цветовая схема для статусов узлов
export const NODE_COLORS = {
  not_started: '#94a3b8',  // gray
  in_progress: '#3b82f6',  // blue
  completed: '#22c55e',    // green
  locked: '#ef4444',       // red
} as const;

// Цвета для ховера (ярче)
export const NODE_HOVER_COLORS = {
  not_started: '#cbd5e1',
  in_progress: '#60a5fa',
  completed: '#4ade80',
  locked: '#f87171',
} as const;

// Константы для размеров
export const CONSTANTS = {
  NODE_RADIUS: 30,
  NODE_LABEL_OFFSET: 40,
  ARROW_SIZE: 6,
  STROKE_WIDTH: 2,
  HOVER_STROKE_WIDTH: 4,
  MIN_ZOOM: 0.5,
  MAX_ZOOM: 3,
  MARGIN: 50,
} as const;

// Силы для симуляции
export const FORCE_CONFIG = {
  charge: -400,            // Отталкивание узлов
  linkDistance: 150,       // Расстояние между связанными узлами
  collideRadius: 40,       // Радиус коллизии
  centerStrength: 0.05,    // Сила притяжения к центру
} as const;

/**
 * Преобразует данные графа в формат D3
 */
export const transformGraphData = (data: GraphData): { nodes: D3Node[]; links: D3Link[] } => {
  // Создаем копии узлов с начальными позициями
  // Если позиции не заданы, распределяем узлы по кругу чтобы избежать наложения
  const nodes: D3Node[] = data.nodes.map((node, index) => {
    let x = node.x;
    let y = node.y;

    // Если позиция не задана, используем круговую раскладку
    if (x === null || x === undefined || y === null || y === undefined) {
      const angle = (index / data.nodes.length) * 2 * Math.PI;
      const radius = 200;
      x = 400 + radius * Math.cos(angle);
      y = 300 + radius * Math.sin(angle);
    }

    return {
      ...node,
      x,
      y,
      fx: node.fx ?? null,
      fy: node.fy ?? null,
    };
  });

  // Создаем индекс узлов для быстрого поиска
  const nodeMap = new Map<string, D3Node>();
  nodes.forEach(node => nodeMap.set(node.id, node));

  // Преобразуем связи, заменяя ID на объекты узлов
  const links: D3Link[] = data.links
    .map(link => {
      const source = typeof link.source === 'string'
        ? nodeMap.get(link.source)
        : link.source as D3Node;
      const target = typeof link.target === 'string'
        ? nodeMap.get(link.target)
        : link.target as D3Node;

      if (!source || !target) {
        console.warn('Link references non-existent node:', link);
        return null;
      }

      return {
        ...link,
        source,
        target,
      };
    })
    .filter((link): link is D3Link => link !== null);

  return { nodes, links };
};

/**
 * Получает цвет узла по статусу
 */
export const getNodeColor = (status: GraphNode['status'], isHovered: boolean = false): string => {
  return isHovered ? NODE_HOVER_COLORS[status] : NODE_COLORS[status];
};

/**
 * Получает opacity для заблокированного узла
 */
export const getNodeOpacity = (status: GraphNode['status']): number => {
  return status === 'locked' ? 0.5 : 1;
};

/**
 * Получает стиль линии для связи
 */
export const getLinkStyle = (type: GraphLink['type'], sourceLocked: boolean): string => {
  if (sourceLocked) {
    return '5,5'; // dashed для заблокированных
  }
  return type === 'prerequisite' ? '' : '2,2'; // сплошная для prerequisite, пунктир для suggested
};

/**
 * Вычисляет позицию стрелки на линии
 */
export const calculateArrowPosition = (
  source: { x: number; y: number },
  target: { x: number; y: number },
  nodeRadius: number
): { x: number; y: number; angle: number } => {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const angle = Math.atan2(dy, dx);
  const distance = Math.sqrt(dx * dx + dy * dy);

  // Позиция стрелки - на краю целевого узла
  const arrowDistance = distance - nodeRadius;
  const x = source.x + Math.cos(angle) * arrowDistance;
  const y = source.y + Math.sin(angle) * arrowDistance;

  return { x, y, angle };
};

/**
 * Валидирует структуру графа
 */
export const validateGraphData = (data: GraphData): { valid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (!data.nodes || !Array.isArray(data.nodes)) {
    errors.push('Nodes must be an array');
  }

  if (!data.links || !Array.isArray(data.links)) {
    errors.push('Links must be an array');
  }

  const nodeIds = new Set(data.nodes.map(n => n.id));

  data.links.forEach((link, index) => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;

    if (!nodeIds.has(sourceId)) {
      errors.push(`Link ${index} references non-existent source node: ${sourceId}`);
    }

    if (!nodeIds.has(targetId)) {
      errors.push(`Link ${index} references non-existent target node: ${targetId}`);
    }
  });

  // Проверка на циклические зависимости
  const hasCycle = detectCycle(data);
  if (hasCycle) {
    errors.push('Graph contains cycles in prerequisite dependencies');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
};

/**
 * Обнаруживает циклы в графе зависимостей
 */
const detectCycle = (data: GraphData): boolean => {
  const adjList = new Map<string, string[]>();

  // Строим список смежности только для prerequisite связей
  data.nodes.forEach(node => adjList.set(node.id, []));
  data.links.forEach(link => {
    if (link.type === 'prerequisite') {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      adjList.get(sourceId)?.push(targetId);
    }
  });

  const visited = new Set<string>();
  const recStack = new Set<string>();

  const dfs = (nodeId: string): boolean => {
    visited.add(nodeId);
    recStack.add(nodeId);

    const neighbors = adjList.get(nodeId) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) {
          return true;
        }
      } else if (recStack.has(neighbor)) {
        return true; // Цикл найден
      }
    }

    recStack.delete(nodeId);
    return false;
  };

  for (const nodeId of adjList.keys()) {
    if (!visited.has(nodeId)) {
      if (dfs(nodeId)) {
        return true;
      }
    }
  }

  return false;
};

/**
 * Находит связанные узлы (соседи)
 */
export const getConnectedNodes = (nodeId: string, links: D3Link[]): Set<string> => {
  const connected = new Set<string>();

  links.forEach(link => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
    const targetId = typeof link.target === 'object' ? link.target.id : link.target;

    if (sourceId === nodeId) {
      connected.add(targetId);
    }
    if (targetId === nodeId) {
      connected.add(sourceId);
    }
  });

  return connected;
};

/**
 * Усекает длинный текст
 */
export const truncateText = (text: string, maxLength: number = 20): string => {
  if (text.length <= maxLength) {
    return text;
  }
  return text.slice(0, maxLength - 3) + '...';
};
