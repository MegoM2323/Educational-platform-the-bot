import { describe, it, expect, vi, beforeEach } from 'vitest';
import { studentAPI } from '../student';
import { unifiedAPI } from '../unifiedClient';

// Mock unifiedAPI
vi.mock('../unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
    getToken: vi.fn(() => 'mock-token'),
  },
}));

describe('studentAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getSubjects', () => {
    it('should fetch and transform subjects from materials_by_subject', async () => {
      const mockData = {
        materials_by_subject: {
          'Math': {
            subject_info: {
              id: 1,
              name: 'Mathematics',
              color: '#FF5733',
              teacher: {
                id: 10,
                full_name: 'John Doe'
              }
            },
            materials: []
          },
          'Physics': {
            subject_info: {
              id: 2,
              name: 'Physics',
              color: '#33FF57',
              teacher: {
                id: 11,
                full_name: 'Jane Smith'
              }
            },
            materials: []
          }
        }
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockData,
        error: null
      });

      const result = await studentAPI.getSubjects();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/materials/student/');
      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        id: 1,
        name: 'Mathematics',
        color: '#FF5733',
        teacher: {
          id: 10,
          full_name: 'John Doe'
        },
        enrollment_status: 'enrolled'
      });
    });

    it('should handle missing teacher data', async () => {
      const mockData = {
        materials_by_subject: {
          'Math': {
            subject_info: {
              id: 1,
              name: 'Mathematics',
              teacher: null
            },
            materials: []
          }
        }
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockData,
        error: null
      });

      const result = await studentAPI.getSubjects();

      expect(result[0].teacher).toEqual({
        id: 0,
        full_name: 'Не назначен'
      });
    });

    it('should return empty array when no subjects exist', async () => {
      const mockData = {
        materials_by_subject: {}
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockData,
        error: null
      });

      const result = await studentAPI.getSubjects();

      expect(result).toEqual([]);
    });

    it('should throw error when request fails', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Network error'
      });

      await expect(studentAPI.getSubjects()).rejects.toThrow('Network error');
    });
  });

  describe('getSubjectMaterials', () => {
    it('should fetch materials for specific subject', async () => {
      const mockData = {
        materials_by_subject: {
          'Math': {
            subject_info: {
              id: 1,
              name: 'Mathematics'
            },
            materials: [
              {
                id: 101,
                title: 'Algebra Basics',
                description: 'Introduction to algebra',
                created_at: '2025-01-15T10:00:00Z',
                type: 'lesson',
                status: 'new',
                progress_percentage: 0
              },
              {
                id: 102,
                title: 'Geometry',
                description: 'Shapes and angles',
                created_at: '2025-01-16T10:00:00Z',
                type: 'lesson',
                status: 'in_progress',
                progress_percentage: 45
              }
            ]
          }
        }
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockData,
        error: null
      });

      const result = await studentAPI.getSubjectMaterials(1);

      expect(result).toHaveLength(2);
      expect(result[0]).toEqual({
        id: 101,
        title: 'Algebra Basics',
        description: 'Introduction to algebra',
        created_at: '2025-01-15T10:00:00Z',
        type: 'lesson',
        status: 'new',
        progress_percentage: 0
      });
    });

    it('should return empty array for non-existent subject', async () => {
      const mockData = {
        materials_by_subject: {
          'Math': {
            subject_info: { id: 1, name: 'Mathematics' },
            materials: []
          }
        }
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockData,
        error: null
      });

      const result = await studentAPI.getSubjectMaterials(999);

      expect(result).toEqual([]);
    });

    it('should handle materials without progress_percentage', async () => {
      const mockData = {
        materials_by_subject: {
          'Math': {
            subject_info: { id: 1, name: 'Mathematics' },
            materials: [
              {
                id: 101,
                title: 'Test Material',
                created_at: '2025-01-15T10:00:00Z'
              }
            ]
          }
        }
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockData,
        error: null
      });

      const result = await studentAPI.getSubjectMaterials(1);

      expect(result[0].progress_percentage).toBe(0);
    });
  });

  describe('submitHomework', () => {
    it('should submit homework with FormData', async () => {
      const mockSubmission = {
        id: 1,
        status: 'pending',
        submitted_at: '2025-01-20T10:00:00Z'
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockSubmission,
        error: null
      });

      const formData = new FormData();
      formData.append('text', 'My homework submission');

      const result = await studentAPI.submitHomework(101, formData);

      expect(unifiedAPI.request).toHaveBeenCalledWith(
        '/student/materials/101/submissions/',
        expect.objectContaining({
          method: 'POST',
          body: formData,
          headers: {}
        })
      );
      expect(result).toEqual(mockSubmission);
    });

    it('should throw error on submission failure', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: false,
        data: null,
        error: 'Submission failed'
      });

      const formData = new FormData();

      await expect(studentAPI.submitHomework(101, formData)).rejects.toThrow('Submission failed');
    });
  });

  describe('getFeedback', () => {
    it('should fetch feedback for submission', async () => {
      const mockFeedback = {
        id: 1,
        submission_id: 101,
        teacher_id: 10,
        feedback_text: 'Great work!',
        grade: 95,
        created_at: '2025-01-21T10:00:00Z'
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockFeedback,
        error: null
      });

      const result = await studentAPI.getFeedback(101);

      expect(unifiedAPI.request).toHaveBeenCalledWith('/student/submissions/101/feedback/');
      expect(result).toEqual(mockFeedback);
    });

    it('should handle feedback without grade', async () => {
      const mockFeedback = {
        id: 1,
        submission_id: 101,
        teacher_id: 10,
        feedback_text: 'Needs improvement',
        created_at: '2025-01-21T10:00:00Z'
      };

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockFeedback,
        error: null
      });

      const result = await studentAPI.getFeedback(101);

      expect(result.grade).toBeUndefined();
    });
  });

  describe('getSubmissions', () => {
    it('should fetch all submissions', async () => {
      const mockSubmissions = [
        {
          id: 1,
          status: 'pending',
          submitted_at: '2025-01-20T10:00:00Z'
        },
        {
          id: 2,
          status: 'reviewed',
          submitted_at: '2025-01-19T10:00:00Z'
        }
      ];

      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: mockSubmissions,
        error: null
      });

      const result = await studentAPI.getSubmissions();

      expect(unifiedAPI.request).toHaveBeenCalledWith('/student/submissions/');
      expect(result).toHaveLength(2);
      expect(result[0].status).toBe('pending');
    });

    it('should return empty array when no submissions exist', async () => {
      vi.mocked(unifiedAPI.request).mockResolvedValue({
        success: true,
        data: [],
        error: null
      });

      const result = await studentAPI.getSubmissions();

      expect(result).toEqual([]);
    });
  });
});
