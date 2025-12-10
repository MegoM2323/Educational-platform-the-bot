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

/**
 * Frontend Environment Configuration
 *
 * URL Detection Precedence:
 * 1. Environment variable (VITE_DJANGO_API_URL for API, VITE_WEBSOCKET_URL for WebSocket)
 * 2. Auto-detection from window.location (production-friendly)
 * 3. Fallback to localhost (SSR/build-time only)
 *
 * Environment Setup:
 * - Development: Set VITE_DJANGO_API_URL=http://localhost:8003/api in .env.local
 * - Production: Auto-detects from window.location (https://the-bot.ru → https://the-bot.ru/api)
 * - Override WebSocket: Set VITE_WEBSOCKET_URL in .env (optional, auto-detected if not set)
 */

function getApiUrl(): string {
  // Priority 1: Check environment variable (set in .env.local or .env)
  const envUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DJANGO_API_URL);
  if (envUrl && envUrl !== 'undefined') {
    let url = envUrl;
    // Normalize: ensure ends with /api
    if (!url.endsWith('/api')) {
      url = url.replace(/\/$/, '') + '/api';
    }
    logger.info('[Config] Using API URL from VITE_DJANGO_API_URL env var:', url);
    return url;
  }

  // Priority 2: Auto-detect from current location (production-friendly)
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
    const url = `${protocol}//${window.location.host}/api`;
    logger.info('[Config] Using auto-detected API URL from window.location:', url);
    return url;
  }

  // Fallback 3: SSR or build-time only (should not be used in browser)
  logger.info('[Config] Using fallback API URL (SSR/build-time)');
  return 'http://localhost:8003/api';
}

function getWebSocketUrl(): string {
  // Priority 1: Check environment variable (set in .env.local or .env)
  const envUrl = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_WEBSOCKET_URL);
  if (envUrl && envUrl !== 'undefined') {
    const url = envUrl.replace(/\/$/, '');
    logger.info('[Config] Using WebSocket URL from VITE_WEBSOCKET_URL env var:', url);
    return url;
  }

  // Priority 2: Auto-detect from current location (production-friendly)
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;
    logger.info('[Config] Using auto-detected WebSocket URL from window.location:', url);
    return url;
  }

  // Fallback 3: SSR or build-time only (should not be used in browser)
  logger.info('[Config] Using fallback WebSocket URL (SSR/build-time)');
  return 'ws://localhost:8003/ws';
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
  is_active?: boolean;
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
  student_info: {
    id: number;
    name: string;
    username: string;
    role: string;
    avatar?: string;
  };
  subjects: Array<{
    id: number;
    name: string;
    description: string;
    color: string;
    teacher: {
      id: number;
      name: string;
      username: string;
    };
    enrolled_at: string;
    enrollment_id: number;
  }>;
  materials_by_subject: {
    [subjectName: string]: {
      subject_info: {
        id: number;
        name: string;
        color?: string;
      };
      materials: Array<{
        id: number;
        title: string;
        description?: string;
        type?: string;
        difficulty_level?: string;
        subject: {
          id: number;
          name: string;
          color?: string;
        };
        author: {
          id: number;
          name: string;
          role: string;
        };
        file_url?: string;
        video_url?: string;
        tags?: string[];
        created_at: string;
        published_at?: string;
        status?: string;
        progress_percentage?: number;
        progress?: {
          is_completed: boolean;
          progress_percentage: number;
          time_spent: number;
          started_at?: string;
          completed_at?: string;
          last_accessed?: string;
        };
      }>;
    };
  };
  stats: {
    total_materials: number;
    completed_materials: number;
    in_progress_materials: number;
    not_started_materials: number;
    completion_percentage: number;
    average_progress: number;
    total_time_spent: number;
    subject_statistics: {
      [subjectName: string]: {
        total: number;
        completed: number;
        in_progress: number;
        not_started: number;
      };
    };
  };
  progress_statistics: {
    total_materials: number;
    completed_materials: number;
    in_progress_materials: number;
    not_started_materials: number;
    completion_percentage: number;
    average_progress: number;
    total_time_spent: number;
    overall_percentage?: number;
    completed_tasks?: number;
    total_tasks?: number;
    streak_days?: number;
    accuracy_percentage?: number;
    subject_statistics: {
      [subjectName: string]: {
        total: number;
        completed: number;
        in_progress: number;
        not_started: number;
      };
    };
  };
  recent_activity: Array<{
    id: number;
    type: string;
    title: string;
    deadline: string;
    status: 'pending' | 'completed' | 'overdue';
    description?: string;
    timestamp?: string;
    data?: {
      material_id?: number;
      subject_id?: number;
      progress_percentage?: number;
      time_spent?: number;
    };
  }>;
  profile?: any;
}

export interface TeacherDashboard {
  teacher_info?: {
    id: number;
    name: string;
    role: string;
    avatar?: string | null;
  };
  students: Array<{
    id: number;
    username: string;
    name: string;
    first_name: string;
    last_name: string;
    email: string;
    avatar?: string | null;
    subjects: Array<{
      id: number;
      name: string;
      color?: string;
      custom_subject_name?: string;
    }>;
    profile?: {
      grade: string;
      goal: string;
      progress_percentage: number;
      streak_days: number;
      total_points: number;
      accuracy_percentage: number;
    };
    assigned_materials_count: number;
    completed_materials_count: number;
    completion_percentage: number;
  }>;
  materials: Array<{
    id: number;
    title: string;
    description: string;
    type: string;
    status: string;
    subject: {
      id: number;
      name: string;
      color?: string;
    };
    assigned_count: number;
    completed_count: number;
    completion_percentage: number;
  }>;
  progress_overview?: any;
  reports?: any[];
  general_chat?: any;
  profile?: any;
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
  private refreshTokenValue: string | null = null;
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
    this.refreshTokenValue = tokens.refreshToken;

