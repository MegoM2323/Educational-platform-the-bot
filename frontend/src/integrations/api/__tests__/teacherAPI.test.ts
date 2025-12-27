import { describe, it, expect, vi, beforeEach } from 'vitest';
import { teacherAPI } from '../teacher';
import { unifiedAPI } from '../unifiedClient';

// Mock unifiedAPI
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
    getToken: vi.fn(() => 'mock-token'),
  },
}));

describe('teacherAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getPendingSubmissions', () => {
    it('should fetch pending submissions', async () => {
      const mockSubmissions = [
        {
          id: 1,
          material_id: 101,
          material_title: 'Algebra Homework',
          student_id: 5,
          student_name: 'Alice Smith',
          submitted_at: '2025-01-20T10:00:00Z',
          submission_text: 'My homework answer',
          status: 'pending' as const
        },
        {
          id: 2,
          material_id: 102,
          material_title: 'Geometry Quiz',
          student_id: 6,
          student_name: 'Bob Johnson',
          submitted_at: '2025-01-19T14:30:00Z',
          submission_file: '/media/submissions/quiz.pdf',
          status: 'pending' as const
        }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: { pending: mockSubmissions },
        error: null
      });

      const result = await teacherAPI.getPendingSubmissions();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/materials/teacher/submissions/pending/');
      expect(result).toHaveLength(2);
      expect(result[0].student_name).toBe('Alice Smith');
      expect(result[1].submission_file).toBe('/media/submissions/quiz.pdf');
    });

    it('should return empty array when no pending submissions', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: { pending: [] },
        error: null
      });

      const result = await teacherAPI.getPendingSubmissions();

      expect(result).toEqual([]);
    });

    it('should throw error on request failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Failed to fetch submissions'
      });

      await expect(teacherAPI.getPendingSubmissions()).rejects.toThrow('Failed to fetch submissions');
    });
  });

  describe('provideFeedback', () => {
    it('should submit feedback with grade', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await teacherAPI.provideFeedback(1, {
        feedback_text: 'Excellent work!',
        grade: 95
      });

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/teacher/submissions/1/feedback/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            feedback_text: 'Excellent work!',
            grade: 95
          })
        })
      );
    });

    it('should submit feedback without grade', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await teacherAPI.provideFeedback(1, {
        feedback_text: 'Please revise section 2'
      });

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/teacher/submissions/1/feedback/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            feedback_text: 'Please revise section 2'
          })
        })
      );
    });

    it('should throw error on feedback submission failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Feedback submission failed'
      });

      await expect(teacherAPI.provideFeedback(1, {
        feedback_text: 'Test'
      })).rejects.toThrow('Feedback submission failed');
    });
  });

  describe('updateSubmissionStatus', () => {
    it('should update status to reviewed', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await teacherAPI.updateSubmissionStatus(1, 'reviewed');

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/teacher/submissions/1/status/',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ status: 'reviewed' })
        })
      );
    });

    it('should update status to needs_changes', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await teacherAPI.updateSubmissionStatus(2, 'needs_changes');

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/teacher/submissions/2/status/',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ status: 'needs_changes' })
        })
      );
    });

    it('should throw error on status update failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Status update failed'
      });

      await expect(teacherAPI.updateSubmissionStatus(1, 'reviewed')).rejects.toThrow('Status update failed');
    });
  });

  describe('getSubjects', () => {
    it('should fetch teacher subjects', async () => {
      const mockSubjects = [
        { id: 1, name: 'Mathematics', students_count: 15 },
        { id: 2, name: 'Physics', students_count: 12 }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: { subjects: mockSubjects },
        error: null
      });

      const result = await teacherAPI.getSubjects();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/materials/teacher/subjects/');
      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('Mathematics');
      expect(result[1].students_count).toBe(12);
    });

    it('should return empty array when no subjects', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: { subjects: [] },
        error: null
      });

      const result = await teacherAPI.getSubjects();

      expect(result).toEqual([]);
    });
  });

  describe('getAllStudents', () => {
    it('should fetch all students', async () => {
      const mockStudents = [
        { id: 1, full_name: 'Alice Smith', grade: '10A' },
        { id: 2, full_name: 'Bob Johnson', grade: '10B' }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: { students: mockStudents },
        error: null
      });

      const result = await teacherAPI.getAllStudents();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/materials/teacher/all-students/');
      expect(result).toHaveLength(2);
      expect(result[0].full_name).toBe('Alice Smith');
    });

    it('should handle empty student list', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: { students: [] },
        error: null
      });

      const result = await teacherAPI.getAllStudents();

      expect(result).toEqual([]);
    });
  });

  describe('assignSubjectToStudents', () => {
    it('should assign subject to multiple students using enrollment endpoint', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await teacherAPI.assignSubjectToStudents(1, [5, 6, 7]);

      // Should call enrollment endpoint for each student
      expect(unifiedAPI.request).toHaveBeenCalledTimes(3);
      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/subjects/1/enroll/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            student_id: 5,
            teacher_id: null
          })
        })
      );
      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/subjects/1/enroll/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            student_id: 6,
            teacher_id: null
          })
        })
      );
      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/subjects/1/enroll/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            student_id: 7,
            teacher_id: null
          })
        })
      );
    });

    it('should assign subject to single student using enrollment endpoint', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: {},
        error: null
      });

      await teacherAPI.assignSubjectToStudents(2, [10]);

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/materials/subjects/2/enroll/',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            student_id: 10,
            teacher_id: null
          })
        })
      );
    });

    it('should throw error when enrollment fails for any student', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Assignment failed'
      });

      await expect(teacherAPI.assignSubjectToStudents(1, [5])).rejects.toThrow('Failed to assign some students');
    });

    it('should collect errors from multiple failed enrollments', async () => {
      vi.mocked(unifiedAPI.request)
        .mockResolvedValueOnce({
          success: true,
          data: {},
          error: null
        })
        .mockResolvedValueOnce({
          success: false,
          data: null,
          error: 'Student already enrolled'
        })
        .mockResolvedValueOnce({
          success: false,
          data: null,
          error: 'Invalid teacher'
        });

      await expect(teacherAPI.assignSubjectToStudents(1, [5, 6, 7])).rejects.toThrow('Failed to assign some students');
    });
  });
});
