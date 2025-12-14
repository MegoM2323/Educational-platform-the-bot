import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTeacherGraphEditor } from '../useTeacherGraphEditor';
import { knowledgeGraphAPI } from '@/integrations/api/knowledgeGraphAPI';
import type { Student, KnowledgeGraph, Lesson, GraphLesson, LessonDependency } from '@/types/knowledgeGraph';
import React from 'react';

// Mock the API
vi.mock('@/integrations/api/knowledgeGraphAPI', () => ({
  knowledgeGraphAPI: {
    getTeacherStudents: vi.fn(),
    getOrCreateGraph: vi.fn(),
    getLessons: vi.fn(),
    addLessonToGraph: vi.fn(),
    removeLessonFromGraph: vi.fn(),
    batchUpdateLessons: vi.fn(),
    addDependency: vi.fn(),
    removeDependency: vi.fn(),
    deleteLesson: vi.fn(),
    deleteDependency: vi.fn(),
  },
}));

// ============================================
// Mock Data Fixtures
// ============================================

const mockStudents: Student[] = [
  {
    id: 1,
    email: 'student1@test.com',
    full_name: 'John Doe',
    role: 'student',
  },
  {
    id: 2,
    email: 'student2@test.com',
    full_name: 'Jane Smith',
    role: 'student',
  },
];

const mockLessons: Lesson[] = [
  {
    id: 1,
    title: 'Introduction to Calculus',
    description: 'Basic calculus concepts',
    subject: 5,
    subject_name: 'Mathematics',
    created_by: 10,
    created_at: '2025-01-01T10:00:00Z',
    updated_at: '2025-01-05T10:00:00Z',
    is_public: true,
    total_duration_minutes: 60,
    total_max_score: 100,
    elements_count: 5,
  },
  {
    id: 2,
    title: 'Derivatives',
    description: 'Understanding derivatives',
    subject: 5,
    subject_name: 'Mathematics',
    created_by: 10,
    created_at: '2025-01-02T10:00:00Z',
    updated_at: '2025-01-05T10:00:00Z',
    is_public: true,
    total_duration_minutes: 90,
    total_max_score: 100,
    elements_count: 8,
  },
  {
    id: 3,
    title: 'Integrals',
    description: 'Integration techniques',
    subject: 5,
    subject_name: 'Mathematics',
    created_by: 10,
    created_at: '2025-01-03T10:00:00Z',
    updated_at: '2025-01-05T10:00:00Z',
    is_public: true,
    total_duration_minutes: 120,
    total_max_score: 100,
    elements_count: 10,
  },
];

const mockGraphLessons: GraphLesson[] = [
  {
    id: 101,
    lesson: mockLessons[0],
    position_x: 100,
    position_y: 100,
    is_unlocked: true,
    node_color: '#FF6B6B',
    node_size: 50,
    added_at: '2025-01-10T10:00:00Z',
  },
];

const mockDependencies: LessonDependency[] = [
  {
    id: 201,
    from_lesson: 101,
    to_lesson: 102,
    dependency_type: 'required',
    min_score_percent: 80,
    created_at: '2025-01-10T10:30:00Z',
  },
];

const mockGraph: KnowledgeGraph = {
  id: 1,
  student: 1,
  student_name: 'John Doe',
  subject: 5,
  subject_name: 'Mathematics',
  lessons: mockGraphLessons,
  dependencies: mockDependencies,
  created_by: 10,
  created_at: '2025-01-10T10:00:00Z',
  updated_at: '2025-01-15T10:00:00Z',
  is_active: true,
  allow_skip: false,
};

// ============================================
// Test Utilities
// ============================================

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// ============================================
// Tests
// ============================================

