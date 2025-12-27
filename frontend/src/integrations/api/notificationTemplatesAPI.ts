/**
 * API Client for Notification Templates
 * Handles CRUD operations for notification templates with preview and validation
 */

import { unifiedAPI as apiClient, ApiResponse } from './unifiedClient';

/**
 * Notification template type choices from backend
 */
export type NotificationType =
  | 'assignment_new'
  | 'assignment_due'
  | 'assignment_graded'
  | 'material_new'
  | 'message_new'
  | 'report_ready'
  | 'payment_success'
  | 'payment_failed'
  | 'system'
  | 'reminder'
  | 'student_created'
  | 'subject_assigned'
  | 'material_published'
  | 'homework_submitted'
  | 'payment_processed'
  | 'invoice_sent'
  | 'invoice_paid'
  | 'invoice_overdue'
  | 'invoice_viewed';

/**
 * Notification Template data structure
 */
export interface NotificationTemplate {
  id: number;
  name: string;
  description: string;
  type: NotificationType;
  type_display: string;
  title_template: string;
  message_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Request to create or update a template
 */
export interface CreateUpdateTemplateRequest {
  name: string;
  description?: string;
  type: NotificationType;
  title_template: string;
  message_template: string;
  is_active?: boolean;
}

/**
 * Preview request with context variables
 */
export interface PreviewRequest {
  context: {
    user_name?: string;
    user_email?: string;
    subject?: string;
    date?: string;
    title?: string;
    grade?: string;
    feedback?: string;
  };
}

/**
 * Preview response with rendered templates
 */
export interface PreviewResponse {
  rendered_title: string;
  rendered_message: string;
}

/**
 * Validation response
 */
export interface ValidationResponse {
  is_valid: boolean;
  errors?: string[];
}

/**
 * Paginated list response
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Notification Templates API Client
 */
export const notificationTemplatesAPI = {
  /**
   * Get list of notification templates with pagination and filters
   */
  async getTemplates(
    page: number = 1,
    pageSize: number = 20,
    filters?: {
      type?: NotificationType;
      is_active?: boolean;
      search?: string;
    }
  ): Promise<ApiResponse<PaginatedResponse<NotificationTemplate>>> {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    if (filters?.type) {
      params.append('type', filters.type);
    }
    if (filters?.is_active !== undefined) {
      params.append('is_active', filters.is_active.toString());
    }
    if (filters?.search) {
      params.append('search', filters.search);
    }

    return apiClient.request<PaginatedResponse<NotificationTemplate>>(
      `/notifications/templates/?${params.toString()}`,
      { method: 'GET' }
    );
  },

  /**
   * Get a single notification template by ID
   */
  async getTemplate(id: number): Promise<ApiResponse<NotificationTemplate>> {
    return apiClient.request<NotificationTemplate>(`/notifications/templates/${id}/`, {
      method: 'GET',
    });
  },

  /**
   * Create a new notification template
   */
  async createTemplate(
    data: CreateUpdateTemplateRequest
  ): Promise<ApiResponse<NotificationTemplate>> {
    return apiClient.request<NotificationTemplate>(`/notifications/templates/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update an existing notification template
   */
  async updateTemplate(
    id: number,
    data: CreateUpdateTemplateRequest
  ): Promise<ApiResponse<NotificationTemplate>> {
    return apiClient.request<NotificationTemplate>(`/notifications/templates/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a notification template
   */
  async deleteTemplate(id: number): Promise<ApiResponse<void>> {
    return apiClient.request<void>(`/notifications/templates/${id}/`, {
      method: 'DELETE',
    });
  },

  /**
   * Preview a template with sample context
   */
  async previewTemplate(
    id: number,
    context: PreviewRequest['context']
  ): Promise<ApiResponse<PreviewResponse>> {
    return apiClient.request<PreviewResponse>(
      `/notifications/templates/${id}/preview/`,
      {
        method: 'POST',
        body: JSON.stringify({ context }),
      }
    );
  },

  /**
   * Validate template syntax and variables
   */
  async validateTemplate(
    titleTemplate: string,
    messageTemplate: string
  ): Promise<ApiResponse<ValidationResponse>> {
    return apiClient.request<ValidationResponse>(
      `/notifications/templates/validate/`,
      {
        method: 'POST',
        body: JSON.stringify({
          title_template: titleTemplate,
          message_template: messageTemplate,
        }),
      }
    );
  },

  /**
   * Clone an existing template
   */
  async cloneTemplate(id: number): Promise<ApiResponse<NotificationTemplate>> {
    return apiClient.request<NotificationTemplate>(
      `/notifications/templates/${id}/clone/`,
      {
        method: 'POST',
      }
    );
  },
};
