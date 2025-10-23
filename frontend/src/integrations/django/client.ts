// Django Backend API Client
const DJANGO_API_BASE_URL = import.meta.env.VITE_DJANGO_API_URL || 'http://localhost:8000/api';

export interface Payment {
  id: string;
  yookassa_payment_id?: string;
  amount: string;
  status: 'pending' | 'waiting_for_capture' | 'succeeded' | 'canceled';
  service_name: string;
  customer_fio: string;
  description: string;
  confirmation_url?: string;
  return_url?: string;
  metadata: Record<string, any>;
  created: string;
  updated: string;
  paid_at?: string;
}

export interface CreatePaymentRequest {
  amount: string;
  service_name: string;
  customer_fio: string;
  description?: string;
  return_url?: string;
  metadata?: Record<string, any>;
}

export interface Application {
  id: number;
  student_name: string;
  parent_name: string;
  phone: string;
  email: string;
  grade: number;
  goal?: string;
  message?: string;
  status: 'new' | 'processing' | 'approved' | 'rejected' | 'completed';
  created_at: string;
  updated_at: string;
  processed_at?: string;
  notes?: string;
}

export interface CreateApplicationRequest {
  student_name: string;
  parent_name: string;
  phone: string;
  email: string;
  grade: number;
  goal?: string;
  message?: string;
}

class DjangoAPIClient {
  private baseURL: string;

  constructor(baseURL: string = DJANGO_API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      credentials: 'include', // Для поддержки сессий Django
    };

    const response = await fetch(url, { ...defaultOptions, ...options });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Payment methods
  async createPayment(data: CreatePaymentRequest): Promise<Payment> {
    return this.request<Payment>('/payments/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPayment(id: string): Promise<Payment> {
    return this.request<Payment>(`/payments/${id}/`);
  }

  async getPayments(): Promise<Payment[]> {
    return this.request<Payment[]>('/payments/');
  }

  async getPaymentStatus(id: string): Promise<Payment> {
    return this.request<Payment>(`/payments/${id}/status/`);
  }

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health/');
  }

  // Application methods
  async createApplication(data: CreateApplicationRequest): Promise<Application> {
    return this.request<Application>('/applications/create/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getApplications(): Promise<Application[]> {
    return this.request<Application[]>('/applications/');
  }

  async getApplication(id: number): Promise<Application> {
    return this.request<Application>(`/applications/${id}/`);
  }

  async updateApplicationStatus(id: number, status: string, notes?: string): Promise<Application> {
    return this.request<Application>(`/applications/${id}/status/`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    });
  }

  async getApplicationStatistics(): Promise<{
    total: number;
    new: number;
    processing: number;
    approved: number;
    rejected: number;
    completed: number;
    recent_week: number;
  }> {
    return this.request('/applications/statistics/');
  }

  async testTelegramConnection(): Promise<{ status: string; message: string }> {
    return this.request('/applications/test-telegram/', {
      method: 'POST',
    });
  }
}

// Export singleton instance
export const djangoAPI = new DjangoAPIClient();

// Export class for custom instances
export { DjangoAPIClient };

