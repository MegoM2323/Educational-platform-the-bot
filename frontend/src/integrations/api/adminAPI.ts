import { unifiedAPI as apiClient, ApiResponse, User } from './unifiedClient';

// Generic paginated response interface
interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Types for User updates
export interface UserUpdateData {
  email?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  is_active?: boolean;
  profile_data?: StudentProfileData | TeacherProfileData | TutorProfileData | ParentProfileData;
}

/**
 * ВАЖНО: Приватные поля профилей
 *
 * StudentProfileData:
 * - goal, tutor_id, parent_id - ПРИВАТНЫЕ (студент не видит, видят teacher/tutor/admin)
 *
 * TeacherProfileData:
 * - bio, experience_years - ПРИВАТНЫЕ (преподаватель не видит, видит только admin)
 *
 * TutorProfileData:
 * - bio, experience_years - ПРИВАТНЫЕ (тьютор не видит, видит только admin)
 *
 * Backend автоматически фильтрует эти поля в зависимости от прав.
 * На фронтенде проверяем наличие через optional chaining.
 */

// Types for Profile updates
export interface StudentProfileData {
  grade?: string;
  goal?: string; // ПРИВАТНОЕ: студент не видит
  tutor_id?: number | null; // ПРИВАТНОЕ: студент не видит
  parent_id?: number | null; // ПРИВАТНОЕ: студент не видит
}

export interface TeacherProfileData {
  experience_years?: number; // ПРИВАТНОЕ: только для admin
  bio?: string; // ПРИВАТНОЕ: только для admin
}

export interface TutorProfileData {
  specialization?: string;
  experience_years?: number; // ПРИВАТНОЕ: только для admin
  bio?: string; // ПРИВАТНОЕ: только для admin
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface ParentProfileData {
  // Пока нет специфичных полей для родителя
}

// Types for User creation
export interface UserCreateData {
  role: 'student' | 'teacher' | 'tutor' | 'parent';
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  password?: string;

  // Для student
  grade?: string;
  goal?: string;
  tutor_id?: number | null;
  parent_id?: number | null;

