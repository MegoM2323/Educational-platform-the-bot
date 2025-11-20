import { describe, it, expect, vi, beforeEach } from 'vitest';
import { tutorAPI } from '../tutor';
import { unifiedAPI } from '../unifiedClient';

// Mock unifiedAPI
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
    getToken: vi.fn(() => 'mock-token'),
  },
}));

describe('tutorAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listStudents', () => {
    it('should fetch students list', async () => {
      const mockStudents = [
        {
          id: 1,
          user_id: 10,
          full_name: 'Alice Smith',
          first_name: 'Alice',
          last_name: 'Smith',
          grade: '10A',
          goal: 'University preparation',
          parent_name: 'John Smith',
          subjects: []
        },
        {
          id: 2,
          user_id: 11,
          full_name: 'Bob Johnson',
          first_name: 'Bob',
          last_name: 'Johnson',
          grade: '9B',
          subjects: []
        }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockStudents,
        error: null
      });

      const result = await tutorAPI.listStudents();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/tutor/students/');
      expect(result).toHaveLength(2);
      expect(result[0].full_name).toBe('Alice Smith');
      expect(result[1].grade).toBe('9B');
    });

    it('should handle nested data structure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {
          data: [
            { id: 1, full_name: 'Test Student' }
          ]
        },
        error: null
      });

      const result = await tutorAPI.listStudents();

      expect(result).toHaveLength(1);
      expect(result[0].full_name).toBe('Test Student');
    });

    it('should handle results array structure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {
          results: [
            { id: 1, full_name: 'Test Student' }
          ]
        },
        error: null
      });

      const result = await tutorAPI.listStudents();

      expect(result).toHaveLength(1);
    });

    it('should return empty array when no students', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: null,
        error: null
      });

      const result = await tutorAPI.listStudents();

      expect(result).toEqual([]);
    });

    it('should throw error when token is missing', async () => {
      vi.mocked(unifiedAPI.getToken).mockReturnValue(null);

      await expect(tutorAPI.listStudents()).rejects.toThrow('Authentication required');
    });

    it('should throw error on request failure', async () => {
      // Ensure token is available for this test
      vi.mocked(unifiedAPI.getToken).mockReturnValue('mock-token');

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Network error'
      });

      await expect(tutorAPI.listStudents()).rejects.toThrow('Network error');
    });
  });

  describe('createStudent', () => {
    it('should create student with all data', async () => {
      const mockResponse = {
        student: {
          id: 1,
          full_name: 'New Student',
          grade: '10A'
        },
        parent: {
          id: 100,
          full_name: 'Parent Name'
        },
        credentials: {
          student: {
            username: 'student123',
            password: 'temp_pass_123'
          },
          parent: {
            username: 'parent123',
            password: 'temp_pass_456'
          }
        }
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockResponse,
        error: null
      });

      const requestData = {
        first_name: 'New',
        last_name: 'Student',
        grade: '10A',
        goal: 'University',
        parent_first_name: 'Parent',
        parent_last_name: 'Name',
        parent_email: 'parent@example.com',
        parent_phone: '+1234567890'
      };

      const result = await tutorAPI.createStudent(requestData);

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/tutor/students/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(requestData)
        })
      );
      expect(result.student.full_name).toBe('New Student');
      expect(result.credentials.student.username).toBe('student123');
    });

    it('should throw error when token is missing', async () => {
      vi.mocked(unifiedAPI.getToken).mockReturnValue(null);

      await expect(tutorAPI.createStudent({
        first_name: 'Test',
        last_name: 'Student',
        grade: '10A',
        parent_first_name: 'Parent',
        parent_last_name: 'Name',
        parent_email: 'test@example.com',
        parent_phone: '+1234567890'
      })).rejects.toThrow('HTTP 403: Forbidden');
    });

    it('should handle 403 Forbidden error', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'HTTP 403: Forbidden - Access denied'
      });

      await expect(tutorAPI.createStudent({
        first_name: 'Test',
        last_name: 'Student',
        grade: '10A',
        parent_first_name: 'Parent',
        parent_last_name: 'Name',
        parent_email: 'test@example.com',
        parent_phone: '+1234567890'
      })).rejects.toThrow('HTTP 403: Forbidden');
    });
  });

  describe('getStudent', () => {
    it('should fetch specific student', async () => {
      const mockStudent = {
        id: 1,
        full_name: 'Alice Smith',
        grade: '10A',
        goal: 'University',
        subjects: [
          {
            id: 1,
            name: 'Mathematics',
            teacher_name: 'John Teacher',
            enrollment_id: 101
          }
        ]
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockStudent,
        error: null
      });

      const result = await tutorAPI.getStudent(1);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/tutor/students/1/');
      expect(result.full_name).toBe('Alice Smith');
      expect(result.subjects).toHaveLength(1);
    });

    it('should throw error when student not found', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Student not found'
      });

      await expect(tutorAPI.getStudent(999)).rejects.toThrow('Student not found');
    });
  });

  describe('assignSubject', () => {
    it('should assign subject with all parameters', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null,
        status: 201
      });

      await tutorAPI.assignSubject(1, {
        subject_id: 10,
        subject_name: 'Mathematics',
        teacher_id: 5
      });

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/tutor/students/1/subjects/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            subject_id: 10,
            subject_name: 'Mathematics',
            teacher_id: 5
          })
        })
      );
    });

    it('should assign subject with only subject_id', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await tutorAPI.assignSubject(1, {
        subject_id: 10
      });

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/tutor/students/1/subjects/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ subject_id: 10 })
        })
      );
    });

    it('should throw error on assignment failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: { detail: 'Subject already assigned' },
        error: 'Assignment failed'
      });

      await expect(tutorAPI.assignSubject(1, {
        subject_id: 10
      })).rejects.toThrow();
    });
  });

  describe('removeSubject', () => {
    it('should remove subject from student', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await tutorAPI.removeSubject(1, 10);

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/tutor/students/1/subjects/10/',
        expect.objectContaining({
          method: 'DELETE'
        })
      );
    });

    it('should throw error on removal failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Subject not found'
      });

      await expect(tutorAPI.removeSubject(1, 10)).rejects.toThrow('Subject not found');
    });
  });
});
