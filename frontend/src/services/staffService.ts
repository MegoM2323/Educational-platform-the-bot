import { unifiedAPI as apiClient, ApiResponse, User } from '@/integrations/api/unifiedClient';

export interface Subject {
  id: number;
  name: string;
  description?: string;
  color?: string;
  is_active: boolean;
  assigned_at?: string;
}

export interface StaffListItem {
  id: number;
  user: User;
  subject?: string;
  specialization?: string;
  experience_years?: number;
  bio?: string;
  subjects?: Subject[]; // Массив назначенных предметов (для преподавателей)
}

export interface CreateStaffPayload {
  role: 'teacher' | 'tutor';
  email: string;
  first_name: string;
  last_name: string;
  subject?: string; // for teacher
  specialization?: string; // for tutor
  experience_years?: number;
  bio?: string;
}

export interface CreateStaffResponse {
  user: User;
  credentials: { login: string; password: string };
}

export const staffService = {
  async list(role: 'teacher' | 'tutor'): Promise<StaffListItem[]> {
    // Добавляем timestamp для предотвращения кеширования
    const timestamp = Date.now();
    const res = await apiClient.request<{ results: StaffListItem[] } | StaffListItem[]>(`/auth/staff/?role=${role}&_=${timestamp}`, { method: 'GET' });
    if (!res.success) {
      console.error('Error loading staff list:', res.error);
      throw new Error(res.error || 'Не удалось получить список');
    }
    // unifiedClient уже извлекает results из ответа, поэтому res.data может быть либо массивом, либо объектом с results
    let results: StaffListItem[] = [];
    if (Array.isArray(res.data)) {
      // Если unifiedClient уже извлек results, res.data будет массивом
      results = res.data;
    } else if (res.data && typeof res.data === 'object' && 'results' in res.data) {
      // Если unifiedClient не извлек results (редкий случай), извлекаем вручную
      results = (res.data as any).results || [];
    }
    console.log(`[staffService] Loaded ${results.length} ${role}s`, { dataType: typeof res.data, isArray: Array.isArray(res.data) });
    return results;
  },

  async create(payload: CreateStaffPayload): Promise<CreateStaffResponse> {
    const res = await apiClient.request<CreateStaffResponse>('/auth/staff/create/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!res.success) throw new Error(res.error || 'Не удалось создать пользователя');
    return res.data as any;
  },

  async getAllSubjects(): Promise<Subject[]> {
    const res = await apiClient.request<Subject[]>('/materials/subjects/all/', {
      method: 'GET',
    });
    if (!res.success) {
      throw new Error(res.error || 'Не удалось загрузить предметы');
    }
    return res.data as Subject[];
  },

  async updateTeacherSubjects(teacherId: number, subjectIds: number[]): Promise<void> {
    const res = await apiClient.request(`/staff/teachers/${teacherId}/subjects/`, {
      method: 'PATCH',
      body: JSON.stringify({ subject_ids: subjectIds }),
    });
    if (!res.success) {
      throw new Error(res.error || 'Не удалось обновить предметы');
    }
  },
};


