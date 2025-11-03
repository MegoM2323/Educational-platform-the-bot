import { unifiedAPI as apiClient, ApiResponse, User } from '@/integrations/api/unifiedClient';

export interface StaffListItem {
  id: number;
  user: User;
  subject?: string;
  specialization?: string;
  experience_years?: number;
  bio?: string;
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
    const res = await apiClient.request<{ results: StaffListItem[] }>(`/auth/staff/?role=${role}&_=${Date.now()}`, { method: 'GET' });
    if (!res.success) throw new Error(res.error || 'Не удалось получить список');
    return (res.data as any)?.results || [];
  },

  async create(payload: CreateStaffPayload): Promise<CreateStaffResponse> {
    const res = await apiClient.request<CreateStaffResponse>('/auth/staff/create/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (!res.success) throw new Error(res.error || 'Не удалось создать пользователя');
    return res.data as any;
  },
};


