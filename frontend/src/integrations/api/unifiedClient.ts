// Unified API Client for THE_BOT_platform
// Consolidates all API communication between frontend and backend
import { safeJsonParse } from '../../utils/jsonUtils';
import { errorHandlingService } from '../../services/errorHandlingService';
import { retryService } from '../../services/retryService';
import { errorLoggingService } from '../../services/errorLoggingService';
import { performanceMonitoringService } from '../../services/performanceMonitoringService';
import { cacheService } from '../../services/cacheService';
import { tokenStorage } from '../../services/tokenStorage';
import { normalizeResponse, validateResponseData, extractErrorMessage, isResponseError } from './responseNormalizer';
import { logger } from '../../utils/logger';
import type { ParentDashboard } from './dashboard';

// Environment configuration - получаем URL с автоопределением
function getApiUrl(): string {
  // Сначала проверяем переменную окружения
  const envUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DJANGO_API_URL);
  if (envUrl && envUrl !== 'undefined') {
    let url = envUrl;
    // Нормализуем: гарантируем окончание на /api
    if (!url.endsWith('/api')) {
      url = url.replace(/\/$/, '') + '/api';
    }
    logger.info('[Config] Using API URL from env:', url);
    return url;
  }

  // Если нет переменной окружения, автоматически определяем по текущему хосту
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const url = `${protocol}//${window.location.host}/api`;
    logger.info('[Config] Using auto-detected API URL:', url);
    return url;
  }

  // Fallback для SSR
  logger.info('[Config] Using fallback API URL');
  return 'http://localhost:8000/api';
}

function getWebSocketUrl(): string {
  // Сначала проверяем переменную окружения
  const envUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_WEBSOCKET_URL);
  if (envUrl && envUrl !== 'undefined') {
    const url = envUrl.replace(/\/$/, '');
    logger.info('[Config] Using WebSocket URL from env:', url);
    return url;
  }

  // Если нет переменной окружения, автоматически определяем по текущему хосту
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;
    logger.info('[Config] Using auto-detected WebSocket URL:', url);
    return url;
  }

  // Fallback для SSR
  logger.info('[Config] Using fallback WebSocket URL');
  return 'ws://localhost:8000/ws';
}

