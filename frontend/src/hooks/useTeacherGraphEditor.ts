/**
 * Custom Hook for Teacher Graph Editor
 * Управление состоянием графа знаний для преподавателя
 */

import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeGraphAPI } from '@/integrations/api/knowledgeGraphAPI';
import type {
  Student,
  KnowledgeGraph,
  Lesson,
  EditState,
} from '@/types/knowledgeGraph';

export interface UseTeacherGraphEditorReturn {
  // Data
  students: Student[];
  selectedStudent: Student | null;
  graph: KnowledgeGraph | null;
  availableLessons: Lesson[];

  // Loading states
  isLoadingStudents: boolean;
  isLoadingGraph: boolean;
  isLoadingLessons: boolean;
  isSaving: boolean;

  // Error states
  studentsError: Error | null;
  graphError: Error | null;
  lessonsError: Error | null;

  // Edit state
  editState: EditState;
  hasUnsavedChanges: boolean;

  // Actions
  selectStudent: (student: Student | null) => void;
  addLesson: (lessonId: number, x?: number, y?: number) => Promise<void>;
  removeLesson: (graphLessonId: number) => void;
  updateLessonPosition: (graphLessonId: number, x: number, y: number) => void;
  addDependency: (fromLessonId: number, toLessonId: number) => void;
  removeDependency: (dependencyId: number) => void;
  saveChanges: () => Promise<void>;
  cancelChanges: () => void;
  undo: () => void;
  redo: () => void;

  // Undo/Redo
  canUndo: boolean;
  canRedo: boolean;
}

