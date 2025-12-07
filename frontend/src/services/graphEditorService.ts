/**
 * Graph Editor Service
 * Утилиты и бизнес-логика для редактора графов
 */

import type { KnowledgeGraph, LessonDependency } from '@/types/knowledgeGraph';

/**
 * Проверка наличия цикла в графе
 * Использует алгоритм DFS для поиска циклов
 */
export const detectCycle = (
  lessons: number[],
  dependencies: Array<{ from: number; to: number }>
): boolean => {
  const graph = new Map<number, number[]>();

  // Построить граф смежности
  for (const lesson of lessons) {
    graph.set(lesson, []);
  }

  for (const dep of dependencies) {
    const adjacents = graph.get(dep.from) || [];
    adjacents.push(dep.to);
    graph.set(dep.from, adjacents);
  }

  // DFS для поиска цикла
  const visited = new Set<number>();
  const recursionStack = new Set<number>();

  const hasCycleDFS = (node: number): boolean => {
    visited.add(node);
    recursionStack.add(node);

    const neighbors = graph.get(node) || [];
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (hasCycleDFS(neighbor)) {
          return true;
        }
      } else if (recursionStack.has(neighbor)) {
        return true;
      }
    }

    recursionStack.delete(node);
    return false;
  };

  for (const lesson of lessons) {
    if (!visited.has(lesson)) {
      if (hasCycleDFS(lesson)) {
        return true;
      }
    }
  }

  return false;
};

/**
 * Проверка, создаст ли новая зависимость цикл
 */
export const wouldCreateCycle = (
  graph: KnowledgeGraph,
  newDependency: { from: number; to: number }
): boolean => {
  const lessonIds = graph.lessons.map((gl) => gl.lesson.id);
  const existingDeps = graph.dependencies.map((dep) => ({
    from: dep.from_lesson,
    to: dep.to_lesson,
  }));

  const allDeps = [...existingDeps, newDependency];

  return detectCycle(lessonIds, allDeps);
};

/**
 * Получить топологическую сортировку уроков
 * Возвращает null если граф содержит цикл
 */
export const topologicalSort = (
  lessons: number[],
  dependencies: Array<{ from: number; to: number }>
): number[] | null => {
  // Проверить наличие цикла
  if (detectCycle(lessons, dependencies)) {
    return null;
  }

  // Подсчитать входящие рёбра
  const inDegree = new Map<number, number>();
  const graph = new Map<number, number[]>();

  for (const lesson of lessons) {
    inDegree.set(lesson, 0);
    graph.set(lesson, []);
  }

  for (const dep of dependencies) {
    const adjacents = graph.get(dep.from) || [];
    adjacents.push(dep.to);
    graph.set(dep.from, adjacents);

    inDegree.set(dep.to, (inDegree.get(dep.to) || 0) + 1);
  }

  // Алгоритм Кана
  const queue: number[] = [];
  const result: number[] = [];

  // Добавить все уроки без prerequisites
  for (const [lesson, degree] of inDegree.entries()) {
    if (degree === 0) {
      queue.push(lesson);
    }
  }

  while (queue.length > 0) {
    const current = queue.shift()!;
    result.push(current);

    const neighbors = graph.get(current) || [];
    for (const neighbor of neighbors) {
      const newDegree = (inDegree.get(neighbor) || 0) - 1;
      inDegree.set(neighbor, newDegree);

      if (newDegree === 0) {
        queue.push(neighbor);
      }
    }
  }

  // Если не все уроки в результате - есть цикл
  if (result.length !== lessons.length) {
    return null;
  }

  return result;
};

/**
 * Получить зависимости урока (predecessors и successors)
 */
