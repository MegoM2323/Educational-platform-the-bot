// Unified API Client for THE_BOT_platform
// Consolidates all API communication between frontend and backend
import { safeJsonParse } from '../../utils/jsonUtils';
import { errorHandlingService } from '../../services/errorHandlingService';
import { retryService } from '../../services/retryService';
import { errorLoggingService } from '../../services/errorLoggingService';
import { performanceMonitoringService } from '../../services/performanceMonitoringService';
import { cacheService } from '../../services/cacheService';

// Environment configuration
let API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DJANGO_API_URL) || 'http://localhost:8000/api';
// Нормализуем базовый URL: гарантируем окончание на /api
if (!API_BASE_URL.endsWith('/api')) {
  API_BASE_URL = API_BASE_URL.replace(/\/$/, '') + '/api';
}
const WS_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_WS_URL) || 'ws://localhost:8000/ws';

// Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: 'student' | 'teacher' | 'parent' | 'tutor';
  role_display: string;
  phone: string;
  avatar?: string;
  is_verified: boolean;
  is_staff?: boolean;
  date_joined: string;
  full_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
  message: string;
  refresh_token?: string;
  expires_at?: string;
}

export interface TokenResponse {
  token: string;
  refresh_token?: string;
  expires_at: string;
}

// Dashboard Types
export interface StudentDashboard {
  materials_count: number;
  completed_materials: number;
  progress_percentage: number;
  recent_materials: Array<{
    id: number;
    title: string;
    subject: string;
    assigned_date: string;
    completion_status: string;
  }>;
  upcoming_deadlines: Array<{
    id: number;
    title: string;
    deadline: string;
  }>;
}

export interface TeacherDashboard {
  total_students: number;
  total_materials: number;
  pending_reports: number;
  recent_activity: Array<{
    id: number;
    student_name: string;
    material_title: string;
    action: string;
    timestamp: string;
  }>;
}

export interface ParentDashboard {
  total_children: number;
  total_subjects: number;
  pending_payments: number;
  recent_reports: Array<{
    id: number;
    child_name: string;
    report_type: string;
    created_at: string;
  }>;
}

// Chat Types
export interface ChatMessage {
  id: number;
  sender_id: number;
  sender_name: string;
  sender_role: string;
  content: string;
  thread_id?: number;
  parent_message_id?: number;
  created_at: string;
  updated_at: string;
  is_edited?: boolean;
  message_type?: 'text' | 'file' | 'system';
}

export interface MessageThread {
  id: number;
  parent_message_id: number;
  thread_title: string;
  message_count: number;
  last_message_time: string;
  created_at: string;
}

export interface ChatRoom {
  id: number;
  name: string;
  description?: string;
  room_type: string;
  participant_count: number;
  created_at: string;
}

// Payment Types
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

// Application Types
export interface Application {
  id: number;
  first_name: string;
  last_name: string;
  full_name?: string;
  email: string;
  phone: string;
  telegram_id?: string;
  applicant_type: 'student' | 'teacher' | 'parent';
  status: 'pending' | 'approved' | 'rejected';
  tracking_token: string;
  grade?: string;
  subject?: string;
  experience?: string;
  motivation?: string;
  parent_first_name?: string;
  parent_last_name?: string;
  parent_full_name?: string;
  parent_email?: string;
  parent_phone?: string;
  parent_telegram_id?: string;
  created_at: string;
  processed_at?: string;
  notes?: string;
}

export interface CreateApplicationRequest {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  telegram_id?: string;
  applicant_type: 'student' | 'teacher' | 'parent';
  grade?: string;
  subject?: string;
  experience?: string;
  motivation: string;
  parent_first_name?: string;
  parent_last_name?: string;
  parent_email?: string;
  parent_phone?: string;
  parent_telegram_id?: string;
}

// Error Types
export interface ApiError {
  type: 'network' | 'auth' | 'validation' | 'server' | 'websocket';
  message: string;
  code?: string;
  details?: any;
}

// Retry Configuration
interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  backoffMultiplier: number;
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
};

class UnifiedAPIClient {
  private baseURL: string;
  private wsURL: string;
  private token: string | null = null;
  private refreshToken: string | null = null;
  private retryConfig: RetryConfig;
  private requestQueue: Map<string, Promise<any>> = new Map();

  constructor(
    baseURL: string = API_BASE_URL,
    wsURL: string = WS_BASE_URL,
    retryConfig: Partial<RetryConfig> = {}
  ) {
    this.baseURL = baseURL;
    this.wsURL = wsURL;
    this.retryConfig = { ...DEFAULT_RETRY_CONFIG, ...retryConfig };
    this.loadTokensFromStorage();
  }

