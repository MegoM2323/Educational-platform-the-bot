/**
 * Утилиты для безопасного парсинга JSON
 */

export interface SafeJsonResult<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Безопасно парсит JSON из Response
 */
export async function safeJsonParse<T = any>(
  response: Response,
  defaultValue?: T
): Promise<SafeJsonResult<T>> {
  try {
    // Проверяем статус ответа
    if (!response.ok) {
      return {
        success: false,
        error: `HTTP ${response.status}: ${response.statusText}`,
        data: defaultValue
      };
    }

    // Обработка 204 No Content и других статусов без тела ответа
    if (response.status === 204 || response.status === 205) {
      return {
        success: true,
        data: defaultValue as T
      };
    }

    // Проверяем Content-Type
    const contentType = response.headers.get('content-type');
    if (contentType && !contentType.includes('application/json') && !contentType.includes('text/json')) {
      console.warn(`Unexpected content type: ${contentType}`);
    }

    // Получаем текст ответа
    const text = await response.text();

    // Проверяем, что текст не пустой
    if (!text.trim()) {
      // Пустой ответ для успешного запроса считаем успехом (например, DELETE без тела)
      return {
        success: true,
        data: defaultValue as T
      };
    }

    // Парсим JSON
    const data = JSON.parse(text);

    return {
      success: true,
      data
    };

  } catch (error) {
    console.error('JSON parse error:', error);

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown JSON parse error',
      data: defaultValue
    };
  }
}

/**
 * Безопасно парсит JSON из строки
 */
export function safeJsonStringParse<T = any>(
  text: string,
  defaultValue?: T
): SafeJsonResult<T> {
  try {
    if (!text || !text.trim()) {
      return {
        success: false,
        error: 'Empty string',
        data: defaultValue
      };
    }

    const data = JSON.parse(text);
    
    return {
      success: true,
      data
    };

  } catch (error) {
    console.error('JSON string parse error:', error);
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown JSON parse error',
      data: defaultValue
    };
  }
}

/**
 * Проверяет, является ли строка валидным JSON
 */
export function isValidJson(text: string): boolean {
  try {
    JSON.parse(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * Безопасно сериализует данные в JSON
 */
export function safeJsonStringify(data: any, defaultValue: string = '{}'): string {
  try {
    return JSON.stringify(data);
  } catch (error) {
    console.error('JSON stringify error:', error);
    return defaultValue;
  }
}
