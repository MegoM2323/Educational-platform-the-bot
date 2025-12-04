import { describe, it, expect, vi, beforeEach } from 'vitest';
import { schedulingAPI } from '../schedulingAPI';
import { unifiedAPI } from '../unifiedClient';

// Mock unifiedAPI at file level
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('schedulingAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createLesson', () => {
    it('should call POST /scheduling/lessons/ with payload', async () => {
      const payload = {
        student: '550e8400-e29b-41d4-a716-446655440000',
        subject: '660e8400-e29b-41d4-a716-446655440000',
        date: '2025-12-15',
        start_time: '09:00:00',
        end_time: '10:00:00',
        description: 'Algebra basics',
        telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
      };

      const mockResponse = {
        data: {
          id: '770e8400-e29b-41d4-a716-446655440000',
          ...payload,
          status: 'pending',
          created_at: '2025-11-29T10:00:00Z',
          updated_at: '2025-11-29T10:00:00Z',
          teacher_name: 'John Doe',
          student_name: 'Jane Smith',
          subject_name: 'Mathematics',
        },
        error: null,
      };

      vi.mocked(unifiedAPI.post).mockResolvedValue(mockResponse);

      const result = await schedulingAPI.createLesson(payload);

      expect(unifiedAPI.post).toHaveBeenCalledWith('/scheduling/lessons/', payload);
      expect(result.id).toBe('770e8400-e29b-41d4-a716-446655440000');
      expect(result.status).toBe('pending');
      expect(result.teacher_name).toBe('John Doe');
    });

    it('should throw error if response has error', async () => {
      const payload = {
        student: 'invalid-id',
        subject: 'invalid-id',
        date: '2025-12-15',
        start_time: '09:00:00',
        end_time: '10:00:00',
      };

      vi.mocked(unifiedAPI.post).mockResolvedValue({
        error: 'Invalid student or subject',
        data: null,
      });

      await expect(schedulingAPI.createLesson(payload)).rejects.toThrow(
        'Invalid student or subject'
      );
    });
  });

  describe('getLessons', () => {
    it('should fetch lessons without filters', async () => {
      const mockLessons = [
        {
          id: '770e8400-e29b-41d4-a716-446655440000',
          teacher: '550e8400-e29b-41d4-a716-446655440001',
          student: '550e8400-e29b-41d4-a716-446655440000',
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-15',
          start_time: '09:00:00',
          end_time: '10:00:00',
          description: 'Algebra basics',
          telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
          status: 'confirmed',
          created_at: '2025-11-29T10:00:00Z',
          updated_at: '2025-11-29T10:00:00Z',
          teacher_name: 'John Doe',
          student_name: 'Jane Smith',
          subject_name: 'Mathematics',
          is_upcoming: true,
        },
      ];

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: mockLessons,
        error: null,
      });

      const result = await schedulingAPI.getLessons();

      expect(unifiedAPI.get).toHaveBeenCalledWith('/scheduling/lessons/', { params: undefined });
      expect(result).toHaveLength(1);
      expect(result[0].subject_name).toBe('Mathematics');
    });

    it('should fetch lessons with filters', async () => {
      const mockLessons = [
        {
          id: '770e8400-e29b-41d4-a716-446655440000',
          teacher: '550e8400-e29b-41d4-a716-446655440001',
          student: '550e8400-e29b-41d4-a716-446655440000',
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-15',
          start_time: '09:00:00',
          end_time: '10:00:00',
          description: 'Algebra basics',
          telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
          status: 'confirmed',
          created_at: '2025-11-29T10:00:00Z',
          updated_at: '2025-11-29T10:00:00Z',
          teacher_name: 'John Doe',
          student_name: 'Jane Smith',
          subject_name: 'Mathematics',
          is_upcoming: true,
        },
      ];

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: mockLessons,
        error: null,
      });

      const filters = {
        subject: '660e8400-e29b-41d4-a716-446655440000',
        date_from: '2025-12-01',
      };

      const result = await schedulingAPI.getLessons(filters);

      expect(unifiedAPI.get).toHaveBeenCalledWith('/scheduling/lessons/', { params: filters });
      expect(result).toHaveLength(1);
    });

    it('should return empty array when no lessons exist', async () => {
      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: [],
        error: null,
      });

      const result = await schedulingAPI.getLessons();

      expect(result).toEqual([]);
    });

    it('should throw error if API call fails', async () => {
      vi.mocked(unifiedAPI.get).mockResolvedValue({
        error: 'Failed to fetch lessons',
        data: null,
      });

      await expect(schedulingAPI.getLessons()).rejects.toThrow('Failed to fetch lessons');
    });
  });

  describe('getLesson', () => {
    it('should fetch a single lesson by ID', async () => {
      const lessonId = '770e8400-e29b-41d4-a716-446655440000';
      const mockLesson = {
        id: lessonId,
        teacher: '550e8400-e29b-41d4-a716-446655440001',
        student: '550e8400-e29b-41d4-a716-446655440000',
        subject: '660e8400-e29b-41d4-a716-446655440000',
        date: '2025-12-15',
        start_time: '09:00:00',
        end_time: '10:00:00',
        description: 'Algebra basics',
        telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
        status: 'confirmed',
        created_at: '2025-11-29T10:00:00Z',
        updated_at: '2025-11-29T10:00:00Z',
        teacher_name: 'John Doe',
        student_name: 'Jane Smith',
        subject_name: 'Mathematics',
      };

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: mockLesson,
        error: null,
      });

      const result = await schedulingAPI.getLesson(lessonId);

      expect(unifiedAPI.get).toHaveBeenCalledWith(`/scheduling/lessons/${lessonId}/`);
      expect(result.id).toBe(lessonId);
      expect(result.teacher_name).toBe('John Doe');
    });

    it('should throw error if lesson not found', async () => {
      vi.mocked(unifiedAPI.get).mockResolvedValue({
        error: 'Lesson not found',
        data: null,
      });

      await expect(schedulingAPI.getLesson('invalid-id')).rejects.toThrow('Lesson not found');
    });
  });

  describe('updateLesson', () => {
    it('should call PATCH /scheduling/lessons/{id}/ with payload', async () => {
      const lessonId = '770e8400-e29b-41d4-a716-446655440000';
      const payload = {
        description: 'Updated description',
        telemost_link: 'https://telemost.yandex.ru/j/newlink',
      };

      const mockResponse = {
        data: {
          id: lessonId,
          teacher: '550e8400-e29b-41d4-a716-446655440001',
          student: '550e8400-e29b-41d4-a716-446655440000',
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-15',
          start_time: '09:00:00',
          end_time: '10:00:00',
          description: 'Updated description',
          telemost_link: 'https://telemost.yandex.ru/j/newlink',
          status: 'confirmed',
          created_at: '2025-11-29T10:00:00Z',
          updated_at: '2025-11-29T11:00:00Z',
          teacher_name: 'John Doe',
          student_name: 'Jane Smith',
          subject_name: 'Mathematics',
        },
        error: null,
      };

      vi.mocked(unifiedAPI.patch).mockResolvedValue(mockResponse);

      const result = await schedulingAPI.updateLesson(lessonId, payload);

      expect(unifiedAPI.patch).toHaveBeenCalledWith(
        `/scheduling/lessons/${lessonId}/`,
        payload
      );
      expect(result.description).toBe('Updated description');
      expect(result.telemost_link).toBe('https://telemost.yandex.ru/j/newlink');
    });

    it('should throw error if update fails', async () => {
      const lessonId = '770e8400-e29b-41d4-a716-446655440000';

      vi.mocked(unifiedAPI.patch).mockResolvedValue({
        error: 'Cannot update lesson within 2 hours of start',
        data: null,
      });

      await expect(
        schedulingAPI.updateLesson(lessonId, { description: 'New' })
      ).rejects.toThrow('Cannot update lesson within 2 hours of start');
    });
  });

  describe('deleteLesson', () => {
    it('should call DELETE /scheduling/lessons/{id}/', async () => {
      const lessonId = '770e8400-e29b-41d4-a716-446655440000';

      vi.mocked(unifiedAPI.delete).mockResolvedValue({
        data: undefined,
        error: null,
      });

      await schedulingAPI.deleteLesson(lessonId);

      expect(unifiedAPI.delete).toHaveBeenCalledWith(`/scheduling/lessons/${lessonId}/`);
    });

    it('should throw error if deletion fails', async () => {
      const lessonId = '770e8400-e29b-41d4-a716-446655440000';

      vi.mocked(unifiedAPI.delete).mockResolvedValue({
        error: 'Cannot delete lesson within 2 hours of start',
        data: null,
      });

      await expect(schedulingAPI.deleteLesson(lessonId)).rejects.toThrow(
        'Cannot delete lesson within 2 hours of start'
      );
    });
  });

  describe('getMySchedule', () => {
    it('should fetch current user schedule', async () => {
      const mockLessons = [
        {
          id: '770e8400-e29b-41d4-a716-446655440000',
          teacher: '550e8400-e29b-41d4-a716-446655440001',
          student: '550e8400-e29b-41d4-a716-446655440000',
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-15',
          start_time: '09:00:00',
          end_time: '10:00:00',
          description: 'Algebra basics',
          telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
          status: 'confirmed',
          created_at: '2025-11-29T10:00:00Z',
          updated_at: '2025-11-29T10:00:00Z',
          teacher_name: 'John Doe',
          student_name: 'Jane Smith',
          subject_name: 'Mathematics',
          is_upcoming: true,
        },
      ];

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: mockLessons,
        error: null,
      });

      const result = await schedulingAPI.getMySchedule();

      expect(unifiedAPI.get).toHaveBeenCalledWith('/scheduling/lessons/my_schedule/', {
        params: undefined,
      });
      expect(result).toHaveLength(1);
      expect(result[0].is_upcoming).toBe(true);
    });

    it('should fetch schedule with date filters', async () => {
      const mockLessons = [];

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: mockLessons,
        error: null,
      });

      const filters = {
        date_from: '2025-12-01',
        date_to: '2025-12-31',
      };

      const result = await schedulingAPI.getMySchedule(filters);

      expect(unifiedAPI.get).toHaveBeenCalledWith('/scheduling/lessons/my_schedule/', {
        params: filters,
      });
    });
  });

  describe('getStudentSchedule', () => {
    it('should fetch student schedule by student ID', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';
      const mockLessons = [
        {
          id: '770e8400-e29b-41d4-a716-446655440000',
          teacher: '550e8400-e29b-41d4-a716-446655440001',
          student: studentId,
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-15',
          start_time: '09:00:00',
          end_time: '10:00:00',
          description: 'Algebra basics',
          telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
          status: 'confirmed',
          created_at: '2025-11-29T10:00:00Z',
          updated_at: '2025-11-29T10:00:00Z',
          teacher_name: 'John Doe',
          student_name: 'Jane Smith',
          subject_name: 'Mathematics',
        },
      ];

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: mockLessons,
        error: null,
      });

      const result = await schedulingAPI.getStudentSchedule(studentId);

      expect(unifiedAPI.get).toHaveBeenCalledWith(
        `/materials/dashboard/tutor/students/${studentId}/schedule/`,
        { params: undefined }
      );
      expect(result).toHaveLength(1);
      expect(result[0].student).toBe(studentId);
    });

    it('should fetch student schedule with filters', async () => {
      const studentId = '550e8400-e29b-41d4-a716-446655440000';

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: [],
        error: null,
      });

      const filters = {
        date_from: '2025-12-01',
        status: 'confirmed',
      };

      const result = await schedulingAPI.getStudentSchedule(studentId, filters);

      expect(unifiedAPI.get).toHaveBeenCalledWith(
        `/materials/dashboard/tutor/students/${studentId}/schedule/`,
        { params: filters }
      );
    });

    it('should throw error if fetch fails', async () => {
      vi.mocked(unifiedAPI.get).mockResolvedValue({
        error: 'Access denied',
        data: null,
      });

      await expect(
        schedulingAPI.getStudentSchedule('550e8400-e29b-41d4-a716-446655440000')
      ).rejects.toThrow('Access denied');
    });
  });

  describe('getUpcomingLessons', () => {
    it('should fetch upcoming lessons with default limit', async () => {
      const mockLessons = [
        {
          id: '770e8400-e29b-41d4-a716-446655440000',
          teacher: '550e8400-e29b-41d4-a716-446655440001',
          student: '550e8400-e29b-41d4-a716-446655440000',
          subject: '660e8400-e29b-41d4-a716-446655440000',
          date: '2025-12-15',
          start_time: '09:00:00',
          end_time: '10:00:00',
          description: 'Algebra basics',
          telemost_link: 'https://telemost.yandex.ru/j/abcd1234',
          status: 'confirmed',
          created_at: '2025-11-29T10:00:00Z',
          updated_at: '2025-11-29T10:00:00Z',
          teacher_name: 'John Doe',
          student_name: 'Jane Smith',
          subject_name: 'Mathematics',
        },
      ];

      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: mockLessons,
        error: null,
      });

      const result = await schedulingAPI.getUpcomingLessons();

      expect(unifiedAPI.get).toHaveBeenCalledWith('/scheduling/lessons/upcoming/', {
        params: { limit: 10 },
      });
      expect(result).toHaveLength(1);
    });

    it('should fetch upcoming lessons with custom limit', async () => {
      vi.mocked(unifiedAPI.get).mockResolvedValue({
        data: [],
        error: null,
      });

      await schedulingAPI.getUpcomingLessons(5);

      expect(unifiedAPI.get).toHaveBeenCalledWith('/scheduling/lessons/upcoming/', {
        params: { limit: 5 },
      });
    });
  });
});