  // Token Management
  private loadTokensFromStorage(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      // Пробуем загрузить из authToken (простой формат)
      this.token = localStorage.getItem('authToken');
      
      // Если не найдено, пробуем загрузить из secureStorage формата
      if (!this.token) {
        const secureItem = localStorage.getItem('bot_platform_auth_token');
        if (secureItem) {
          try {
            const parsed = JSON.parse(secureItem);
            this.token = parsed?.data || null;
            if (this.token) {
              console.log('[Token Management] Token loaded from secure storage format');
            }
          } catch (e) {
            console.warn('[Token Management] Failed to parse secure storage token:', e);
          }
        }
      }
      
      // Для refresh token
      this.refreshToken = localStorage.getItem('refreshToken');
      const secureRefresh = localStorage.getItem('bot_platform_refresh_token');
      if (!this.refreshToken && secureRefresh) {
        try {
          const parsed = JSON.parse(secureRefresh);
          this.refreshToken = parsed?.data || null;
        } catch (e) {
          console.warn('[Token Management] Failed to parse secure refresh token:', e);
        }
      }
      
      if (!this.token) {
        console.warn('[Token Management] No auth token found in any storage location');
      } else {
        console.log('[Token Management] Token loaded from storage');
      }
    } else {
      console.warn('[Token Management] localStorage not available');
    }
  }

  private saveTokensToStorage(token: string, refreshToken?: string): void {
    this.token = token;
    console.log('[Token Management] Saving token to storage');
    if (typeof window !== 'undefined' && window.localStorage) {
      // Сохраняем в простом формате
      localStorage.setItem('authToken', token);
      console.log('[Token Management] Token saved to localStorage');
      
      // Также сохраняем в secureStorage формат для совместимости с authService
      const tokenItem = {
        data: token,
        timestamp: Date.now()
      };
      localStorage.setItem('bot_platform_auth_token', JSON.stringify(tokenItem));
      console.log('[Token Management] Token saved to secure storage format');
      
      if (refreshToken) {
        this.refreshToken = refreshToken;
        localStorage.setItem('refreshToken', refreshToken);
        console.log('[Token Management] Refresh token saved to localStorage');
        
        // Также сохраняем refresh token в secureStorage формат
        const refreshItem = {
          data: refreshToken,
          timestamp: Date.now()
        };
        localStorage.setItem('bot_platform_refresh_token', JSON.stringify(refreshItem));
      }
    } else {
      console.warn('[Token Management] Cannot save token: localStorage not available');
    }
  }

  private clearTokens(): void {
    this.token = null;
    this.refreshToken = null;
    if (typeof window !== 'undefined' && window.localStorage) {
      // Очищаем простой формат
      localStorage.removeItem('authToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('userData');
      
      // Очищаем secureStorage формат
      localStorage.removeItem('bot_platform_auth_token');
      localStorage.removeItem('bot_platform_refresh_token');
      localStorage.removeItem('bot_platform_user_data');
      
      console.log('[Token Management] Tokens cleared from all storage locations');
    }
  }

  // Request Queue Management
  private getRequestKey(endpoint: string, options: RequestInit): string {
    return `${options.method || 'GET'}:${endpoint}:${JSON.stringify(options.body || '')}`;
  }

  // Retry Logic
  private async sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private calculateDelay(attempt: number): number {
    const delay = this.retryConfig.baseDelay * Math.pow(this.retryConfig.backoffMultiplier, attempt - 1);
    return Math.min(delay, this.retryConfig.maxDelay);
  }

  // Error Classification
  private classifyError(error: any, response?: Response): ApiError {
    if (!response) {
      return {
        type: 'network',
        message: 'Network error: Unable to connect to server',
        code: 'NETWORK_ERROR',
        details: error
      };
    }

    if (response.status === 401) {
      return {
        type: 'auth',
        message: 'Authentication required or token expired',
        code: 'AUTH_ERROR',
        details: { status: response.status }
      };
    }

    if (response.status >= 400 && response.status < 500) {
      return {
        type: 'validation',
        message: 'Invalid request data',
        code: 'VALIDATION_ERROR',
        details: { status: response.status }
      };
    }

    if (response.status >= 500) {
      return {
        type: 'server',
        message: 'Server error occurred',
        code: 'SERVER_ERROR',
        details: { status: response.status }
      };
    }

    return {
      type: 'server',
      message: 'Unknown error occurred',
      code: 'UNKNOWN_ERROR',
      details: { error, response }
    };
  }

  // Main Request Method with Enhanced Error Handling and Retry Logic
  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retryCount: number = 0
  ): Promise<ApiResponse<T>> {
    const requestKey = this.getRequestKey(endpoint, options);
    
    // Check if request is already in progress
    if (this.requestQueue.has(requestKey)) {
      return this.requestQueue.get(requestKey)!;
    }

    const requestPromise = this.executeRequestWithRetry<T>(endpoint, options);
    this.requestQueue.set(requestKey, requestPromise);

    try {
      const result = await requestPromise;
      return result;
    } finally {
      this.requestQueue.delete(requestKey);
    }
  }

  // Enhanced request execution with retry service
  private async executeRequestWithRetry<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      return await retryService.retryApiCall(
        () => this.executeRequest<T>(endpoint, options, 0),
        `API ${options.method || 'GET'} ${endpoint}`
      );
    } catch (error) {
      // Handle error with user-friendly messages
      const userFriendlyError = errorHandlingService.handleError(error, {
        operation: `API ${options.method || 'GET'} ${endpoint}`,
        component: 'UnifiedAPIClient',
      });

      return {
        success: false,
        error: userFriendlyError.message,
        timestamp: new Date().toISOString(),
      };
    }
  }

  private async executeRequest<T>(
    endpoint: string,
    options: RequestInit = {},
    retryCount: number = 0
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    
    // Load tokens from storage before each request
    this.loadTokensFromStorage();
    console.log('[API Request] Token loaded:', this.token ? 'YES' : 'NO');
    console.log('[API Request] Endpoint:', endpoint);
    
    // Check cache for GET requests
    const isGET = !options.method || options.method === 'GET';
    if (isGET && !retryCount) {
      const cachedData = cacheService.get<T>(endpoint);
      if (cachedData !== null) {
        return {
          success: true,
          data: cachedData,
          timestamp: new Date().toISOString(),
        };
      }
    }

    const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
    const headers: HeadersInit = {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Token ${this.token}`;
      console.log('[API Request] Authorization header added');
    } else {
      console.warn('[API Request] No token available for request');
    }

    // Start performance timer
    const timerId = performanceMonitoringService.startTimer(endpoint);

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include',
      });

      const duration = performanceMonitoringService.endTimer(timerId);

      const result = await safeJsonParse(response);

      if (!result.success) {
        return {
          success: false,
          error: result.error || 'Ошибка парсинга ответа сервера',
          timestamp: new Date().toISOString(),
        };
      }

      if (!response.ok) {
        const apiError = this.classifyError(null, response);
        
        // Handle authentication errors with token refresh
        if (apiError.type === 'auth' && this.refreshToken && retryCount === 0) {
          const refreshSuccess = await this.refreshAuthToken();
          if (refreshSuccess) {
            return this.request<T>(endpoint, options, retryCount + 1);
          }
        }

        // Retry logic for network and server errors
        if (
          (apiError.type === 'network' || apiError.type === 'server') &&
          retryCount < this.retryConfig.maxRetries
        ) {
          const delay = this.calculateDelay(retryCount + 1);
          await this.sleep(delay);
          return this.request<T>(endpoint, options, retryCount + 1);
        }

        return {
          success: false,
          error: result.data?.error || result.data?.detail || result.data?.message || apiError.message,
          timestamp: new Date().toISOString(),
        };
      }

      // Если backend возвращает данные в формате {success: true, data: {...}}
      // то используем result.data напрямую, иначе result.data.data
      const responseData = result.data?.data || result.data;
      
      const apiResponse: ApiResponse<T> = {
        success: true,
        data: responseData,
        message: result.data?.message,
        timestamp: new Date().toISOString(),
      };

      // Cache GET responses
      if (isGET && apiResponse.success && apiResponse.data) {
        cacheService.set(endpoint, apiResponse.data);
      }

      // Record successful API call
      performanceMonitoringService.recordAPICall(endpoint, duration, 'success');

      return apiResponse;
    } catch (error) {
      const duration = performanceMonitoringService.endTimer(timerId);
      const apiError = this.classifyError(error);

      // Record failed API call
      performanceMonitoringService.recordAPICall(
        endpoint,
        duration,
        apiError.type === 'network' ? 'error' : 'timeout'
      );
      
      // Retry logic for network errors
      if (apiError.type === 'network' && retryCount < this.retryConfig.maxRetries) {
        const delay = this.calculateDelay(retryCount + 1);
        await this.sleep(delay);
        return this.request<T>(endpoint, options, retryCount + 1);
      }

      return {
        success: false,
        error: apiError.message,
        timestamp: new Date().toISOString(),
      };
    }
  }

  // Token Refresh
  private async refreshAuthToken(): Promise<boolean> {
    if (!this.refreshToken) {
      return false;
    }

    try {
      const response = await fetch(`${this.baseURL}/auth/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.data?.token) {
          this.saveTokensToStorage(result.data.token, result.data.refresh_token);
          return true;
        }
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }

    // If refresh fails, clear tokens and redirect to login
    this.clearTokens();
    return false;
  }

  // Authentication Methods
  async login(credentials: LoginRequest): Promise<ApiResponse<LoginResponse>> {
    const response = await this.request<LoginResponse>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    if (response.success && response.data) {
      this.saveTokensToStorage(
        response.data.token,
        response.data.refresh_token
      );
      localStorage.setItem('userData', JSON.stringify(response.data.user));
    }

    return response;
  }

  async logout(): Promise<ApiResponse> {
    const response = await this.request('/auth/logout/', {
      method: 'POST',
    });

    this.clearTokens();
    return response;
  }

  async getProfile(): Promise<ApiResponse<{ user: User; profile?: any }>> {
    return this.request<{ user: User; profile?: any }>('/auth/profile/');
  }

  async updateProfile(profileData: Partial<User>): Promise<ApiResponse<User>> {
    return this.request<User>('/auth/profile/update/', {
      method: 'PATCH',
      body: JSON.stringify(profileData),
    });
  }

  async changePassword(passwordData: {
    old_password: string;
    new_password: string;
    new_password_confirm: string;
  }): Promise<ApiResponse> {
    return this.request('/auth/change-password/', {
      method: 'POST',
      body: JSON.stringify(passwordData),
    });
  }

  // Dashboard Methods
  async getStudentDashboard(): Promise<ApiResponse<StudentDashboard>> {
    return this.request<StudentDashboard>('/materials/student/');
  }

  async getTeacherDashboard(): Promise<ApiResponse<TeacherDashboard>> {
    return this.request<TeacherDashboard>('/materials/dashboard/teacher/');
  }

  async getParentDashboard(): Promise<ApiResponse<ParentDashboard>> {
    return this.request<ParentDashboard>('/materials/dashboard/parent/');
  }

  // Chat Methods
  async getGeneralChat(): Promise<ApiResponse<ChatRoom>> {
    return this.request<ChatRoom>('/chat/general/');
  }

  async getGeneralMessages(page: number = 1, pageSize: number = 50): Promise<ApiResponse<{
    results: ChatMessage[];
    count: number;
    next?: string;
    previous?: string;
  }>> {
    return this.request<{
      results: ChatMessage[];
      count: number;
      next?: string;
      previous?: string;
    }>(`/chat/general/messages/?page=${page}&page_size=${pageSize}`);
  }

  async sendMessage(data: {
    content: string;
    thread_id?: number;
    parent_message_id?: number;
  }): Promise<ApiResponse<ChatMessage>> {
    return this.request<ChatMessage>('/chat/general/messages/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Payment Methods
  async createPayment(data: CreatePaymentRequest): Promise<ApiResponse<Payment>> {
    return this.request<Payment>('/payments/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getPayment(id: string): Promise<ApiResponse<Payment>> {
    return this.request<Payment>(`/payments/${id}/`);
  }

  async getPayments(): Promise<ApiResponse<Payment[]>> {
    return this.request<Payment[]>('/payments/');
  }

  async getPaymentStatus(id: string): Promise<ApiResponse<Payment>> {
    return this.request<Payment>(`/payments/${id}/status/`);
  }

  // Application Methods
  async createApplication(data: CreateApplicationRequest): Promise<ApiResponse<Application>> {
    return this.request<Application>('/applications/submit/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getApplications(): Promise<ApiResponse<Application[]>> {
    return this.request<Application[]>('/applications/');
  }

  async getApplication(id: number): Promise<ApiResponse<Application>> {
    return this.request<Application>(`/applications/${id}/`);
  }

  async updateApplicationStatus(id: number, status: string, notes?: string): Promise<ApiResponse<Application>> {
    return this.request<Application>(`/applications/${id}/status/`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    });
  }

  // Health Check
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    return this.request<{ status: string }>('/health/');
  }

  // Utility Methods
  setToken(token: string): void {
    this.token = token;
    // Сохраняем в оба места для совместимости
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem('authToken', token);
      // Также в secureStorage формат для authService
      const item = {
        data: token,
        timestamp: Date.now()
      };
      localStorage.setItem('bot_platform_auth_token', JSON.stringify(item));
      console.log('[Token Management] Token saved to both storage locations');
    }
  }

  getToken(): string | null {
    // Всегда читаем из localStorage для актуальности
    this.loadTokensFromStorage();
    return this.token;
  }

  isAuthenticated(): boolean {
    return !!this.token;
  }

  // WebSocket Connection (placeholder for future implementation)
  connectWebSocket(): WebSocket | null {
    if (typeof WebSocket === 'undefined') {
      console.warn('WebSocket not supported in this environment');
      return null;
    }

    try {
      const ws = new WebSocket(`${this.wsURL}/chat/`);
      return ws;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      return null;
    }
  }
}

// Export singleton instance
export const unifiedAPI = new UnifiedAPIClient();

// Export class for custom instances
export { UnifiedAPIClient };