export const useTeacherGraphEditor = (subjectId?: number): UseTeacherGraphEditorReturn => {
  const queryClient = useQueryClient();

  // State
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [editState, setEditState] = useState<EditState>({
    modifiedPositions: new Map(),
    addedLessons: new Set(),
    removedLessons: new Set(),
    addedDependencies: [],
    removedDependencies: new Set(),
  });
  const [undoStack, setUndoStack] = useState<EditState[]>([]);
  const [redoStack, setRedoStack] = useState<EditState[]>([]);

  // Queries
  const {
    data: students = [],
    isLoading: isLoadingStudents,
    error: studentsError,
  } = useQuery<Student[], Error>({
    queryKey: ['teacher-students'],
    queryFn: knowledgeGraphAPI.getTeacherStudents,
    staleTime: 60000, // 1 minute
  });

  const {
    data: graph = null,
    isLoading: isLoadingGraph,
    error: graphError,
    refetch: refetchGraph,
  } = useQuery<KnowledgeGraph | null, Error>({
    queryKey: ['knowledge-graph', selectedStudent?.id, subjectId],
    queryFn: () => {
      if (!selectedStudent || !subjectId) return Promise.resolve(null);
      return knowledgeGraphAPI.getOrCreateGraph(selectedStudent.id, subjectId);
    },
    enabled: !!selectedStudent && !!subjectId,
    staleTime: 30000, // 30 seconds
  });

  const {
    data: availableLessons = [],
    isLoading: isLoadingLessons,
    error: lessonsError,
  } = useQuery<Lesson[], Error>({
    queryKey: ['lessons', subjectId],
    queryFn: () =>
      knowledgeGraphAPI.getLessons({
        subject: subjectId,
        created_by: 'me', // Only teacher's own lessons
      }),
    enabled: !!subjectId,
    staleTime: 60000, // 1 minute
  });

  // Mutations
  const addLessonMutation = useMutation({
    mutationFn: ({
      graphId,
      lessonId,
      x,
      y,
    }: {
      graphId: number;
      lessonId: number;
      x?: number;
      y?: number;
    }) => knowledgeGraphAPI.addLessonToGraph(graphId, { lesson_id: lessonId, position_x: x, position_y: y }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] });
    },
  });

  const batchUpdateMutation = useMutation({
    mutationFn: ({
      graphId,
      updates,
    }: {
      graphId: number;
      updates: { graph_lesson_id: number; position_x: number; position_y: number }[];
    }) => knowledgeGraphAPI.batchUpdateLessons(graphId, { lessons: updates }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] });
    },
  });

  const removeLessonMutation = useMutation({
    mutationFn: ({ graphId, graphLessonId }: { graphId: number; graphLessonId: number }) =>
      knowledgeGraphAPI.removeLessonFromGraph(graphId, graphLessonId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] });
    },
  });

  const addDependencyMutation = useMutation({
    mutationFn: ({
      graphId,
      fromLessonId,
      toLessonId,
    }: {
      graphId: number;
      fromLessonId: number;
      toLessonId: number;
    }) => knowledgeGraphAPI.addDependency(graphId, fromLessonId, { to_lesson_id: toLessonId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] });
    },
  });

  const removeDependencyMutation = useMutation({
    mutationFn: ({
      graphId,
      lessonId,
      dependencyId,
    }: {
      graphId: number;
      lessonId: number;
      dependencyId: number;
    }) => knowledgeGraphAPI.removeDependency(graphId, lessonId, dependencyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-graph'] });
    },
  });

  // Auto-select first student
  useEffect(() => {
    if (students.length > 0 && !selectedStudent) {
      setSelectedStudent(students[0]);
    }
  }, [students, selectedStudent]);

  // Reset edit state when graph changes
  useEffect(() => {
    setEditState({
      modifiedPositions: new Map(),
      addedLessons: new Set(),
      removedLessons: new Set(),
      addedDependencies: [],
      removedDependencies: new Set(),
    });
    setUndoStack([]);
    setRedoStack([]);
  }, [graph?.id]);

  // Helpers
  const pushToUndoStack = useCallback(() => {
    setUndoStack((prev) => [...prev, { ...editState }]);
    setRedoStack([]); // Clear redo stack on new action
  }, [editState]);

  const hasUnsavedChanges =
    editState.modifiedPositions.size > 0 ||
    editState.addedLessons.size > 0 ||
    editState.removedLessons.size > 0 ||
    editState.addedDependencies.length > 0 ||
    editState.removedDependencies.size > 0;

  // Actions
  const selectStudent = useCallback((student: Student | null) => {
    setSelectedStudent(student);
  }, []);

  const addLesson = useCallback(
    async (lessonId: number, x: number = 0, y: number = 0) => {
      if (!graph) return;

      pushToUndoStack();

      // Optimistic update
      setEditState((prev) => ({
        ...prev,
        addedLessons: new Set([...prev.addedLessons, lessonId]),
      }));

      // API call
      await addLessonMutation.mutateAsync({
        graphId: graph.id,
        lessonId,
        x,
        y,
      });
    },
    [graph, pushToUndoStack, addLessonMutation]
  );

  const removeLesson = useCallback(
    (graphLessonId: number) => {
      pushToUndoStack();

      setEditState((prev) => ({
        ...prev,
        removedLessons: new Set([...prev.removedLessons, graphLessonId]),
      }));
    },
    [pushToUndoStack]
  );

  const updateLessonPosition = useCallback(
    (graphLessonId: number, x: number, y: number) => {
      pushToUndoStack();

      setEditState((prev) => {
        const newPositions = new Map(prev.modifiedPositions);
        newPositions.set(graphLessonId, { x, y });
        return {
          ...prev,
          modifiedPositions: newPositions,
        };
      });
    },
    [pushToUndoStack]
  );

  const addDependency = useCallback(
    (fromLessonId: number, toLessonId: number) => {
      pushToUndoStack();

      setEditState((prev) => ({
        ...prev,
        addedDependencies: [...prev.addedDependencies, { from: fromLessonId, to: toLessonId }],
      }));
    },
    [pushToUndoStack]
  );

  const removeDependency = useCallback(
    (dependencyId: number) => {
      pushToUndoStack();

      setEditState((prev) => ({
        ...prev,
        removedDependencies: new Set([...prev.removedDependencies, dependencyId]),
      }));
    },
    [pushToUndoStack]
  );

  const saveChanges = useCallback(async () => {
    if (!graph) return;

    // Save position changes
    if (editState.modifiedPositions.size > 0) {
      const updates = Array.from(editState.modifiedPositions.entries()).map(
        ([graphLessonId, position]) => ({
          graph_lesson_id: graphLessonId,
          position_x: position.x,
          position_y: position.y,
        })
      );

      await batchUpdateMutation.mutateAsync({
        graphId: graph.id,
        updates,
      });
    }

    // Remove lessons
    for (const graphLessonId of editState.removedLessons) {
      await removeLessonMutation.mutateAsync({
        graphId: graph.id,
        graphLessonId,
      });
    }

    // Add dependencies
    for (const dep of editState.addedDependencies) {
      await addDependencyMutation.mutateAsync({
        graphId: graph.id,
        fromLessonId: dep.from,
        toLessonId: dep.to,
      });
    }

    // Remove dependencies
    for (const depId of editState.removedDependencies) {
      // Find which lesson this dependency belongs to
      const dependency = graph.dependencies.find((d) => d.id === depId);
      if (dependency) {
        await removeDependencyMutation.mutateAsync({
          graphId: graph.id,
          lessonId: dependency.from_lesson,
          dependencyId: depId,
        });
      }
    }

    // Refetch graph
    await refetchGraph();

    // Reset edit state
    setEditState({
      modifiedPositions: new Map(),
      addedLessons: new Set(),
      removedLessons: new Set(),
      addedDependencies: [],
      removedDependencies: new Set(),
    });
    setUndoStack([]);
    setRedoStack([]);
  }, [
    graph,
    editState,
    batchUpdateMutation,
    removeLessonMutation,
    addDependencyMutation,
    removeDependencyMutation,
    refetchGraph,
  ]);

  const cancelChanges = useCallback(() => {
    setEditState({
      modifiedPositions: new Map(),
      addedLessons: new Set(),
      removedLessons: new Set(),
      addedDependencies: [],
      removedDependencies: new Set(),
    });
    setUndoStack([]);
    setRedoStack([]);
  }, []);

  const undo = useCallback(() => {
    if (undoStack.length === 0) return;

    const previousState = undoStack[undoStack.length - 1];
    setRedoStack((prev) => [...prev, editState]);
    setEditState(previousState);
    setUndoStack((prev) => prev.slice(0, -1));
  }, [undoStack, editState]);

  const redo = useCallback(() => {
    if (redoStack.length === 0) return;

    const nextState = redoStack[redoStack.length - 1];
    setUndoStack((prev) => [...prev, editState]);
    setEditState(nextState);
    setRedoStack((prev) => prev.slice(0, -1));
  }, [redoStack, editState]);

  return {
    // Data
    students,
    selectedStudent,
    graph,
    availableLessons,

    // Loading states
    isLoadingStudents,
    isLoadingGraph,
    isLoadingLessons,
    isSaving:
      addLessonMutation.isPending ||
      batchUpdateMutation.isPending ||
      removeLessonMutation.isPending ||
      addDependencyMutation.isPending ||
      removeDependencyMutation.isPending,

    // Error states
    studentsError,
    graphError,
    lessonsError,

    // Edit state
    editState,
    hasUnsavedChanges,

    // Actions
    selectStudent,
    addLesson,
    removeLesson,
    updateLessonPosition,
    addDependency,
    removeDependency,
    saveChanges,
    cancelChanges,
    undo,
    redo,

    // Undo/Redo
    canUndo: undoStack.length > 0,
    canRedo: redoStack.length > 0,
  };
};