    logger.debug('[TokenClient] Load tokens from storage:', {
      hasAccessToken: !!tokens.accessToken,
      hasRefreshToken: !!tokens.refreshToken,
      accessTokenLength: tokens.accessToken?.length || 0
    });
  }

  private saveTokensToStorage(token: string, refreshToken?: string): void {
    this.token = token;
    this.refreshTokenValue = refreshToken || this.refreshTokenValue || undefined;

    // Use unified tokenStorage service
    tokenStorage.saveTokens(token, refreshToken);
    logger.debug('[TokenClient] Tokens saved to unified storage');
  }

  private clearTokens(): void {
    this.token = null;
    this.refreshTokenValue = null;

    // Use unified tokenStorage service
    tokenStorage.clearTokens();

    logger.info('[TokenClient] Tokens cleared');
    // Note: Redirection to login page is handled by ProtectedRoute component
    // when it detects no authentication, not by this method
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
      !endpoint.includes('/tutor/students/') &&
      !endpoint.includes('/profile/'); // Don't cache any profile endpoints
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
      logger.debug('[API Request] Authorization header added', {
        endpoint,
        tokenLength: this.token.length,
        hasAuthHeader: true
      });
    } else {
      logger.warn('[API Request] No token available for request', {
        endpoint,
        method: options.method || 'GET'
      });
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
          if (this.refreshTokenValue) {
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
      // 4. Пагинированный объект: {count, results, next, previous}
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
        } else if ('count' in result.data && 'results' in result.data) {
          // ВАЖНО: Для пагинированных endpoints используем весь объект, не только results!
          // Фронтенд ожидает {count, results, next, previous}, а не только массив results
          responseData = result.data;
          if (isStaffEndpoint) {
            logger.debug('[unifiedClient] Using full paginated response with count:', result.data.count);
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
        !endpoint.includes('/tutor/students/') &&
        !endpoint.includes('/profile/'); // Don't cache profile endpoints
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
    if (!this.refreshTokenValue) {
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
        body: JSON.stringify({ refresh_token: this.refreshTokenValue }),
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
    // Ensure token is loaded before making the request
    this.loadTokensFromStorage();

    logger.debug('[UnifiedAPI.getProfile] Fetching profile with token:', {
      hasToken: !!this.token,
      tokenLength: this.token?.length || 0
    });

    // Get user data from localStorage to determine role
    let userRole: string | null = null;
    try {
      const userDataStr = localStorage.getItem('userData');
      if (userDataStr) {
        const userData = JSON.parse(userDataStr);
        userRole = userData.role;
        logger.debug('[UnifiedAPI.getProfile] User role from localStorage:', userRole);
      }
    } catch (error) {
      logger.warn('[UnifiedAPI.getProfile] Failed to get user role from localStorage:', error);
    }

    // If no role found in localStorage, try to get it from token
    if (!userRole) {
      logger.warn('[UnifiedAPI.getProfile] No user role found in localStorage');
      // Fallback: try common endpoint, backend will handle it
      // Since we don't have role, we'll try the most generic approach
      // by attempting to fetch from student endpoint (most common)
      return this.request<{ user: User; profile?: any }>('/profile/student/').catch(async (error) => {
        logger.warn('[UnifiedAPI.getProfile] Failed with /profile/student/, falling back to /profile/teacher/');
        return this.request<{ user: User; profile?: any }>('/profile/teacher/');
      });
    }

    // Route to correct endpoint based on role
    const endpoint = this.getProfileEndpointForRole(userRole);
    logger.debug('[UnifiedAPI.getProfile] Using endpoint:', endpoint);

    return this.request<{ user: User; profile?: any }>(endpoint);
  }

  private getProfileEndpointForRole(role: string): string {
    switch (role) {
      case 'student':
        return '/profile/student/';
      case 'teacher':
        return '/profile/teacher/';
      case 'tutor':
        return '/profile/tutor/';
      case 'parent':
        return '/profile/parent/';
      case 'admin':
        // Admin may not have a profile endpoint, fallback to student
        return '/profile/student/';
      default:
        logger.warn(`[UnifiedAPI.getProfileEndpointForRole] Unknown role: ${role}, defaulting to student`);
        return '/profile/student/';
    }
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
    return this.request<TeacherDashboard>('/teacher/');
  }

  async getParentDashboard(): Promise<ApiResponse<ParentDashboard>> {
    return this.request<ParentDashboard>('/materials/parent/');
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

  // HTTP Method Wrappers (for use by API client classes like schedulingAPI)
  async get<T = any>(endpoint: string, options?: RequestInit & { params?: Record<string, any> }): Promise<ApiResponse<T>> {
    const params = options?.params;
    let url = endpoint;

    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      const queryString = searchParams.toString();
      if (queryString) {
        url = `${endpoint}${endpoint.includes('?') ? '&' : '?'}${queryString}`;
      }
    }

    return this.request<T>(url, {
      ...options,
      method: 'GET',
    });
  }

  async post<T = any>(endpoint: string, data?: any, options?: RequestInit): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: typeof data === 'string' ? data : JSON.stringify(data),
    });
  }

  async patch<T = any>(endpoint: string, data?: any, options?: RequestInit): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: typeof data === 'string' ? data : JSON.stringify(data),
    });
  }

  async put<T = any>(endpoint: string, data?: any, options?: RequestInit): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: typeof data === 'string' ? data : JSON.stringify(data),
    });
  }

  async delete<T = any>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'DELETE',
    });
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
