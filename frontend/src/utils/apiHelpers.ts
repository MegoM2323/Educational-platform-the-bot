/**
 * API Response Helper Functions
 * Утилиты для унифицированной обработки ответов API
 */

/**
 * Извлекает массив результатов из ответа API с различными форматами.
 * Обрабатывает как прямые массивы, так и пагинированные ответы.
 *
 * @param response - Ответ API (может быть массивом или объектом с пагинацией)
 * @returns Массив элементов, пустой массив если формат некорректен
 *
 * @example
 * // Обработка прямого массива
 * extractResults([1, 2, 3]) // возвращает [1, 2, 3]
 *
 * @example
 * // Обработка пагинированного ответа
 * extractResults({ count: 10, results: [1, 2, 3] }) // возвращает [1, 2, 3]
 *
 * @example
 * // Обработка вложенного ответа
 * extractResults({ data: { results: [1, 2, 3] } }) // возвращает [1, 2, 3]
 */
export function extractResults<T>(response: unknown): T[] {
  // Случай 1: Уже массив
  if (Array.isArray(response)) {
    return response;
  }

  // Случай 2: Пагинированный ответ с ключом results
  if (response && typeof response === 'object') {
    const obj = response as Record<string, unknown>;

    // Прямой ключ results
    if ('results' in obj && Array.isArray(obj.results)) {
      return obj.results as T[];
    }

    // Вложенная структура data.results
    if ('data' in obj && obj.data && typeof obj.data === 'object') {
      const data = obj.data as Record<string, unknown>;
      if ('results' in data && Array.isArray(data.results)) {
        return data.results as T[];
      }
    }
  }

  // Случай 3: Некорректный или неизвестный формат
  console.warn('[extractResults] Unknown response format:', response);
  return [];
}

/**
 * Type guard для проверки является ли ответ пагинированным
 *
 * @param response - Ответ API для проверки
 * @returns true если ответ является пагинированным объектом
 *
 * @example
 * if (isPaginatedResponse(data)) {
 *   console.log('Total count:', data.count);
 *   console.log('Results:', data.results);
 * }
 */
export function isPaginatedResponse<T>(
  response: unknown
): response is { count: number; results: T[]; next?: string; previous?: string } {
  return (
    response !== null &&
    typeof response === 'object' &&
    'results' in response &&
    Array.isArray((response as Record<string, unknown>).results)
  );
}
