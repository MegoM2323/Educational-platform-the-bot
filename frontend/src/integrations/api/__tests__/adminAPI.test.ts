import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminAPI } from '../adminAPI';
import { unifiedAPI } from '../unifiedClient';

vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

describe('adminAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('assignStudentsToTeacher', () => {
    it('test_assignStudentsToTeacher_sendsCorrectRequest', async () => {
      const mockResponse = {
        success: true,
        data: { success: true, assigned_students: [1, 2, 3] },
        timestamp: new Date().toISOString(),
      };

      (unifiedAPI.request as any).mockResolvedValue(mockResponse);

      const teacherId = 5;
      const data = {
        student_ids: [1, 2, 3],
        subject_id: 10,
      };

      const result = await adminAPI.assignStudentsToTeacher(teacherId, data);

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        `/auth/teachers/${teacherId}/assign-students/`,
        {
          method: 'POST',
          body: JSON.stringify(data),
        }
      );

      expect(result).toEqual(mockResponse);
    });

    it('test_assignStudentsToTeacher_correctSignature', async () => {
      const mockResponse = {
        success: true,
        data: { success: true, assigned_students: [10, 20] },
        timestamp: new Date().toISOString(),
      };

      (unifiedAPI.request as any).mockResolvedValue(mockResponse);

      const result = await adminAPI.assignStudentsToTeacher(1, {
        student_ids: [10, 20],
        subject_id: 5,
      });

      expect(result.success).toBe(true);
      expect(result.data?.assigned_students).toEqual([10, 20]);
    });

    it('test_assignStudentsToTeacher_correctUrlFormat', async () => {
      (unifiedAPI.request as any).mockResolvedValue({
        success: true,
        data: {},
        timestamp: new Date().toISOString(),
      });

      await adminAPI.assignStudentsToTeacher(123, {
        student_ids: [1],
        subject_id: 2,
      });

      const calledUrl = (unifiedAPI.request as any).mock.calls[0][0];
      expect(calledUrl).toBe('/auth/teachers/123/assign-students/');
    });

    it('test_assignStudentsToTeacher_parsesResponse', async () => {
      const mockData = {
        success: true,
        assigned_students: [1, 2, 3],
      };

      (unifiedAPI.request as any).mockResolvedValue({
        success: true,
        data: mockData,
        timestamp: new Date().toISOString(),
      });

      const result = await adminAPI.assignStudentsToTeacher(1, {
        student_ids: [1, 2, 3],
        subject_id: 1,
      });

      expect(result.data).toEqual(mockData);
      expect(result.data?.success).toBe(true);
      expect(result.data?.assigned_students).toHaveLength(3);
    });

    it('test_assignStudentsToTeacher_emptyStudentIds', async () => {
      (unifiedAPI.request as any).mockResolvedValue({
        success: true,
        data: { success: true, assigned_students: [] },
        timestamp: new Date().toISOString(),
      });

      const result = await adminAPI.assignStudentsToTeacher(1, {
        student_ids: [],
        subject_id: 1,
      });

      expect(result.success).toBe(true);
      expect(result.data?.assigned_students).toEqual([]);
    });

    it('test_assignStudentsToTeacher_handleError', async () => {
      (unifiedAPI.request as any).mockResolvedValue({
        success: false,
        error: 'Failed to assign students',
        timestamp: new Date().toISOString(),
      });

      const result = await adminAPI.assignStudentsToTeacher(1, {
        student_ids: [1, 2],
        subject_id: 1,
      });

      expect(result.success).toBe(false);
      expect(result.error).toBe('Failed to assign students');
    });
  });
});