export const getLessonConnections = (
  lessonId: number,
  dependencies: LessonDependency[]
): {
  prerequisites: number[]; // Уроки, которые должны быть выполнены перед этим
  dependents: number[]; // Уроки, которые зависят от этого
} => {
  const prerequisites: number[] = [];
  const dependents: number[] = [];

  for (const dep of dependencies) {
    if (dep.to_lesson === lessonId) {
      prerequisites.push(dep.from_lesson);
    }
    if (dep.from_lesson === lessonId) {
      dependents.push(dep.to_lesson);
    }
  }

  return { prerequisites, dependents };
};

/**
 * Валидация графа перед сохранением
 */
export const validateGraph = (
  graph: KnowledgeGraph
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  // Проверка наличия уроков
  if (graph.lessons.length === 0) {
    errors.push('Граф должен содержать хотя бы один урок');
  }

  // Проверка наличия циклов
  const lessonIds = graph.lessons.map((gl) => gl.lesson.id);
  const deps = graph.dependencies.map((dep) => ({
    from: dep.from_lesson,
    to: dep.to_lesson,
  }));

  if (detectCycle(lessonIds, deps)) {
    errors.push('Граф содержит циклы. Удалите циклические зависимости.');
  }

  // Проверка, что все зависимости ссылаются на существующие уроки
  const lessonIdSet = new Set(lessonIds);
  for (const dep of graph.dependencies) {
    if (!lessonIdSet.has(dep.from_lesson)) {
      errors.push(`Зависимость ссылается на несуществующий урок (from: ${dep.from_lesson})`);
    }
    if (!lessonIdSet.has(dep.to_lesson)) {
      errors.push(`Зависимость ссылается на несуществующий урок (to: ${dep.to_lesson})`);
    }
  }

  // Проверка дублирующихся зависимостей
  const depSet = new Set<string>();
  for (const dep of graph.dependencies) {
    const key = `${dep.from_lesson}->${dep.to_lesson}`;
    if (depSet.has(key)) {
      errors.push(`Дублирующаяся зависимость: ${key}`);
    }
    depSet.add(key);
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

/**
 * Автоматическое расположение уроков (force-directed layout)
 * Простая версия для начала
 */
export const autoLayout = (
  lessons: number[],
  dependencies: Array<{ from: number; to: number }>,
  width: number = 800,
  height: number = 600
): Map<number, { x: number; y: number }> => {
  const positions = new Map<number, { x: number; y: number }>();

  // Простое кольцевое размещение
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 3;

  lessons.forEach((lesson, index) => {
    const angle = (2 * Math.PI * index) / lessons.length;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    positions.set(lesson, { x, y });
  });

  return positions;
};

/**
 * Расчёт статистики графа
 */
export const calculateGraphStats = (
  graph: KnowledgeGraph
): {
  totalLessons: number;
  totalDependencies: number;
  averageDependenciesPerLesson: number;
  maxDepth: number;
  unlockedLessons: number;
} => {
  const lessonIds = graph.lessons.map((gl) => gl.lesson.id);
  const deps = graph.dependencies.map((dep) => ({
    from: dep.from_lesson,
    to: dep.to_lesson,
  }));

  // Topological sort для вычисления глубины
  const sorted = topologicalSort(lessonIds, deps);
  let maxDepth = 0;

  if (sorted) {
    const depths = new Map<number, number>();
    for (const lesson of sorted) {
      const prerequisites = graph.dependencies
        .filter((dep) => dep.to_lesson === lesson)
        .map((dep) => dep.from_lesson);

      let depth = 0;
      for (const prereq of prerequisites) {
        depth = Math.max(depth, (depths.get(prereq) || 0) + 1);
      }

      depths.set(lesson, depth);
      maxDepth = Math.max(maxDepth, depth);
    }
  }

  const unlockedLessons = graph.lessons.filter((gl) => gl.is_unlocked).length;

  return {
    totalLessons: graph.lessons.length,
    totalDependencies: graph.dependencies.length,
    averageDependenciesPerLesson:
      graph.lessons.length > 0 ? graph.dependencies.length / graph.lessons.length : 0,
    maxDepth: maxDepth + 1, // +1 чтобы начать с 1 вместо 0
    unlockedLessons,
  };
};
