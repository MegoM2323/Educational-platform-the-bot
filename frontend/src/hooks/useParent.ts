import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { logger } from '@/utils/logger';
import { parentDashboardAPI, type ChildData, type ParentDashboard } from '@/integrations/api/dashboard';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

export const useParentDashboard = () => {
  return useQuery<ParentDashboard>({
    queryKey: ['parent-dashboard'],
    queryFn: async () => {
      logger.debug('[useParentDashboard] Fetching dashboard data...');
      const response = await unifiedAPI.getParentDashboard();
      logger.debug('[useParentDashboard] Full response:', response);
      logger.debug('[useParentDashboard] Response.data:', response.data);
      logger.debug('[useParentDashboard] Response.data.children:', response.data?.children);

      if (response.error) {
        logger.error('[useParentDashboard] Error:', response.error);
        throw new Error(response.error);
      }

      if (!response.data) {
        logger.error('[useParentDashboard] No data in response!');
        throw new Error('Данные дашборда отсутствуют');
      }

      logger.debug('[useParentDashboard] Returning data with', response.data.children?.length || 0, 'children');
      return response.data;
    },
    staleTime: 60000, // 60 seconds - снижает нагрузку на сервер
    refetchOnWindowFocus: true,
    refetchOnMount: true,
  });
};

export const useParentChildren = () => {
  return useQuery<ChildData[]>({
    queryKey: ['parent-children'],
    queryFn: () => parentDashboardAPI.getChildren(),
    staleTime: 60000,
  });
};

export const useChildSubjects = (childId?: number) => {
  return useQuery<any[]>({
    queryKey: ['parent-child-subjects', childId],
    queryFn: () => parentDashboardAPI.getChildSubjects(childId!),
    enabled: !!childId,
    staleTime: 60000,
  });
};

export const useInitiatePayment = (childId: number, enrollmentId: number, data?: { amount?: number; description?: string; create_subscription?: boolean }) => {
  const qc = useQueryClient();
  return useMutation<any, Error, void>({
    mutationFn: () => parentDashboardAPI.initiatePayment(childId, enrollmentId, {
      // amount определяется на бэкенде в зависимости от режима (тестовый/обычный)
      ...(data?.amount && { amount: data.amount }),
      description: data?.description || 'Оплата за предмет',
      create_subscription: data?.create_subscription !== false, // По умолчанию создаем подписку
    }),
    onSuccess: (response) => {
      qc.invalidateQueries({ queryKey: ['parent-children'] });
      qc.invalidateQueries({ queryKey: ['parent-child-subjects', childId] });
      // Сохраняем payment_id перед переходом на оплату, чтобы при возврате можно было проверить статус
      if (response?.payment_id) {
        sessionStorage.setItem('pending_payment_id', response.payment_id);
      }
      
      // Если есть URL для оплаты, переходим в текущей вкладке
      const paymentUrl = response?.confirmation_url || response?.payment_url || response?.return_url;
      if (paymentUrl) {
        // Используем текущую вкладку для сохранения сессии и cookies
        window.location.href = paymentUrl;
      }
    },
  });
};

export const useChildProgress = (childId?: number) => {
  return useQuery<any>({
    queryKey: ['parent-child-progress', childId],
    queryFn: () => parentDashboardAPI.getChildProgress(childId!),
    enabled: !!childId,
    staleTime: 60000,
  });
};
