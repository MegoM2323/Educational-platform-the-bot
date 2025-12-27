import { describe, it, expect, vi, beforeEach } from 'vitest';
import { parentDashboardAPI } from '../dashboard';
import { unifiedAPI } from '../unifiedClient';
import { cacheInvalidationManager } from '@/services/cacheInvalidationManager';

// Mock unifiedAPI
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
    getParentDashboard: vi.fn(),
    getToken: vi.fn(() => 'mock-token'),
  },
}));

// Mock cacheInvalidationManager
vi.mock('@/services/cacheInvalidationManager', () => ({
  cacheInvalidationManager: {
    invalidateEndpoint: vi.fn(),
  },
}));

describe('parentDashboardAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getDashboard', () => {
    it('should fetch parent dashboard data', async () => {
      const mockDashboard = {
        parent: {
          id: 1,
          name: 'John Doe',
          email: 'john@example.com'
        },
        children: [
          {
            id: 1,
            name: 'Alice Doe',
            grade: '10A',
            goal: 'University preparation',
            tutor_name: 'Jane Smith',
            progress_percentage: 75,
            progress: 75,
            subjects: []
          }
        ],
        reports: [],
        statistics: {
          total_children: 1,
          average_progress: 75,
          completed_payments: 2,
          pending_payments: 0,
          overdue_payments: 0
        },
        total_children: 1
      };

      vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
        success: true,
        data: mockDashboard,
        error: null
      });

      const result = await parentDashboardAPI.getDashboard();

      expect(unifiedAPI.getParentDashboard).toHaveBeenCalled();
      expect(result.parent.name).toBe('John Doe');
      expect(result.children).toHaveLength(1);
      expect(result.statistics.total_children).toBe(1);
    });

    it('should throw error when data is missing', async () => {
      vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      await expect(parentDashboardAPI.getDashboard()).rejects.toThrow('Не удалось загрузить данные дашборда');
    });

    it('should throw error on request failure', async () => {
      vi.mocked(unifiedAPI.getParentDashboard).mockResolvedValue({
        success: false,
        data: null,
        error: 'Network error'
      });

      await expect(parentDashboardAPI.getDashboard()).rejects.toThrow('Network error');
    });
  });

  describe('getChildren', () => {
    it('should fetch children list', async () => {
      const mockChildren = [
        {
          id: 1,
          name: 'Alice',
          full_name: 'Alice Doe',
          email: 'alice@example.com',
          grade: '10A',
          goal: 'University',
          subjects: []
        },
        {
          id: 2,
          name: 'Bob',
          full_name: 'Bob Doe',
          email: 'bob@example.com',
          grade: '9B',
          subjects: []
        }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockChildren,
        error: null
      });

      const result = await parentDashboardAPI.getChildren();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/dashboard/parent/children/');
      expect(result).toHaveLength(2);
      expect(result[0].full_name).toBe('Alice Doe');
    });

    it('should return empty array when no children', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      const result = await parentDashboardAPI.getChildren();

      expect(result).toEqual([]);
    });
  });

  describe('getChildSubjects', () => {
    it('should fetch subjects for specific child', async () => {
      const mockSubjects = [
        {
          id: 1,
          name: 'Mathematics',
          teacher_name: 'John Teacher',
          payment_status: 'paid'
        },
        {
          id: 2,
          name: 'Physics',
          teacher_name: 'Jane Teacher',
          payment_status: 'pending'
        }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockSubjects,
        error: null
      });

      const result = await parentDashboardAPI.getChildSubjects(1);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/dashboard/parent/children/1/subjects/');
      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('Mathematics');
    });

    it('should return empty array for child without subjects', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      const result = await parentDashboardAPI.getChildSubjects(1);

      expect(result).toEqual([]);
    });
  });

  describe('getChildProgress', () => {
    it('should fetch progress data for child', async () => {
      const mockProgress = {
        overall_percentage: 78,
        completed_tasks: 15,
        total_tasks: 20,
        subjects_progress: [
          { subject: 'Math', progress: 85 },
          { subject: 'Physics', progress: 71 }
        ]
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockProgress,
        error: null
      });

      const result = await parentDashboardAPI.getChildProgress(1);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/dashboard/parent/children/1/progress/');
      expect(result.overall_percentage).toBe(78);
      expect(result.subjects_progress).toHaveLength(2);
    });

    it('should return empty object when no progress data', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      const result = await parentDashboardAPI.getChildProgress(1);

      expect(result).toEqual({});
    });
  });

  describe('initiatePayment', () => {
    it('should initiate payment with subscription', async () => {
      const mockPayment = {
        payment_id: 'pay_123',
        confirmation_url: 'https://yookassa.ru/checkout/123',
        amount: 5000,
        subscription_id: 'sub_456'
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockPayment,
        error: null
      });

      const result = await parentDashboardAPI.initiatePayment(1, 101, {
        amount: 5000,
        description: 'Monthly subscription',
        create_subscription: true
      });

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/dashboard/parent/children/1/payment/101/',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(String)
        })
      );

      // Проверяем что body содержит правильные данные (порядок не важен)
      const callArgs = vi.mocked(unifiedAPI.request).mock.calls[0];
      const bodyData = JSON.parse(callArgs[1].body);
      expect(bodyData).toEqual(expect.objectContaining({
        amount: 5000,
        description: 'Monthly subscription',
        create_subscription: true
      }));
      expect(result.confirmation_url).toBe('https://yookassa.ru/checkout/123');
      expect(cacheInvalidationManager.invalidateEndpoint).toHaveBeenCalledWith('/dashboard/parent/children/');
    });

    it('should initiate payment without explicit amount', async () => {
      const mockPayment = {
        payment_id: 'pay_123',
        confirmation_url: 'https://yookassa.ru/checkout/123'
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockPayment,
        error: null
      });

      await parentDashboardAPI.initiatePayment(1, 101, {
        description: 'Subject payment',
        create_subscription: false
      });

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/dashboard/parent/children/1/payment/101/',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('"create_subscription":false')
        })
      );
    });

    it('should throw error when payment data is missing', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      await expect(parentDashboardAPI.initiatePayment(1, 101, {
        description: 'Test'
      })).rejects.toThrow('Не удалось инициировать оплату');
    });

    it('should throw error on payment initiation failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Payment failed'
      });

      await expect(parentDashboardAPI.initiatePayment(1, 101, {
        description: 'Test'
      })).rejects.toThrow('Payment failed');
    });
  });

  describe('cancelSubscription', () => {
    it('should cancel subscription successfully', async () => {
      const mockResponse = {
        success: true,
        message: 'Subscription cancelled',
        expires_at: '2025-02-20T10:00:00Z'
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockResponse,
        error: null
      });

      const result = await parentDashboardAPI.cancelSubscription(1, 101);

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/dashboard/parent/children/1/subscription/101/cancel/',
        expect.objectContaining({
          method: 'POST'
        })
      );
      expect(result.message).toBe('Subscription cancelled');
      expect(cacheInvalidationManager.invalidateEndpoint).toHaveBeenCalledWith('/dashboard/parent/children/');
    });

    it('should throw error when cancellation data is missing', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      await expect(parentDashboardAPI.cancelSubscription(1, 101)).rejects.toThrow('Не удалось отменить подписку');
    });

    it('should throw error on cancellation failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Cancellation failed'
      });

      await expect(parentDashboardAPI.cancelSubscription(1, 101)).rejects.toThrow('Cancellation failed');
    });
  });

  describe('getPaymentHistory', () => {
    it('should fetch payment history', async () => {
      const mockPayments = [
        {
          id: 1,
          amount: 5000,
          status: 'succeeded',
          created_at: '2025-01-15T10:00:00Z',
          description: 'Monthly subscription'
        },
        {
          id: 2,
          amount: 5000,
          status: 'succeeded',
          created_at: '2025-01-08T10:00:00Z',
          description: 'Monthly subscription'
        }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockPayments,
        error: null
      });

      const result = await parentDashboardAPI.getPaymentHistory();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/dashboard/parent/payments/');
      expect(result).toHaveLength(2);
      expect(result[0].status).toBe('succeeded');
    });

    it('should return empty array when no payment history', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      const result = await parentDashboardAPI.getPaymentHistory();

      expect(result).toEqual([]);
    });
  });

  describe('getPaymentStatus', () => {
    it('should fetch payment status for child', async () => {
      const mockStatus = {
        has_active_subscription: true,
        next_payment_date: '2025-02-20T10:00:00Z',
        payment_amount: 5000,
        payment_status: 'active'
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockStatus,
        error: null
      });

      const result = await parentDashboardAPI.getPaymentStatus(1);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/dashboard/parent/children/1/payments/');
      expect(result.has_active_subscription).toBe(true);
      expect(result.payment_amount).toBe(5000);
    });

    it('should return empty object when no payment status', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      const result = await parentDashboardAPI.getPaymentStatus(1);

      expect(result).toEqual({});
    });
  });
});