  // Для teacher/tutor
  experience_years?: number;
  bio?: string;
  specialization?: string;
}

export interface CreateUserResponse {
  user: User;
  credentials: {
    login: string;
    password: string;
  };
}

export interface ResetPasswordResponse {
  new_password: string;
}

// Types for selection lists
export interface Tutor {
  id: number;
  user: User;
  specialization?: string;
  experience_years?: number;
}

export interface Parent {
  id: number;
  user: User;
  children_count: number;
}

/**
 * Admin API Client
 * Provides CRUD operations for user management
 */
export const adminAPI = {
  /**
   * Update User basic information
   */
  async updateUser(userId: number, data: UserUpdateData): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/users/${userId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update Student Profile
   */
  async updateStudentProfile(studentId: number, data: StudentProfileData): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/students/${studentId}/profile/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update Teacher Profile
   */
  async updateTeacherProfile(teacherId: number, data: TeacherProfileData): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/teachers/${teacherId}/profile/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update Tutor Profile
   */
  async updateTutorProfile(tutorId: number, data: TutorProfileData): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/tutors/${tutorId}/profile/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update Parent Profile
   */
  async updateParentProfile(parentId: number, data: ParentProfileData): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/parents/${parentId}/profile/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Reset user password
   * Returns new auto-generated password
   */
  async resetPassword(userId: number): Promise<ApiResponse<ResetPasswordResponse>> {
    return apiClient.request<ResetPasswordResponse>(`/auth/users/${userId}/reset-password/`, {
      method: 'POST',
    });
  },

  /**
   * Delete or deactivate user
   * @param permanent - true for hard delete, false for soft delete (deactivation)
   */
  async deleteUser(userId: number, permanent: boolean = false): Promise<ApiResponse<void>> {
    return apiClient.request<void>(`/auth/users/${userId}/delete/`, {
      method: 'DELETE',
      body: JSON.stringify({ permanent }),
    });
  },

  /**
   * Create new user with role-specific profile
   */
  async createUser(data: UserCreateData): Promise<ApiResponse<CreateUserResponse>> {
    return apiClient.request<CreateUserResponse>('/auth/users/create/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get list of tutors for selection
   */
  async getTutors(): Promise<ApiResponse<Tutor[]>> {
    const response = await apiClient.request<PaginatedResponse<Tutor>>('/auth/staff/?role=tutor');
    // Extract results array from paginated response
    if (response.data?.results) {
      return { ...response, data: response.data.results };
    }
    // Handle case where response is already an array
    if (Array.isArray(response.data)) {
      return response as ApiResponse<Tutor[]>;
    }
    return { ...response, data: [] };
  },

  /**
   * Get list of parents for selection
   */
  async getParents(): Promise<ApiResponse<Parent[]>> {
    const response = await apiClient.request<PaginatedResponse<Parent> | Parent[]>('/auth/parents/');
    // Extract results array from paginated response
    if (response.data && !Array.isArray(response.data) && 'results' in response.data) {
      return { ...response, data: response.data.results };
    }
    // Handle case where response is already an array
    if (Array.isArray(response.data)) {
      return response as ApiResponse<Parent[]>;
    }
    return { ...response, data: [] };
  },

  /**
   * Get students list with filtering and pagination
   */
  async getStudents(filters?: {
    grade?: string;
    tutor_id?: number | null;
    search?: string;
    is_active?: boolean | null;
    ordering?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<{
    count: number;
    next: string | null;
    previous: string | null;
    results: Array<{
      id: number;
      user: User;
      grade?: string;
      tutor_id?: number | null;
      parent_id?: number | null;
    }>;
  }>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.grade) params.append('grade', filters.grade);
      if (filters.tutor_id) params.append('tutor_id', filters.tutor_id.toString());
      if (filters.search) params.append('search', filters.search);
      if (filters.is_active !== null && filters.is_active !== undefined) {
        params.append('is_active', filters.is_active.toString());
      }
      if (filters.ordering) params.append('ordering', filters.ordering);
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.page_size) params.append('page_size', filters.page_size.toString());
    }
    const queryString = params.toString();
    const url = `/auth/students/${queryString ? '?' + queryString : ''}`;
    return apiClient.request<{
      count: number;
      next: string | null;
      previous: string | null;
      results: Array<{
        id: number;
        user: User;
        grade?: string;
        tutor_id?: number | null;
        parent_id?: number | null;
      }>;
    }>(url);
  },

  /**
   * Create new student
   * Specialized endpoint for student creation
   */
  async createStudent(data: {
    email: string;
    first_name: string;
    last_name: string;
    grade: string;
    phone?: string;
    goal?: string;
    tutor_id?: number | null;
    parent_id?: number | null;
    password?: string;
  }): Promise<ApiResponse<CreateUserResponse>> {
    return apiClient.request<CreateUserResponse>('/auth/students/create/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Edit teacher via admin endpoint
   * Updates both user and profile data
   */
  async editTeacher(
    teacherId: number,
    data: {
      email?: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      is_active?: boolean;
      experience_years?: number;
      bio?: string;
      subject_ids?: number[];
    }
  ): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/teachers/${teacherId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Edit tutor via admin endpoint
   * Updates both user and profile data
   */
  async editTutor(
    tutorId: number,
    data: {
      email?: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      is_active?: boolean;
      specialization?: string;
      experience_years?: number;
      bio?: string;
    }
  ): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/tutors/${tutorId}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  /**
   * Reactivate a user profile
   * Sets is_active=True for the user
   */
  async reactivateUser(userId: number): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/auth/users/${userId}/reactivate/`, {
      method: 'POST',
    });
  },

  /**
   * Create new parent
   * Specialized endpoint for parent creation
   */
  async createParent(data: {
    email: string;
    first_name: string;
    last_name: string;
    phone?: string;
    password?: string;
  }): Promise<ApiResponse<CreateUserResponse>> {
    return apiClient.request<CreateUserResponse>('/auth/parents/create/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Get list of parents for selection
   */
  async listParents(): Promise<ApiResponse<{
    results: Array<{
      id: number;
      user: User;
      children_count?: number;
    }>;
  }>> {
    return apiClient.request<{
      results: Array<{
        id: number;
        user: User;
        children_count?: number;
      }>;
    }>('/auth/parents/');
  },

  /**
   * Assign parent to multiple students
   */
  async assignParentToStudents(parentId: number, studentIds: number[]): Promise<ApiResponse<{
    success: boolean;
    parent_id: number;
    assigned_students: number[];
    message: string;
  }>> {
    return apiClient.request<{
      success: boolean;
      parent_id: number;
      assigned_students: number[];
      message: string;
    }>('/auth/assign-parent/', {
      method: 'POST',
      body: JSON.stringify({
        parent_id: parentId,
        student_ids: studentIds,
      }),
    });
  },

  /**
   * Get admin schedule with filters
   */
  async getSchedule(params?: {
    teacher_id?: string;
    subject_id?: string;
    student_id?: string;
    date_from?: string;
    date_to?: string;
    status?: string;
  }): Promise<ApiResponse<{
    success: boolean;
    count: number;
    lessons: Array<{
      id: string;
      date: string;
      start_time: string;
      end_time: string;
      teacher: number;
      teacher_name: string;
      student: number;
      student_name: string;
      subject: number;
      subject_name: string;
      status: string;
      description?: string;
      telemost_link?: string;
      created_at: string;
      updated_at: string;
    }>;
  }>> {
    const queryParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams.append(key, value);
        }
      });
    }

    const url = `/admin/schedule/lessons/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    const response = await apiClient.request<{
      success: boolean;
      count: number;
      next: string | null;
      previous: string | null;
      results: Array<{
        id: string;
        date: string;
        start_time: string;
        end_time: string;
        teacher: number;
        teacher_name: string;
        student: number;
        student_name: string;
        subject: number;
        subject_name: string;
        status: string;
        description?: string;
        telemost_link?: string;
        created_at: string;
        updated_at: string;
      }>;
    }>(url);

    // Transform backend response: results -> lessons
    if (!response.data) {
      return {
        ...response,
        data: {
          success: false,
          count: 0,
          lessons: []
        }
      };
    }

    return {
      ...response,
      data: {
        success: response.data.success ?? false,
        count: response.data.count ?? 0,
        lessons: response.data.results ?? []
      }
    };
  },

  /**
   * Get schedule statistics
   */
  async getScheduleStats(): Promise<ApiResponse<{
    success: boolean;
    stats: {
      total_lessons: number;
      today_lessons: number;
      week_ahead_lessons: number;
      pending_lessons: number;
      completed_lessons: number;
      cancelled_lessons: number;
    };
  }>> {
    return apiClient.request('/admin/schedule/stats/');
  },

  /**
   * Get schedule filter options
   */
  async getScheduleFilters(): Promise<ApiResponse<{
    success: boolean;
    teachers: Array<{ id: number; name: string }>;
    subjects: Array<{ id: number; name: string }>;
    students: Array<{ id: number; name: string }>;
  }>> {
    return apiClient.request('/admin/schedule/filters/');
  },

  /**
   * Chat Management - Admin API
   * Read-only access to all chat rooms and messages
   */

  /**
   * Get all chat rooms with participants and last message
   */
  async getChatRooms(): Promise<ApiResponse<{
    success: boolean;
    data: {
      rooms: Array<{
        id: number;
        name: string;
        description?: string;
        type: 'forum_subject' | 'forum_tutor' | 'direct' | 'group' | 'general';
        participants_count: number;
        participants: Array<{
          id: number;
          full_name: string;
          role: string;
        }>;
        subject?: {
          id: number;
          name: string;
        };
        last_message?: {
          id: number;
          content: string;
          sender: {
            id: number;
            full_name: string;
            role: string;
          };
          created_at: string;
        };
        unread_count: number;
        is_active: boolean;
        created_at: string;
        updated_at: string;
      }>;
      count: number;
    };
  }>> {
    return apiClient.request('/chat/admin/rooms/');
  },

  /**
   * Get detailed information about a specific chat room
   */
  async getChatRoomDetail(roomId: number): Promise<ApiResponse<{
    success: boolean;
    data: {
      room: {
        id: number;
        name: string;
        description?: string;
        type: string;
        participants_count: number;
        participants: Array<{
          id: number;
          full_name: string;
          role: string;
        }>;
        subject?: {
          id: number;
          name: string;
        };
        is_active: boolean;
        created_at: string;
        updated_at: string;
      };
      participants_count: number;
      messages_count: number;
    };
  }>> {
    return apiClient.request(`/chat/admin/rooms/${roomId}/`);
  },

  /**
   * Get messages for a specific chat room
   */
  async getChatMessages(
    roomId: number,
    params?: {
      limit?: number;
      offset?: number;
    }
  ): Promise<ApiResponse<{
    success: boolean;
    data: {
      room_id: number;
      messages: Array<{
        id: number;
        content: string;
        sender: {
          id: number;
          full_name: string;
          role: string;
        };
        sender_name: string;
        sender_role: string;
        sender_avatar?: string;
        message_type?: string;
        file_url?: string;
        image_url?: string;
        is_edited: boolean;
        is_read: boolean;
        created_at: string;
        updated_at: string;
        reply_to?: number;
        replies_count: number;
      }>;
      count: number;
      limit: number;
      offset: number;
    };
  }>> {
    const queryParams = new URLSearchParams();
    if (params?.limit !== undefined) {
      queryParams.append('limit', params.limit.toString());
    }
    if (params?.offset !== undefined) {
      queryParams.append('offset', params.offset.toString());
    }

    const url = `/chat/admin/rooms/${roomId}/messages/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return apiClient.request(url);
  },

  /**
   * Get chat statistics
   */
  async getChatStats(): Promise<ApiResponse<{
    success: boolean;
    data: {
      total_rooms: number;
      active_rooms: number;
      total_messages: number;
      forum_subject_rooms: number;
      direct_rooms: number;
      group_rooms: number;
    };
  }>> {
    return apiClient.request('/chat/admin/stats/');
  },

  /**
   * Get user statistics for admin dashboard
   */
  async getUserStats(): Promise<ApiResponse<{
    total_users: number;
    total_students: number;
    total_teachers: number;
    total_tutors: number;
    total_parents: number;
    active_users?: number;
    active_today: number;
  }>> {
    return apiClient.request('/admin/stats/users/');
  },

  /**
   * Broadcasts Management - Admin API
   */

  /**
   * Get list of broadcasts with pagination and filters
   */
  async getBroadcasts(params?: {
    status?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<{
    success: boolean;
    count: number;
    next: string | null;
    previous: string | null;
    results: Array<{
      id: number;
      target_group: string;
      message: string;
      status: 'draft' | 'sent' | 'failed';
      created_by: {
        id: number;
        full_name: string;
      };
      created_at: string;
      sent_at?: string;
      total_recipients: number;
      successful_sends: number;
      failed_sends: number;
      metadata?: {
        subject_id?: number;
        subject_name?: string;
        tutor_id?: number;
        tutor_name?: string;
      };
    }>;
  }>> {
    const queryParams = new URLSearchParams();
    if (params) {
      if (params.status) queryParams.append('status', params.status);
      if (params.date_from) queryParams.append('date_from', params.date_from);
      if (params.date_to) queryParams.append('date_to', params.date_to);
      if (params.page) queryParams.append('page', params.page.toString());
      if (params.page_size) queryParams.append('page_size', params.page_size.toString());
    }

    const url = `/admin/broadcasts/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return apiClient.request(url);
  },

  /**
   * Get broadcast details
   */
  async getBroadcast(broadcastId: number): Promise<ApiResponse<{
    success: boolean;
    data: {
      id: number;
      target_group: string;
      message: string;
      status: 'draft' | 'sent' | 'failed';
      created_by: {
        id: number;
        full_name: string;
      };
      created_at: string;
      sent_at?: string;
      total_recipients: number;
      successful_sends: number;
      failed_sends: number;
      metadata?: {
        subject_id?: number;
        subject_name?: string;
        tutor_id?: number;
        tutor_name?: string;
      };
    };
  }>> {
    return apiClient.request(`/admin/broadcasts/${broadcastId}/`);
  },

  /**
   * Get broadcast recipients with delivery status
   */
  async getBroadcastRecipients(broadcastId: number): Promise<ApiResponse<{
    success: boolean;
    recipients: Array<{
      user_id: number;
      user_email: string;
      user_name: string;
      status: 'pending' | 'sent' | 'failed';
      error_message?: string;
      sent_at?: string;
    }>;
  }>> {
    return apiClient.request(`/admin/broadcasts/${broadcastId}/recipients/`);
  },

  /**
   * Create and send broadcast
   */
  async createBroadcast(data: {
    target_group: string;
    message: string;
    subject_id?: number;
    tutor_id?: number;
    user_ids?: number[];
  }): Promise<ApiResponse<{
    success: boolean;
    broadcast_id: number;
    message: string;
    recipients_count: number;
  }>> {
    return apiClient.request('/admin/broadcasts/create/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Preview broadcast recipients count
   */
  async previewBroadcast(data: {
    target_group: string;
    subject_id?: number;
    tutor_id?: number;
    user_ids?: number[];
  }): Promise<ApiResponse<{
    success: boolean;
    recipients_count: number;
    recipients_preview: Array<{
      id: number;
      full_name: string;
      email: string;
      role: string;
    }>;
  }>> {
    return apiClient.request('/admin/broadcasts/preview/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Audit Logs Management - Admin API
   * NOTE: Audit log endpoints not implemented in backend yet.
   * TODO: Implement audit logging system in future sprint
   * Current placeholder methods below - will be enabled after backend implementation
   */

  /**
   * Get audit logs with optional filters, sorting, and pagination
   * NOT IMPLEMENTED - Backend support needed
   */
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async getAuditLogs(params?: {
    user_id?: number;
    action?: string;
    resource?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    ordering?: string;
    page?: number;
    page_size?: number;
    format?: string; // 'csv' for CSV export
  }): Promise<ApiResponse<{
    count: number;
    next: string | null;
    previous: string | null;
    results: Array<{
      id: number;
      timestamp: string;
      user: {
        id: number;
        email: string;
        full_name: string;
      };
      action: 'create' | 'read' | 'update' | 'delete' | 'export' | 'login' | 'logout';
      resource: string;
      status: 'success' | 'failed';
      ip_address: string;
      user_agent?: string;
      duration_ms?: number;
      old_values?: Record<string, any>;
      new_values?: Record<string, any>;
      details?: string;
    }>;
  }>> {
    return Promise.reject(new Error('Audit logs endpoint not implemented in backend'));
  },

  /**
   * Get single audit log entry with full details
   * NOT IMPLEMENTED - Backend support needed
   */
  async getAuditLogDetail(logId: number): Promise<ApiResponse<{
    id: number;
    timestamp: string;
    user: {
      id: number;
      email: string;
      full_name: string;
    };
    action: string;
    resource: string;
    status: string;
    ip_address: string;
    user_agent?: string;
    duration_ms?: number;
    old_values?: Record<string, any>;
    new_values?: Record<string, any>;
    details?: string;
  }>> {
    return Promise.reject(new Error(`Audit logs endpoint not implemented in backend (logId: ${logId})`));
  },

  /**
   * Get audit log statistics
   * NOT IMPLEMENTED - Backend support needed
   */
  async getAuditLogStats(): Promise<ApiResponse<{
    success: boolean;
    data: {
      total_logs: number;
      today_logs: number;
      failed_actions: number;
      unique_users: number;
      most_active_action: string;
      most_active_resource: string;
    };
  }>> {
    return Promise.reject(new Error('Audit logs endpoint not implemented in backend'));
  },

  /**
   * Get list of all users with filtering and pagination
   * Maps to backend /auth/users/ (accessible via /api/admin/)
   */
  async getUsers(filters?: {
    search?: string;
    role?: string;
    status?: 'active' | 'inactive' | 'suspended' | 'locked';
    joined_date_from?: string;
    joined_date_to?: string;
    ordering?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<{
    count: number;
    next: string | null;
    previous: string | null;
    results: User[];
  }>> {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.search) params.append('search', filters.search);
      if (filters.role) params.append('role', filters.role);
      if (filters.status) params.append('status', filters.status);
      if (filters.joined_date_from) params.append('joined_date_from', filters.joined_date_from);
      if (filters.joined_date_to) params.append('joined_date_to', filters.joined_date_to);
      if (filters.ordering) params.append('ordering', filters.ordering);
      if (filters.page) params.append('page', filters.page.toString());
      if (filters.page_size) params.append('page_size', filters.page_size.toString());
    }
    const queryString = params.toString();
    const url = `/admin/users/${queryString ? '?' + queryString : ''}`;
    return apiClient.request<{
      count: number;
      next: string | null;
      previous: string | null;
      results: User[];
    }>(url);
  },

  /**
   * Get single user details
   * NOTE: Backend provides /auth/users/{id}/ for updates (PATCH) but not for read (GET)
   * This endpoint is expected by frontend but not fully implemented in backend
   */
  async getUserDetail(userId: number): Promise<ApiResponse<User>> {
    return apiClient.request<User>(`/admin/users/${userId}/`);
  },

  /**
   * Bulk activate users
   */
  async bulkActivateUsers(userIds: number[]): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_ids: number[];
    details: string;
  }>> {
    return apiClient.request(`/admin/bulk-operations/bulk_activate/`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds }),
    });
  },

  /**
   * Bulk deactivate users
   */
  async bulkDeactivateUsers(userIds: number[]): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_ids: number[];
    details: string;
  }>> {
    return apiClient.request(`/admin/bulk-operations/bulk_deactivate/`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds }),
    });
  },