const API_BASE_URL = getApiUrl();
const WS_BASE_URL = getWebSocketUrl();

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
  private isRefreshing = false; // Prevent concurrent refresh attempts
  private refreshQueue: Array<() => void> = []; // Queue requests during refresh

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

  // Token Management - Use unified tokenStorage service
  private loadTokensFromStorage(): void {
    const tokens = tokenStorage.getTokens();
    this.token = tokens.accessToken;
    this.refreshToken = tokens.refreshToken;

    if (this.token) {
      logger.debug('[TokenClient] Tokens loaded from unified storage');
    }
  }

  private saveTokensToStorage(token: string, refreshToken?: string): void {
    this.token = token;
    this.refreshToken = refreshToken || this.refreshToken || undefined;

    // Use unified tokenStorage service
    tokenStorage.saveTokens(token, refreshToken);
    logger.debug('[TokenClient] Tokens saved to unified storage');
  }

  private clearTokens(): void {
    this.token = null;
    this.refreshToken = null;

    // Use unified tokenStorage service
    tokenStorage.clearTokens();

    // Redirect to login if in browser
    if (typeof window !== 'undefined') {
      logger.info('[TokenClient] Tokens cleared, redirecting to login');
      // Redirect to login page
      setTimeout(() => {
        window.location.href = '/auth';
      }, 100);
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
  async request<T>(
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
    
    // Check cache for GET requests (но не для списка пользователей, staff и студентов тьютора, чтобы всегда получать актуальные данные)
    const isGET = !options.method || options.method === 'GET';
    const shouldUseCache = isGET && !retryCount &&
      !endpoint.includes('/accounts/users/') &&
      !endpoint.includes('/auth/staff/') &&
      !endpoint.includes('/tutor/students/');
    if (shouldUseCache) {
      const cachedData = cacheService.get<T>(endpoint);
      if (cachedData !== null) {
        logger.debug('[API Request] Using cached data for:', endpoint);
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
      logger.debug('[API Request] Authorization header added');
    } else {
      logger.warn('[API Request] No token available for request');
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
      
      // Определяем, является ли это staff endpoint
      const isStaffEndpoint = endpoint.includes('/auth/staff/');
      
      // Логируем для отладки списка пользователей и staff
      if (endpoint.includes('/accounts/users/') || isStaffEndpoint) {
        logger.debug('[unifiedClient] API response:', {
          endpoint,
          ok: response.ok,
          status: response.status,
          statusText: response.statusText,
          parseSuccess: result.success,
          dataType: typeof result.data,
          isArray: Array.isArray(result.data),
          dataLength: Array.isArray(result.data) ? result.data.length : 'N/A',
          dataKeys: result.data && typeof result.data === 'object' && !Array.isArray(result.data) ? Object.keys(result.data) : 'N/A'
        });
      }

      if (!result.success) {
        return {
          success: false,
          error: result.error || 'Ошибка парсинга ответа сервера',
          timestamp: new Date().toISOString(),
        };
      }

      if (!response.ok) {
        const apiError = this.classifyError(null, response);

        // Handle authentication errors with token refresh (prevent infinite loops)
        if (apiError.type === 'auth' && retryCount === 0) {
          // If refresh is in progress, queue this request
          if (this.isRefreshing) {
            return new Promise((resolve) => {
              this.refreshQueue.push(() => {
                this.request<T>(endpoint, options, retryCount + 1).then(resolve);
              });
            });
          }

          // If we have a refresh token, attempt refresh
          if (this.refreshToken) {
            this.isRefreshing = true;
            try {
              const refreshSuccess = await this.refreshAuthToken();
              if (refreshSuccess) {
                // Process queued requests
                this.refreshQueue.forEach((callback) => callback());
                this.refreshQueue = [];
                return this.request<T>(endpoint, options, retryCount + 1);
              }
            } finally {
              this.isRefreshing = false;
              this.refreshQueue = [];
            }
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

        // Обрабатываем ошибки валидации Django REST Framework
        let errorMessage = apiError.message;
        if (result.data) {
          // Django REST Framework возвращает ошибки валидации в формате:
          // { field: ["error message"], ... } или { detail: "error message" } или { error: "error message" }
          if (result.data.detail) {
            errorMessage = result.data.detail;
          } else if (result.data.error) {
            errorMessage = result.data.error;
          } else if (result.data.message) {
            errorMessage = result.data.message;
          } else if (typeof result.data === 'object') {
            // Если это объект с ошибками валидации полей, формируем сообщение
            const fieldErrors = Object.entries(result.data)
              .map(([field, errors]: [string, any]) => {
                if (Array.isArray(errors)) {
                  return `${field}: ${errors.join(', ')}`;
                }
                return `${field}: ${errors}`;
              })
              .join('; ');
            if (fieldErrors) {
              errorMessage = fieldErrors;
            }
          }
        }

        return {
          success: false,
          error: errorMessage,
          timestamp: new Date().toISOString(),
        };
      }

      // Обрабатываем ответ от backend
      // Django REST Framework может возвращать:
      // 1. Массив напрямую: [item1, item2, ...] - это самый частый случай для list endpoints
      // 2. Объект: {field: value, ...}
      // 3. Объект с вложенными данными: {data: [...], message: "..."}
      let responseData: any;
      
      // result.data уже содержит распарсенный JSON ответ от сервера
      // Если сервер вернул массив напрямую, result.data будет массивом
      if (Array.isArray(result.data)) {
        // Если это массив, используем его напрямую (самый частый случай для list endpoints)
        responseData = result.data;
        if (endpoint.includes('/accounts/users/') || isStaffEndpoint) {
          logger.debug('[unifiedClient] Data is array, length:', responseData.length);
        }
      } else if (result.data && typeof result.data === 'object') {
        // Если это объект, проверяем наличие вложенных данных
        // Но для list endpoints Django обычно возвращает массив напрямую
        if (endpoint.includes('/accounts/users/') || isStaffEndpoint) {
          logger.debug('[unifiedClient] Data is object, keys:', Object.keys(result.data));
        }
        if (result.data.data !== undefined) {
          // Если есть вложенное поле data, используем его
          responseData = result.data.data;
          if (isStaffEndpoint) {
            logger.debug('[unifiedClient] Using result.data.data');
          }
        } else if (Array.isArray(result.data.results)) {
          // Если есть поле results (пагинация), используем его
          responseData = result.data.results;
          if (isStaffEndpoint) {
            logger.debug('[unifiedClient] Using result.data.results, length:', responseData.length);
          }
        } else {
          // Иначе используем весь объект
          responseData = result.data;
          if (isStaffEndpoint) {
            logger.debug('[unifiedClient] Using result.data as is');
          }
        }
      } else {
        // Если это не массив и не объект, используем как есть
        responseData = result.data;
        if (endpoint.includes('/accounts/users/') || isStaffEndpoint) {
          logger.warn('[unifiedClient] Data is not array or object:', typeof result.data);
        }
      }
      
      const apiResponse: ApiResponse<T> = {
        success: true,
        data: responseData,
        message: result.data?.message,
        timestamp: new Date().toISOString(),
      };
      
      if (endpoint.includes('/accounts/users/') || isStaffEndpoint) {
        logger.debug('[unifiedClient] Final response:', {
          success: apiResponse.success,
          dataType: typeof apiResponse.data,
          isArray: Array.isArray(apiResponse.data),
          dataLength: Array.isArray(apiResponse.data) ? apiResponse.data.length : 'N/A'
        });
      }

      // Cache GET responses (но не для списка пользователей, staff и студентов тьютора, чтобы всегда получать актуальные данные)
      const shouldCache = isGET && apiResponse.success && apiResponse.data && 
        !endpoint.includes('/accounts/users/') && 
        !endpoint.includes('/auth/staff/') &&
        !endpoint.includes('/tutor/students/');
      if (shouldCache) {
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

  // Token Refresh with proper error handling
  private async refreshAuthToken(): Promise<boolean> {
    if (!this.refreshToken) {
      logger.warn('[TokenClient] No refresh token available');
      this.clearTokens();
      return false;
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    try {
      logger.info('[TokenClient] Attempting token refresh');
      const response = await fetch(`${this.baseURL}/auth/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
        signal: controller.signal,
      });

      clearTimeout(timeout);

      // Check HTTP status
      if (!response.ok) {
        logger.error('[TokenClient] Token refresh failed with status:', response.status);
        this.clearTokens();
        return false;
      }

      // Parse response
      const result = await response.json();

      // Validate response structure (using new response normalizer logic)
      if (result.success && result.data?.token) {
        logger.info('[TokenClient] Token refresh successful');
        this.saveTokensToStorage(result.data.token, result.data.refresh_token);
        return true;
      } else {
        logger.error('[TokenClient] Invalid token refresh response:', result);
        this.clearTokens();
        return false;
      }
    } catch (error) {
      clearTimeout(timeout);

      if (error instanceof Error && error.name === 'AbortError') {
        logger.error('[TokenClient] Token refresh timeout');
      } else {
        logger.error('[TokenClient] Token refresh error:', error);
      }

      // Clear tokens and redirect to login on any error
      this.clearTokens();
      return false;
    }
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

  async refreshToken(): Promise<ApiResponse<LoginResponse>> {
    logger.info('[unifiedAPIClient.refreshToken] Refreshing token');
    const response = await this.request<LoginResponse>('/auth/refresh/', {
      method: 'POST',
    });

    if (response.success && response.data) {
      logger.info('[unifiedAPIClient.refreshToken] Token refreshed successfully');
      this.saveTokensToStorage(
        response.data.token,
        response.data.refresh_token
      );
      localStorage.setItem('userData', JSON.stringify(response.data.user));
    } else {
      logger.error('[unifiedAPIClient.refreshToken] Failed to refresh token:', response.error);
    }

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
    return this.request<TeacherDashboard>('/dashboard/teacher/');
  }

  async getParentDashboard(): Promise<ApiResponse<ParentDashboard>> {
    return this.request<ParentDashboard>('/dashboard/parent/');
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
      logger.debug('[Token Management] Token saved to both storage locations');
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
      logger.warn('WebSocket not supported in this environment');
      return null;
    }

    try {
      const ws = new WebSocket(`${this.wsURL}/chat/`);
      return ws;
    } catch (error) {
      logger.error('Failed to create WebSocket connection:', error);
      return null;
    }
  }
}

// Export singleton instance
export const unifiedAPI = new UnifiedAPIClient();

// Export class for custom instances
export { UnifiedAPIClient };