describe('useTeacherGraphEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ============================================
  // 1. Hook Initialization Tests
  // ============================================

  describe('Hook Initialization', () => {
    it('should initialize with default state', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      // Check initial state
      expect(result.current.editState.modifiedPositions.size).toBe(0);
      expect(result.current.editState.addedLessons.size).toBe(0);
      expect(result.current.editState.removedLessons.size).toBe(0);
      expect(result.current.editState.addedDependencies).toHaveLength(0);
      expect(result.current.editState.removedDependencies.size).toBe(0);
      expect(result.current.hasUnsavedChanges).toBe(false);
    });

    it('should load students on mount', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingStudents).toBe(false);
      });

      expect(result.current.students).toEqual(mockStudents);
      expect(knowledgeGraphAPI.getTeacherStudents).toHaveBeenCalledTimes(1);
    });

    it('should auto-select first student when students load', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.selectedStudent).not.toBeNull();
      });

      expect(result.current.selectedStudent?.id).toBe(1);
      expect(result.current.selectedStudent?.full_name).toBe('John Doe');
    });

    it('should show loading states correctly', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      expect(result.current.isLoadingStudents).toBe(true);
      expect(result.current.students).toEqual([]);
    });

    it('should initialize with undefined subjectId', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);

      const { result } = renderHook(() => useTeacherGraphEditor(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingStudents).toBe(false);
      });

      // Without subjectId, graph and lessons should not load
      expect(result.current.graph).toBeNull();
      expect(result.current.availableLessons).toEqual([]);
    });
  });

  // ============================================
  // 2. Student Selection Tests
  // ============================================

  describe('Student Selection (selectStudent)', () => {
    it('should select student and load graph', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      // Wait for initial load
      await waitFor(() => {
        expect(result.current.students).toHaveLength(2);
      });

      // Select different student
      act(() => {
        result.current.selectStudent(mockStudents[1]);
      });

      expect(result.current.selectedStudent?.id).toBe(2);
      expect(result.current.selectedStudent?.full_name).toBe('Jane Smith');
    });

    it('should switch between students', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      // Initially first student is auto-selected
      await waitFor(() => {
        expect(result.current.selectedStudent).not.toBeNull();
      });

      expect(result.current.selectedStudent?.id).toBe(1);

      // Switch to second student
      act(() => {
        result.current.selectStudent(mockStudents[1]);
      });

      expect(result.current.selectedStudent?.id).toBe(2);
      expect(result.current.selectedStudent?.full_name).toBe('Jane Smith');

      // Switch back to first student
      act(() => {
        result.current.selectStudent(mockStudents[0]);
      });

      expect(result.current.selectedStudent?.id).toBe(1);
      expect(result.current.selectedStudent?.full_name).toBe('John Doe');
    });

    it('should load graph when student and subjectId selected', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.graph?.student).toBe(1);
      expect(result.current.graph?.lessons).toEqual(mockGraphLessons);
    });
  });

  // ============================================
  // 3. Add Lesson Tests
  // ============================================

  describe('Add Lesson (addLesson)', () => {
    it('should add lesson to editState and set hasUnsavedChanges', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.addLessonToGraph).mockResolvedValue({
        ...mockGraphLessons[0],
        id: 102,
      });

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // Add lesson
      await act(async () => {
        await result.current.addLesson(2, 200, 200);
      });

      expect(result.current.editState.addedLessons.has(2)).toBe(true);
      expect(result.current.hasUnsavedChanges).toBe(true);
    });

    it('should add lesson with default position (0, 0)', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.addLessonToGraph).mockResolvedValue({
        ...mockGraphLessons[0],
        id: 102,
      });

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // Add lesson without position
      await act(async () => {
        await result.current.addLesson(2);
      });

      expect(result.current.editState.addedLessons.has(2)).toBe(true);
    });

    it('should not add lesson if graph is null', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);

      const { result } = renderHook(() => useTeacherGraphEditor(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.students).toHaveLength(2);
      });

      // Try to add without graph
      await act(async () => {
        await result.current.addLesson(2);
      });

      expect(result.current.editState.addedLessons.size).toBe(0);
      expect(result.current.hasUnsavedChanges).toBe(false);
    });

    it('should push to undo stack when adding lesson', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.addLessonToGraph).mockResolvedValue({
        ...mockGraphLessons[0],
        id: 102,
      });

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      await act(async () => {
        await result.current.addLesson(2);
      });

      expect(result.current.canUndo).toBe(true);
    });

    it('should call API with correct parameters', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.addLessonToGraph).mockResolvedValue({
        ...mockGraphLessons[0],
        id: 102,
      });

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      await act(async () => {
        await result.current.addLesson(2, 150, 250);
      });

      expect(knowledgeGraphAPI.addLessonToGraph).toHaveBeenCalledWith(mockGraph.id, {
        lesson_id: 2,
        position_x: 150,
        position_y: 250,
      });
    });
  });

  // ============================================
  // 4. Remove Lesson Tests
  // ============================================

  describe('Remove Lesson (removeLesson)', () => {
    it('should add lesson to removedLessons set', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.removeLesson(101);
      });

      expect(result.current.editState.removedLessons.has(101)).toBe(true);
      expect(result.current.hasUnsavedChanges).toBe(true);
    });

    it('should support removing multiple lessons', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.removeLesson(101);
        result.current.removeLesson(102);
      });

      expect(result.current.editState.removedLessons.size).toBe(2);
    });

    it('should push to undo stack when removing lesson', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      act(() => {
        result.current.removeLesson(101);
      });

      expect(result.current.canUndo).toBe(true);
    });
  });

  // ============================================
  // 5. Update Lesson Position Tests
  // ============================================

  describe('Update Lesson Position (updateLessonPosition)', () => {
    it('should update lesson position in editState', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      const position = result.current.editState.modifiedPositions.get(101);
      expect(position).toEqual({ x: 500, y: 600 });
      expect(result.current.hasUnsavedChanges).toBe(true);
    });

    it('should support updating multiple lesson positions', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 100, 100);
        result.current.updateLessonPosition(102, 200, 200);
      });

      expect(result.current.editState.modifiedPositions.size).toBe(2);
    });

    it('should overwrite previous position for same lesson', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 100, 100);
        result.current.updateLessonPosition(101, 300, 400);
      });

      const position = result.current.editState.modifiedPositions.get(101);
      expect(position).toEqual({ x: 300, y: 400 });
      expect(result.current.editState.modifiedPositions.size).toBe(1);
    });

    it('should push to undo stack when updating position', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      expect(result.current.canUndo).toBe(true);
    });
  });

  // ============================================
  // 6. Add Dependency Tests
  // ============================================

  describe('Add Dependency (addDependency)', () => {
    it('should add dependency to editState', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.addDependency(101, 102);
      });

      expect(result.current.editState.addedDependencies).toEqual([{ from: 101, to: 102 }]);
      expect(result.current.hasUnsavedChanges).toBe(true);
    });

    it('should support adding multiple dependencies', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.addDependency(101, 102);
        result.current.addDependency(102, 103);
      });

      expect(result.current.editState.addedDependencies).toHaveLength(2);
    });

    it('should allow duplicate dependencies (different lessons)', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.addDependency(101, 102);
        result.current.addDependency(101, 102); // Same dependency twice
      });

      expect(result.current.editState.addedDependencies).toHaveLength(2);
    });

    it('should push to undo stack when adding dependency', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      act(() => {
        result.current.addDependency(101, 102);
      });

      expect(result.current.canUndo).toBe(true);
    });
  });

  // ============================================
  // 7. Remove Dependency Tests
  // ============================================

  describe('Remove Dependency (removeDependency)', () => {
    it('should add dependency to removedDependencies set', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.removeDependency(201);
      });

      expect(result.current.editState.removedDependencies.has(201)).toBe(true);
      expect(result.current.hasUnsavedChanges).toBe(true);
    });

    it('should support removing multiple dependencies', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.removeDependency(201);
        result.current.removeDependency(202);
      });

      expect(result.current.editState.removedDependencies.size).toBe(2);
    });

    it('should push to undo stack when removing dependency', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      act(() => {
        result.current.removeDependency(201);
      });

      expect(result.current.canUndo).toBe(true);
    });
  });

  // ============================================
  // 8. Save Changes Tests
  // ============================================

  describe('Save Changes (saveChanges)', () => {
    it('should save position changes', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.batchUpdateLessons).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(knowledgeGraphAPI.batchUpdateLessons).toHaveBeenCalledWith(mockGraph.id, {
        lessons: [{ graph_lesson_id: 101, position_x: 500, position_y: 600 }],
      });
    });

    it('should save lesson removal', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.removeLessonFromGraph).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.removeLesson(101);
      });

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(knowledgeGraphAPI.removeLessonFromGraph).toHaveBeenCalledWith(mockGraph.id, 101);
    });

    it('should save dependency addition', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.addDependency).mockResolvedValue({
        ...mockDependencies[0],
        id: 202,
      });

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.addDependency(101, 102);
      });

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(knowledgeGraphAPI.addDependency).toHaveBeenCalledWith(mockGraph.id, 101, {
        to_lesson_id: 102,
      });
    });

    it('should save dependency removal', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.removeDependency).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.removeDependency(201);
      });

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(knowledgeGraphAPI.removeDependency).toHaveBeenCalledWith(
        mockGraph.id,
        mockDependencies[0].from_lesson,
        201
      );
    });

    it('should reset editState after successful save', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.batchUpdateLessons).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      expect(result.current.hasUnsavedChanges).toBe(true);

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);
      expect(result.current.editState.addedLessons.size).toBe(0);
      expect(result.current.editState.removedLessons.size).toBe(0);
      expect(result.current.editState.addedDependencies).toHaveLength(0);
      expect(result.current.editState.removedDependencies.size).toBe(0);
      expect(result.current.hasUnsavedChanges).toBe(false);
    });

    it('should clear undo/redo stacks after save', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.batchUpdateLessons).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      expect(result.current.canUndo).toBe(true);

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(result.current.canUndo).toBe(false);
      expect(result.current.canRedo).toBe(false);
    });

    it('should not do anything if graph is null', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);

      const { result } = renderHook(() => useTeacherGraphEditor(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.students).toHaveLength(2);
      });

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(knowledgeGraphAPI.batchUpdateLessons).not.toHaveBeenCalled();
    });

    it('should save multiple changes in one call', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.batchUpdateLessons).mockResolvedValue(undefined);
      vi.mocked(knowledgeGraphAPI.removeLessonFromGraph).mockResolvedValue(undefined);
      vi.mocked(knowledgeGraphAPI.addDependency).mockResolvedValue({
        ...mockDependencies[0],
      });
      vi.mocked(knowledgeGraphAPI.removeDependency).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
        result.current.removeLesson(102);
        result.current.addDependency(101, 103);
        result.current.removeDependency(201);
      });

      await act(async () => {
        await result.current.saveChanges();
      });

      expect(knowledgeGraphAPI.batchUpdateLessons).toHaveBeenCalled();
      expect(knowledgeGraphAPI.removeLessonFromGraph).toHaveBeenCalled();
      expect(knowledgeGraphAPI.addDependency).toHaveBeenCalled();
      expect(knowledgeGraphAPI.removeDependency).toHaveBeenCalled();
    });
  });

  // ============================================
  // 9. Cancel Changes Tests
  // ============================================

  describe('Cancel Changes (cancelChanges)', () => {
    it('should reset editState to initial state', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
        result.current.removeLesson(102);
        result.current.addDependency(101, 103);
      });

      expect(result.current.hasUnsavedChanges).toBe(true);

      act(() => {
        result.current.cancelChanges();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);
      expect(result.current.editState.addedLessons.size).toBe(0);
      expect(result.current.editState.removedLessons.size).toBe(0);
      expect(result.current.editState.addedDependencies).toHaveLength(0);
      expect(result.current.editState.removedDependencies.size).toBe(0);
      expect(result.current.hasUnsavedChanges).toBe(false);
    });

    it('should clear undo/redo stacks', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      expect(result.current.canUndo).toBe(true);

      act(() => {
        result.current.cancelChanges();
      });

      expect(result.current.canUndo).toBe(false);
      expect(result.current.canRedo).toBe(false);
    });
  });

  // ============================================
  // 10. Undo/Redo Tests
  // ============================================

  describe('Undo/Redo Functionality', () => {
    it('should undo last action', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // First change
      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      expect(result.current.editState.modifiedPositions.size).toBe(1);

      // Undo
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);
      expect(result.current.canUndo).toBe(false);
      expect(result.current.canRedo).toBe(true);
    });

    it('should redo undone action', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // First change
      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      // Undo
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);

      // Redo
      act(() => {
        result.current.redo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(1);
      const position = result.current.editState.modifiedPositions.get(101);
      expect(position).toEqual({ x: 500, y: 600 });
    });

    it('should support multiple undo/redo operations', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // First change - position update
      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      // Second change - remove lesson
      act(() => {
        result.current.removeLesson(102);
      });

      expect(result.current.canUndo).toBe(true);
      expect(result.current.editState.modifiedPositions.size).toBe(1);
      expect(result.current.editState.removedLessons.size).toBe(1);

      // Undo first time - removes second change (removeLesson)
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.removedLessons.size).toBe(0);
      expect(result.current.editState.modifiedPositions.size).toBe(1); // Position update still there
      expect(result.current.canUndo).toBe(true);
      expect(result.current.canRedo).toBe(true);

      // Undo second time - removes first change (updatePosition)
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);
      expect(result.current.editState.removedLessons.size).toBe(0);
      expect(result.current.canUndo).toBe(false);
      expect(result.current.canRedo).toBe(true);

      // Redo first time - restores position update
      act(() => {
        result.current.redo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(1);
      expect(result.current.editState.removedLessons.size).toBe(0);
      expect(result.current.canUndo).toBe(true);
      expect(result.current.canRedo).toBe(true);

      // Redo second time - restores removal
      act(() => {
        result.current.redo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(1);
      expect(result.current.editState.removedLessons.size).toBe(1);
      expect(result.current.canUndo).toBe(true);
      expect(result.current.canRedo).toBe(false);
    });

    it('should clear redo stack when new action after undo', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // First change
      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      // Second change
      act(() => {
        result.current.removeLesson(102);
      });

      // Undo
      act(() => {
        result.current.undo();
      });

      expect(result.current.canRedo).toBe(true);

      // New change
      act(() => {
        result.current.addDependency(101, 103);
      });

      // Redo stack should be cleared
      expect(result.current.canRedo).toBe(false);
    });

    it('should not undo if undo stack is empty', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      // Try to undo - should do nothing
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);
    });

    it('should not redo if redo stack is empty', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canRedo).toBe(false);

      // Try to redo - should do nothing
      act(() => {
        result.current.redo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);
    });
  });

  // ============================================
  // 11. Complex Scenarios
  // ============================================

  describe('Complex Scenarios', () => {
    it('should handle mixed operations', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.addLessonToGraph).mockResolvedValue({
        ...mockGraphLessons[0],
        id: 102,
      });
      vi.mocked(knowledgeGraphAPI.batchUpdateLessons).mockResolvedValue(undefined);
      vi.mocked(knowledgeGraphAPI.removeLessonFromGraph).mockResolvedValue(undefined);
      vi.mocked(knowledgeGraphAPI.addDependency).mockResolvedValue({
        ...mockDependencies[0],
        id: 202,
      });

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // Perform mixed operations - use synchronous ones first, then async
      await act(async () => {
        result.current.updateLessonPosition(101, 100, 100);
      });

      act(() => {
        result.current.removeLesson(102);
      });

      act(() => {
        result.current.addDependency(101, 102);
      });

      await act(async () => {
        await result.current.addLesson(2);
      });

      expect(result.current.hasUnsavedChanges).toBe(true);
      expect(result.current.canUndo).toBe(true);

      // Verify all changes are recorded
      expect(result.current.editState.addedLessons.size).toBe(1);
      expect(result.current.editState.modifiedPositions.size).toBe(1);
      expect(result.current.editState.removedLessons.size).toBe(1);
      expect(result.current.editState.addedDependencies).toHaveLength(1);

      // Undo last change (addLesson)
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.addedLessons.size).toBe(0);
      expect(result.current.editState.addedDependencies).toHaveLength(1);

      // Undo previous change (addDependency)
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.addedDependencies).toHaveLength(0);
      expect(result.current.editState.removedLessons.size).toBe(1);

      // Undo previous change (removeLesson)
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.removedLessons.size).toBe(0);
      expect(result.current.editState.modifiedPositions.size).toBe(1);

      // Undo first change (updateLessonPosition)
      act(() => {
        result.current.undo();
      });

      expect(result.current.editState.modifiedPositions.size).toBe(0);
      expect(result.current.canUndo).toBe(false);
    });

    it('should track unsaved changes correctly', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.hasUnsavedChanges).toBe(false);

      // Add position change
      act(() => {
        result.current.updateLessonPosition(101, 500, 600);
      });

      expect(result.current.hasUnsavedChanges).toBe(true);

      // Add another change
      act(() => {
        result.current.removeLesson(102);
      });

      expect(result.current.hasUnsavedChanges).toBe(true);

      // Undo first change
      act(() => {
        result.current.undo();
      });

      // Still has changes from second action
      expect(result.current.hasUnsavedChanges).toBe(true);

      // Undo second change
      act(() => {
        result.current.undo();
      });

      // Now no changes
      expect(result.current.hasUnsavedChanges).toBe(false);
    });
  });

  // ============================================
  // 12. Error Handling Tests
  // ============================================

  describe('Error Handling', () => {
    it('should handle student loading error', async () => {
      const error = new Error('Failed to load students');
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockRejectedValue(error);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingStudents).toBe(false);
      });

      expect(result.current.studentsError).toBeDefined();
      expect(result.current.students).toEqual([]);
    });

    it('should handle graph loading error', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockRejectedValue(
        new Error('Failed to load graph')
      );
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingGraph).toBe(false);
      });

      expect(result.current.graphError).toBeDefined();
      expect(result.current.graph).toBeNull();
    });

    it('should handle lessons loading error', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockRejectedValue(
        new Error('Failed to load lessons')
      );

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isLoadingLessons).toBe(false);
      });

      expect(result.current.lessonsError).toBeDefined();
      expect(result.current.availableLessons).toEqual([]);
    });
  });

  // ============================================
  // 13. Delete Lesson Tests (T011)
  // ============================================

  describe('Delete Lesson (deleteLesson)', () => {
    it('should delete lesson and update state', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteLesson).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.isDeleting).toBe(false);
      expect(result.current.deleteError).toBeNull();

      // Delete lesson
      await act(async () => {
        await result.current.deleteLesson(mockLessons[0].id);
      });

      expect(knowledgeGraphAPI.deleteLesson).toHaveBeenCalledWith(mockGraph.id, mockLessons[0].id);
      expect(result.current.isDeleting).toBe(false);
      expect(result.current.deleteError).toBeNull();
    });

    it('should push to undo stack after successful deletion', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteLesson).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      await act(async () => {
        await result.current.deleteLesson(mockLessons[0].id);
      });

      expect(result.current.canUndo).toBe(true);
    });

    it('should handle 403 permission error', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteLesson).mockRejectedValue(
        new Error('403 Forbidden: Только создатель урока может удалить его')
      );

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      await act(async () => {
        try {
          await result.current.deleteLesson(mockLessons[0].id);
        } catch (error) {
          // Expected error
        }
      });

      expect(result.current.deleteError).not.toBeNull();
      expect(result.current.deleteError?.type).toBe('permission');
      expect(result.current.deleteError?.statusCode).toBe(403);
    });

    it('should handle 404 not found error', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteLesson).mockRejectedValue(
        new Error('404 Not Found: Урок не найден')
      );

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      await act(async () => {
        try {
          await result.current.deleteLesson(999);
        } catch (error) {
          // Expected error
        }
      });

      expect(result.current.deleteError).not.toBeNull();
      expect(result.current.deleteError?.type).toBe('not_found');
      expect(result.current.deleteError?.statusCode).toBe(404);
    });

    it('should handle 400 validation error (multi-graph warning)', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteLesson).mockRejectedValue(
        new Error('400 Bad Request: Урок используется в 3 графах')
      );

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      await act(async () => {
        try {
          await result.current.deleteLesson(mockLessons[0].id);
        } catch (error) {
          // Expected error
        }
      });

      expect(result.current.deleteError).not.toBeNull();
      expect(result.current.deleteError?.type).toBe('validation');
      expect(result.current.deleteError?.statusCode).toBe(400);
    });

    it('should not delete if graph is null', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);

      const { result } = renderHook(() => useTeacherGraphEditor(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.students).toHaveLength(2);
      });

      await act(async () => {
        await result.current.deleteLesson(1);
      });

      expect(knowledgeGraphAPI.deleteLesson).not.toHaveBeenCalled();
    });

    it('should clear deleteError when new deletion starts', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);

      // First call fails
      vi.mocked(knowledgeGraphAPI.deleteLesson).mockRejectedValueOnce(
        new Error('403 Forbidden')
      );

      // Second call succeeds
      vi.mocked(knowledgeGraphAPI.deleteLesson).mockResolvedValueOnce(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      // First deletion fails
      await act(async () => {
        try {
          await result.current.deleteLesson(1);
        } catch (error) {
          // Expected
        }
      });

      expect(result.current.deleteError).not.toBeNull();

      // Second deletion succeeds and clears error
      await act(async () => {
        await result.current.deleteLesson(2);
      });

      expect(result.current.deleteError).toBeNull();
    });
  });

  // ============================================
  // 14. Delete Dependency Tests (T011)
  // ============================================

  describe('Delete Dependency (deleteDependency)', () => {
    it('should delete dependency and update state', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteDependency).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.isDeleting).toBe(false);

      // Delete dependency
      await act(async () => {
        await result.current.deleteDependency(
          mockDependencies[0].id,
          mockDependencies[0].from_lesson,
          mockDependencies[0].to_lesson
        );
      });

      expect(knowledgeGraphAPI.deleteDependency).toHaveBeenCalledWith(
        mockGraph.id,
        mockDependencies[0].to_lesson,
        mockDependencies[0].id
      );
      expect(result.current.isDeleting).toBe(false);
      expect(result.current.deleteError).toBeNull();
    });

    it('should push to undo stack after successful deletion', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteDependency).mockResolvedValue(undefined);

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      expect(result.current.canUndo).toBe(false);

      await act(async () => {
        await result.current.deleteDependency(201, 101, 102);
      });

      expect(result.current.canUndo).toBe(true);
    });

    it('should handle 403 permission error', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteDependency).mockRejectedValue(
        new Error('403 Forbidden: Только создатель графа может удалять зависимости')
      );

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      await act(async () => {
        try {
          await result.current.deleteDependency(201, 101, 102);
        } catch (error) {
          // Expected error
        }
      });

      expect(result.current.deleteError).not.toBeNull();
      expect(result.current.deleteError?.type).toBe('permission');
    });

    it('should handle 404 not found error', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);
      vi.mocked(knowledgeGraphAPI.getOrCreateGraph).mockResolvedValue(mockGraph);
      vi.mocked(knowledgeGraphAPI.getLessons).mockResolvedValue(mockLessons);
      vi.mocked(knowledgeGraphAPI.deleteDependency).mockRejectedValue(
        new Error('404 Not Found: Зависимость не найдена')
      );

      const { result } = renderHook(() => useTeacherGraphEditor(5), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.graph).not.toBeNull();
      });

      await act(async () => {
        try {
          await result.current.deleteDependency(999, 101, 102);
        } catch (error) {
          // Expected error
        }
      });

      expect(result.current.deleteError).not.toBeNull();
      expect(result.current.deleteError?.type).toBe('not_found');
    });

    it('should not delete if graph is null', async () => {
      vi.mocked(knowledgeGraphAPI.getTeacherStudents).mockResolvedValue(mockStudents);

      const { result } = renderHook(() => useTeacherGraphEditor(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.students).toHaveLength(2);
      });

      await act(async () => {
        await result.current.deleteDependency(201, 101, 102);
      });

      expect(knowledgeGraphAPI.deleteDependency).not.toHaveBeenCalled();
    });
  });
});