  /**
   * Bulk suspend users
   */
  async bulkSuspendUsers(userIds: number[]): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_ids: number[];
    details: string;
  }>> {
    return apiClient.request(`/admin/bulk-operations/bulk_suspend/`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds }),
    });
  },

  /**
   * Bulk reset password for users
   */
  async bulkResetPasswordUsers(userIds: number[]): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_ids: number[];
    details: string;
  }>> {
    return apiClient.request(`/admin/bulk-operations/bulk_reset_password/`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds }),
    });
  },

  /**
   * Bulk delete users
   */
  async bulkDeleteUsers(userIds: number[]): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_ids: number[];
    details: string;
  }>> {
    return apiClient.request(`/admin/bulk-operations/bulk_delete/`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds }),
    });
  },

  /**
   * Bulk assign role to users
   */
  async bulkAssignRoleUsers(userIds: number[], role: string): Promise<ApiResponse<{
    success_count: number;
    failed_count: number;
    failed_ids: number[];
    details: string;
  }>> {
    return apiClient.request(`/admin/bulk-operations/bulk_assign_role/`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds, new_role: role }),
    });
  },

  /**
   * Create a new lesson (admin can create lessons on behalf of teachers)
   */
  async createLesson(data: {
    teacher_id: number;
    student_id: number;
    subject_id: number;
    date: string;
    start_time: string;
    end_time: string;
    description?: string;
    telemost_link?: string;
  }): Promise<ApiResponse<{
    id: string;
    date: string;
    start_time: string;
    end_time: string;
    teacher: number;
    teacher_name: string;
    student: number;
    student_name: string;
    subject: number;
    subject_name: string;
    status: string;
    description?: string;
    telemost_link?: string;
    created_at: string;
    updated_at: string;
  }>> {
    return apiClient.request('/admin/schedule/lessons/create/', {
      method: 'POST',
      body: JSON.stringify({
        student: data.student_id,
        subject: data.subject_id,
        teacher: data.teacher_id,
        date: data.date,
        start_time: data.start_time,
        end_time: data.end_time,
        description: data.description || '',
        telemost_link: data.telemost_link || '',
      }),
    });
  },
};
