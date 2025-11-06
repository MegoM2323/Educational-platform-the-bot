import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { parentDashboardAPI, type ChildData } from '@/integrations/api/dashboard';

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
      amount: data?.amount || 5000.00,
      description: data?.description || 'Оплата за предмет',
      create_subscription: data?.create_subscription !== false, // По умолчанию создаем подписку
    }),
    onSuccess: (response) => {
      qc.invalidateQueries({ queryKey: ['parent-children'] });
      qc.invalidateQueries({ queryKey: ['parent-child-subjects', childId] });
      // Если есть URL для оплаты, перенаправляем
      const paymentUrl = response?.confirmation_url || response?.payment_url || response?.return_url;
      if (paymentUrl) {
        const isTestPayment = paymentUrl.includes('test=true') || response?.test === true;
        if (!isTestPayment) {
          window.location.href = paymentUrl;
        }
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
