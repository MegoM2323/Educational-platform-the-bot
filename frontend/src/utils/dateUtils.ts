import { format } from 'date-fns';

/**
 * Форматирует Date объект в строку yyyy-MM-dd для передачи на backend
 * Использует локальную временную зону (не UTC)
 *
 * @param date - Date объект для форматирования
 * @returns Строка формата yyyy-MM-dd (например, "2025-12-06")
 */
export const formatDateOnly = (date: Date): string => {
  return format(date, 'yyyy-MM-dd');
};

/**
 * Форматирует Date объект в полный ISO timestamp для передачи на backend
 * Использует toISOString() для сохранения временной зоны
 *
 * @param date - Date объект для форматирования
 * @returns Строка формата ISO 8601 (например, "2025-12-06T10:30:00.000Z")
 */
export const formatTimestamp = (date: Date): string => {
  return date.toISOString();
};

/**
 * Получает начало недели (понедельник) для заданной даты
 *
 * @param date - Опциональная дата (по умолчанию - сегодня)
 * @returns Date объект начала недели (00:00:00)
 */
export const getWeekStart = (date: Date = new Date()): Date => {
  const result = new Date(date);
  const day = result.getDay();
  const diff = day === 0 ? -6 : 1 - day; // Если воскресенье (0), вернуться на 6 дней назад
  result.setDate(result.getDate() + diff);
  result.setHours(0, 0, 0, 0);
  return result;
};

/**
 * Получает конец недели (воскресенье) для заданной даты
 *
 * @param date - Опциональная дата (по умолчанию - сегодня)
 * @returns Date объект конца недели (23:59:59.999)
 */
export const getWeekEnd = (date: Date = new Date()): Date => {
  const result = new Date(date);
  const day = result.getDay();
  const diff = day === 0 ? 0 : 7 - day; // Если воскресенье (0), оставить как есть
  result.setDate(result.getDate() + diff);
  result.setHours(23, 59, 59, 999);
  return result;
};

/**
 * Получает диапазон текущей недели в формате для API
 *
 * @returns Объект с полями start и end (формат yyyy-MM-dd)
 */
export const getCurrentWeekRange = (): { start: string; end: string } => {
  const monday = getWeekStart();
  const sunday = getWeekEnd();

  return {
    start: formatDateOnly(monday),
    end: formatDateOnly(sunday),
  };
};
