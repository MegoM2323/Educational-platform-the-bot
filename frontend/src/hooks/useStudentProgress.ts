/**
 * Custom hook for Teacher Progress Viewer (T605)
 * Управляет состоянием просмотра прогресса студентов
 */
import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  progressViewerAPI,
  type StudentBasic,
  type StudentProgressOverview,
  type LessonProgressDetail,
  type ElementProgressDetail,
} from '@/integrations/api/progressViewerAPI';

export interface UseStudentProgressOptions {
  graphId?: number;
  studentId?: number;
  subjectId?: number;
  autoRefresh?: boolean;
  refreshInterval?: number; // мс
}

export interface UseStudentProgressReturn {
  // Данные
  students: StudentBasic[];
  selectedStudent: StudentBasic | null;
  graphId: number | null;
  graphProgress: StudentProgressOverview | null;
  lessonProgress: LessonProgressDetail[];
  selectedLesson: LessonProgressDetail | null;
  elementDetails: ElementProgressDetail[];

  // Состояния загрузки
  isLoadingStudents: boolean;
  isLoadingProgress: boolean;
  isLoadingLessons: boolean;
  isLoadingElements: boolean;

  // Ошибки
  studentsError: Error | null;
  progressError: Error | null;
  lessonsError: Error | null;
  elementsError: Error | null;

  // Действия
  selectStudent: (student: StudentBasic) => void;
  selectLesson: (lesson: LessonProgressDetail) => void;
  refreshProgress: () => void;
  exportProgress: () => Promise<void>;

  // Последнее обновление
  lastUpdated: Date | null;
}

export const useStudentProgress = (
  options: UseStudentProgressOptions = {}
): UseStudentProgressReturn => {
  const {
    graphId: initialGraphId,
    studentId: initialStudentId,
    subjectId,
    autoRefresh = false,
    refreshInterval = 30000, // 30 секунд
  } = options;

  const [selectedStudent, setSelectedStudent] = useState<StudentBasic | null>(null);
  const [selectedLesson, setSelectedLesson] = useState<LessonProgressDetail | null>(null);
  const [graphId, setGraphId] = useState<number | null>(initialGraphId || null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Загрузка списка студентов
  const {
    data: students = [],
    isLoading: isLoadingStudents,
    error: studentsError,
  } = useQuery<StudentBasic[], Error>({
    queryKey: ['teacher', 'students'],
    queryFn: progressViewerAPI.getTeacherStudents,
    staleTime: 5 * 60 * 1000, // 5 минут
  });

  // Загрузка graph_id при выборе студента и предмета
  const { data: graphData } = useQuery({
    queryKey: ['knowledge-graph', 'graph', selectedStudent?.id, subjectId],
    queryFn: () =>
      progressViewerAPI.getOrCreateGraph(selectedStudent!.id, subjectId!),
    enabled: !!selectedStudent && !!subjectId,
    staleTime: 10 * 60 * 1000, // 10 минут
  });

  // Обновляем graphId при получении данных
  useEffect(() => {
    if (graphData?.id) {
      setGraphId(graphData.id);
    }
  }, [graphData]);

  // Загрузка обзора прогресса по графу
  const {
    data: progressData,
    isLoading: isLoadingProgress,
    error: progressError,
    refetch: refetchProgress,
  } = useQuery({
    queryKey: ['knowledge-graph', 'progress', graphId],
    queryFn: async () => {
      const result = await progressViewerAPI.getGraphProgress(graphId!);
      setLastUpdated(new Date());
      return result;
    },
    enabled: !!graphId,
    refetchInterval: autoRefresh ? refreshInterval : false,
    staleTime: autoRefresh ? refreshInterval : 60000,
  });

  const graphProgress = progressData?.data?.student || null;

  // Загрузка детального прогресса по урокам
  const {
    data: lessonsData,
    isLoading: isLoadingLessons,
    error: lessonsError,
    refetch: refetchLessons,
  } = useQuery({
    queryKey: ['knowledge-graph', 'lessons', graphId, selectedStudent?.id],
    queryFn: async () => {
      const result = await progressViewerAPI.getStudentDetailedProgress(
        graphId!,
        selectedStudent!.id
      );
      return result;
    },
    enabled: !!graphId && !!selectedStudent,
    refetchInterval: autoRefresh ? refreshInterval : false,
    staleTime: autoRefresh ? refreshInterval : 30000,
  });

  const lessonProgress = lessonsData?.data?.lessons || [];

  // Загрузка деталей урока с элементами
  const {
    data: elementsData,
    isLoading: isLoadingElements,
    error: elementsError,
  } = useQuery({
    queryKey: [
      'knowledge-graph',
      'lesson-elements',
      graphId,
      selectedStudent?.id,
      selectedLesson?.lesson_id,
    ],
    queryFn: async () => {
      const result = await progressViewerAPI.getLessonDetail(
        graphId!,
        selectedStudent!.id,
        selectedLesson!.lesson_id
      );
      return result;
    },
    enabled: !!graphId && !!selectedStudent && !!selectedLesson,
    staleTime: 30000,
  });

  const elementDetails = elementsData?.data?.elements || [];

  // Выбор студента
  const selectStudent = useCallback((student: StudentBasic) => {
    setSelectedStudent(student);
    setSelectedLesson(null); // Сбросить выбранный урок
  }, []);

  // Выбор урока
  const selectLesson = useCallback((lesson: LessonProgressDetail) => {
    setSelectedLesson(lesson);
  }, []);

  // Обновить прогресс вручную
  const refreshProgress = useCallback(() => {
    refetchProgress();
    refetchLessons();
    setLastUpdated(new Date());
  }, [refetchProgress, refetchLessons]);

  // Экспорт прогресса в CSV
  const exportProgress = useCallback(async () => {
    if (!graphId) {
      throw new Error('No graph selected');
    }

    const blob = await progressViewerAPI.exportProgress(graphId);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `student_progress_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }, [graphId]);

  // Автовыбор первого студента если задан initialStudentId
  useEffect(() => {
    if (initialStudentId && students.length > 0 && !selectedStudent) {
      const student = students.find((s) => s.id === initialStudentId);
      if (student) {
        setSelectedStudent(student);
      }
    }
  }, [initialStudentId, students, selectedStudent]);

  return {
    // Данные
    students,
    selectedStudent,
    graphId,
    graphProgress,
    lessonProgress,
    selectedLesson,
    elementDetails,

    // Состояния загрузки
    isLoadingStudents,
    isLoadingProgress,
    isLoadingLessons,
    isLoadingElements,

    // Ошибки
    studentsError: studentsError as Error | null,
    progressError: progressError as Error | null,
    lessonsError: lessonsError as Error | null,
    elementsError: elementsError as Error | null,

    // Действия
    selectStudent,
    selectLesson,
    refreshProgress,
    exportProgress,

    // Последнее обновление
    lastUpdated,
  };
};
