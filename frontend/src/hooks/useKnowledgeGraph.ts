import { useQuery, useQueryClient } from '@tanstack/react-query';
import { knowledgeGraphAPI, KnowledgeGraph } from '../integrations/api/knowledgeGraphAPI';

/**
 * Custom hook for fetching student's knowledge graph
 *
 * Features:
 * - Fetches graph data for current student and selected subject
 * - Handles loading, error, and empty states
 * - Refetches on subject change
 * - Caches with TanStack Query
 * - Provides manual refresh capability
 *
 * @param studentId - ID of the student
 * @param subjectId - ID of the subject (optional - if not provided, won't fetch)
 * @returns Query result with graph data, loading state, and refresh function
 */
export const useKnowledgeGraph = (studentId: number | null, subjectId: number | null) => {
  const queryClient = useQueryClient();

  const query = useQuery<KnowledgeGraph>({
    queryKey: ['knowledge-graph', studentId, subjectId],
    queryFn: async () => {
      if (!studentId || !subjectId) {
        throw new Error('Student ID and Subject ID are required');
      }
      return knowledgeGraphAPI.getStudentGraph(studentId, subjectId);
    },
    // Only fetch if both IDs are available
    enabled: !!studentId && !!subjectId,
    staleTime: 60000, // 1 minute
    retry: 2,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });

  // Manual refresh function
  const refreshGraph = () => {
    queryClient.invalidateQueries({ queryKey: ['knowledge-graph', studentId, subjectId] });
  };

  return {
    ...query,
    refreshGraph,
  };
};

/**
 * Hook for fetching student's subjects (for subject selector)
 */
export const useStudentSubjects = () => {
  return useQuery({
    queryKey: ['student-subjects'],
    queryFn: () => knowledgeGraphAPI.getStudentSubjects(),
    staleTime: 300000, // 5 minutes (subjects don't change often)
    retry: 2,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
  });
};

/**
 * Hook for fetching lesson progress from knowledge graph API
 * Note: Different from useLessonProgress in lesson viewer
 */
export const useGraphLessonProgress = (lessonId: number | null, studentId: number | null) => {
  return useQuery({
    queryKey: ['graph-lesson-progress', lessonId, studentId],
    queryFn: async () => {
      if (!lessonId || !studentId) {
        throw new Error('Lesson ID and Student ID are required');
      }
      return knowledgeGraphAPI.getLessonProgress(lessonId, studentId);
    },
    enabled: !!lessonId && !!studentId,
    staleTime: 30000, // 30 seconds (progress changes more frequently)
    retry: 2,
    refetchOnMount: true,
    refetchOnWindowFocus: false,
  });
};
