import { unifiedAPI as apiClient, ApiResponse, User } from './unifiedClient';

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
    return apiClient.request<Tutor[]>('/auth/staff/?role=tutor');
  },

  /**
   * Get list of parents for selection
   */
  async getParents(): Promise<ApiResponse<Parent[]>> {
    return apiClient.request<Parent[]>('/auth/parents/');
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

    const url = `/admin/schedule/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    return apiClient.request(url);
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
    success: boolean;
    data: {
      total_users: number;
      total_students: number;
      total_teachers: number;
      total_tutors: number;
      total_parents: number;
      active_users: number;
      active_today: number;
    };
  }>> {
    return apiClient.request('/admin/stats/users/');
  },
};
