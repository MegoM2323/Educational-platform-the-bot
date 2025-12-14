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

export interface DeleteError {
  type: 'permission' | 'not_found' | 'validation' | 'network' | 'unknown';
  message: string;
  statusCode?: number;
}

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
  isDeleting: boolean;

  // Error states
  studentsError: Error | null;
  graphError: Error | null;
  lessonsError: Error | null;
  deleteError: DeleteError | null;

  // Edit state
  editState: EditState;
  hasUnsavedChanges: boolean;

  // Actions
  selectStudent: (student: Student | null) => void;
  refetchStudents: () => void;
  addLesson: (lessonId: number, x?: number, y?: number) => Promise<void>;
  removeLesson: (graphLessonId: number) => void;
  updateLessonPosition: (graphLessonId: number, x: number, y: number) => void;
  addDependency: (fromLessonId: number, toLessonId: number) => void;
  removeDependency: (dependencyId: number) => void;
  deleteLesson: (lessonId: number) => Promise<void>;
  deleteDependency: (dependencyId: number, fromId: number, toId: number) => Promise<void>;
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
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<DeleteError | null>(null);

  // Queries
  const {
    data: students = [],
    isLoading: isLoadingStudents,
    error: studentsError,
    refetch: refetchStudents,
  } = useQuery<Student[], Error>({
    queryKey: ['teacher-students'],
    queryFn: knowledgeGraphAPI.getTeacherStudents,
    staleTime: 60000, // 1 minute
    refetchOnMount: true,        // Fix F001 - Force fetch on mount
    refetchOnWindowFocus: false, // Prevent unnecessary refetches
    retry: 2,                    // Retry failed requests
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 5000),
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
  }, [students]); // Fix: Remove selectedStudent to prevent infinite loops

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

  // Helper to parse API errors
  const parseError = useCallback((error: unknown): DeleteError => {
    if (error instanceof Error) {
      const message = error.message.toLowerCase();

      if (message.includes('403') || message.includes('forbidden') || message.includes('прав')) {
        return { type: 'permission', message: error.message, statusCode: 403 };
      }
      if (message.includes('404') || message.includes('не найден')) {
        return { type: 'not_found', message: error.message, statusCode: 404 };
      }
      if (message.includes('400') || message.includes('validation') || message.includes('используется')) {
        return { type: 'validation', message: error.message, statusCode: 400 };
      }
      if (message.includes('network') || message.includes('сеть')) {
        return { type: 'network', message: error.message };
      }

      return { type: 'unknown', message: error.message };
    }

    return { type: 'unknown', message: 'Неизвестная ошибка' };
  }, []);

  // Delete lesson (T011)
  const deleteLesson = useCallback(
    async (lessonId: number): Promise<void> => {
      if (!graph) return;

      setIsDeleting(true);
      setDeleteError(null);

      try {
        // Call API - полное удаление урока
        await knowledgeGraphAPI.deleteLesson(graph.id, lessonId);

        // Успешное удаление - обновить локальное состояние
        // Удалить урок из graph.lessons (найти GraphLesson по lesson.id)
        const graphLessonToRemove = graph.lessons.find((gl) => gl.lesson.id === lessonId);

        if (graphLessonToRemove) {
          // Удалить GraphLesson из lessons
          queryClient.setQueryData<KnowledgeGraph | null>(
            ['knowledge-graph', selectedStudent?.id, subjectId],
            (oldGraph) => {
              if (!oldGraph) return null;

              return {
                ...oldGraph,
                lessons: oldGraph.lessons.filter((gl) => gl.lesson.id !== lessonId),
                dependencies: oldGraph.dependencies.filter(
                  (d) => d.from_lesson !== graphLessonToRemove.id && d.to_lesson !== graphLessonToRemove.id
                ),
              };
            }
          );

          // Push to undo stack AFTER successful deletion
          pushToUndoStack();
        }

        // Refetch graph to get updated state
        await refetchGraph();
      } catch (error) {
        // Handle error
        const parsedError = parseError(error);
        setDeleteError(parsedError);
        throw error; // Re-throw for caller to handle
      } finally {
        setIsDeleting(false);
      }
    },
    [graph, selectedStudent, subjectId, queryClient, pushToUndoStack, parseError, refetchGraph]
  );

  // Delete dependency (T011)
  const deleteDependency = useCallback(
    async (dependencyId: number, fromId: number, toId: number): Promise<void> => {
      if (!graph) return;

      setIsDeleting(true);
      setDeleteError(null);

      try {
        // Call API
        await knowledgeGraphAPI.deleteDependency(graph.id, toId, dependencyId);

        // Успешное удаление - обновить локальное состояние
        queryClient.setQueryData<KnowledgeGraph | null>(
          ['knowledge-graph', selectedStudent?.id, subjectId],
          (oldGraph) => {
            if (!oldGraph) return null;

            return {
              ...oldGraph,
              dependencies: oldGraph.dependencies.filter((d) => d.id !== dependencyId),
            };
          }
        );

        // Push to undo stack AFTER successful deletion
        pushToUndoStack();

        // Refetch to ensure consistency
        await refetchGraph();
      } catch (error) {
        // Handle error
        const parsedError = parseError(error);
        setDeleteError(parsedError);
        throw error; // Re-throw for caller to handle
      } finally {
        setIsDeleting(false);
      }
    },
    [graph, selectedStudent, subjectId, queryClient, pushToUndoStack, parseError, refetchGraph]
  );

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
    isDeleting,

    // Error states
    studentsError,
    graphError,
    lessonsError,
    deleteError,

    // Edit state
    editState,
    hasUnsavedChanges,

    // Actions
    selectStudent,
    refetchStudents,
    addLesson,
    removeLesson,
    updateLessonPosition,
    addDependency,
    removeDependency,
    deleteLesson,
    deleteDependency,
    saveChanges,
    cancelChanges,
    undo,
    redo,

    // Undo/Redo
    canUndo: undoStack.length > 0,
    canRedo: redoStack.length > 0,
  };
};
