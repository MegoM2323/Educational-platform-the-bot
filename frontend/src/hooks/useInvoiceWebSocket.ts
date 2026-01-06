/**
 * React hook для подключения к WebSocket обновлениям счетов
 * Автоматически подключается при монтировании компонента и отключается при размонтировании
 */

import { useEffect } from 'react';
import { useAuth } from './useAuth';
import { invoiceWebSocketService, InvoiceEventHandlers } from '@/services/invoiceWebSocketService';
import { logger } from '@/utils/logger';

/**
 * Hook для подключения к WebSocket обновлениям счетов
 *
 * @example
 * ```tsx
 * const { on, off, isConnected } = useInvoiceWebSocket();
 *
 * useEffect(() => {
 *   const handleUpdate = (data) => {
 *     console.log('Invoice updated:', data);
 *     queryClient.invalidateQueries(['invoices']);
 *   };
 *
 *   on('invoice_updated', handleUpdate);
 *   return () => off('invoice_updated', handleUpdate);
 * }, []);
 * ```
 */
export const useInvoiceWebSocket = () => {
  const { user } = useAuth();

  useEffect(() => {
    // Подключаемся только если пользователь аутентифицирован
    if (!user?.id) {
      logger.debug('[useInvoiceWebSocket] User not authenticated, skipping WebSocket connection');
      return;
    }

    logger.info('[useInvoiceWebSocket] Connecting to invoice WebSocket for user:', user.id);

    try {
      // Подключаемся к WebSocket без обработчиков (они будут добавлены через on())
      if (invoiceWebSocketService && invoiceWebSocketService.connect) {
        invoiceWebSocketService.connect({});
      }
    } catch (error) {
      logger.error('[useInvoiceWebSocket] Failed to connect to WebSocket:', error);
    }

    // Cleanup при размонтировании компонента
    return () => {
      logger.info('[useInvoiceWebSocket] Disconnecting from invoice WebSocket');
      try {
        if (invoiceWebSocketService && invoiceWebSocketService.disconnect) {
          invoiceWebSocketService.disconnect();
        }
      } catch (error) {
        logger.error('[useInvoiceWebSocket] Failed to disconnect from WebSocket:', error);
      }
    };
  }, [user?.id]);

  return {
    /**
     * Подписаться на событие WebSocket
     * @param event - Тип события (invoice.created, invoice.status_update, invoice.paid)
     * @param callback - Функция обработчик
     */
    on: (event: keyof InvoiceEventHandlers, callback: Function) => {
      // Динамически добавляем обработчик в существующие обработчики сервиса
      const handlers: InvoiceEventHandlers = {};
      handlers[event] = callback as any;
      invoiceWebSocketService.connect(handlers);
    },

    /**
     * Отписаться от события WebSocket
     * Примечание: в текущей реализации invoiceWebSocketService нет метода off,
     * поэтому отписка происходит через переподключение без обработчика
     */
    off: (event: keyof InvoiceEventHandlers, callback: Function) => {
      logger.debug('[useInvoiceWebSocket] Unsubscribing from event:', event);
      // В текущей реализации сервиса нет метода off, поэтому просто логируем
      // Отключение произойдет при размонтировании компонента
    },

    /**
     * Проверить состояние WebSocket соединения
     */
    isConnected: () => invoiceWebSocketService.isConnected(),

    /**
     * Подписаться на изменения состояния соединения
     */
    onConnectionChange: (callback: (connected: boolean) => void) => {
      invoiceWebSocketService.onConnectionChange(callback);
    },
  };
};
