/**
 * Утилиты для скачивания защищенных файлов с сервера
 */

/**
 * Скачивает защищенный файл с сервера используя токен авторизации
 * @param url - URL файла
 * @param filename - Имя файла для сохранения (опционально)
 * @param openInNewTab - Открыть файл в новой вкладке вместо скачивания
 */
export async function downloadProtectedFile(
  url: string,
  filename?: string,
  openInNewTab: boolean = true
): Promise<void> {
  try {
    // Получаем токен из localStorage
    let token = localStorage.getItem('authToken');
    
    // Если токен не найден в простом формате, пробуем загрузить из secure storage
    if (!token) {
      const secureItem = localStorage.getItem('bot_platform_auth_token');
      if (secureItem) {
        try {
          const parsed = JSON.parse(secureItem);
          token = parsed?.data || null;
        } catch (e) {
          console.warn('[fileDownload] Failed to parse secure storage token');
        }
      }
    }
    
    console.log('[fileDownload] Token check:', token ? 'Found' : 'NOT FOUND');
    console.log('[fileDownload] localStorage keys:', Object.keys(localStorage));
    
    if (!token) {
      throw new Error('Токен авторизации не найден. Пожалуйста, войдите в систему.');
    }

    // Исправляем Mixed Content - заменяем HTTP на HTTPS для продакшена
    let finalUrl = url;
    if (window.location.protocol === 'https:' && url.startsWith('http://')) {
      finalUrl = url.replace('http://', 'https://');
      console.log('[fileDownload] Fixed Mixed Content:', url, '→', finalUrl);
    }

    // Делаем запрос с токеном
    console.log('[fileDownload] Fetching:', finalUrl);
    console.log('[fileDownload] Token:', token ? `${token.substring(0, 10)}...` : 'MISSING');
    
    const response = await fetch(finalUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Token ${token}`,
      },
      credentials: 'include',
    });

    console.log('[fileDownload] Response status:', response.status, response.statusText);
    console.log('[fileDownload] Response headers:', Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Необходима авторизация для доступа к файлу. Попробуйте выйти и войти заново.');
      } else if (response.status === 403) {
        throw new Error('Доступ к файлу запрещен. Проверьте права доступа или попробуйте выйти и войти заново.');
      } else if (response.status === 404) {
        throw new Error('Файл не найден на сервере');
      } else {
        const errorText = await response.text().catch(() => response.statusText);
        console.error('[fileDownload] Error response:', errorText);
        throw new Error(`Ошибка загрузки файла (${response.status}): ${response.statusText}`);
      }
    }

    // Получаем blob
    const blob = await response.blob();

    // Определяем имя файла
    let finalFilename = filename;
    if (!finalFilename) {
      // Пытаемся извлечь имя файла из заголовка Content-Disposition
      const contentDisposition = response.headers.get('Content-Disposition');
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          finalFilename = filenameMatch[1];
        }
      }
      
      // Если не нашли в заголовке, извлекаем из URL
      if (!finalFilename) {
        const urlParts = url.split('/');
        finalFilename = urlParts[urlParts.length - 1];
      }
    }

    // Создаем URL для blob
    const blobUrl = window.URL.createObjectURL(blob);

    if (openInNewTab) {
      // Открываем в новой вкладке
      window.open(blobUrl, '_blank');
      
      // Освобождаем URL через некоторое время
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
      }, 1000);
    } else {
      // Скачиваем файл
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = finalFilename || 'download';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Освобождаем URL
      window.URL.revokeObjectURL(blobUrl);
    }
  } catch (error) {
    console.error('Error downloading protected file:', error);
    throw error;
  }
}

/**
 * Проверяет, является ли URL медиа-файлом с сервера
 */
export function isProtectedMediaUrl(url: string): boolean {
  if (!url) return false;
  
  // Проверяем, что это URL с нашего сервера и это media файл
  return url.includes('/media/') || url.includes('localhost:8000/media/') || url.includes('the-bot.ru/media/');
}

/**
 * Обработчик клика по ссылке на защищенный файл
 */
export async function handleProtectedFileClick(
  event: React.MouseEvent,
  fileUrl: string,
  filename?: string,
  openInNewTab: boolean = true
): Promise<void> {
  event.preventDefault();
  
  if (!isProtectedMediaUrl(fileUrl)) {
    // Если это не защищенный файл, открываем обычным способом
    window.open(fileUrl, '_blank');
    return;
  }

  try {
    await downloadProtectedFile(fileUrl, filename, openInNewTab);
  } catch (error: any) {
    console.error('Failed to open protected file:', error);
    alert(error.message || 'Ошибка при открытии файла');
  }
}

