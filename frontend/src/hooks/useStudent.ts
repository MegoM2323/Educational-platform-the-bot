import { useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { studentAPI, StudentSubject, SubjectMaterial, SubmissionResponse, FeedbackItem } from '@/integrations/api/student';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { errorLoggingService } from '@/services/errorLoggingService';

export const useStudentDashboard = () => {
  return useQuery({
    queryKey: ['student-dashboard'],
    queryFn: async () => {
      const response = await unifiedAPI.getStudentDashboard();
      if (response.error) {
        throw new Error(response.error);
      }
      return response.data;
    },
    staleTime: 60000, // 1 minute
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    retry: (failureCount) => {
      // Maximum 5 retry attempts
      if (failureCount >= 5) return false;
      return true;
    },
    retryDelay: (attemptIndex) => {
      // Exponential backoff: 1s, 2s, 4s, 8s, 16s (capped at 30s)
      return Math.min(1000 * 2 ** attemptIndex, 30000);
    },
  });
};

export const useStudentSubjects = () => {
  return useQuery<StudentSubject[]>({
    queryKey: ['student-subjects'],
    queryFn: () => studentAPI.getSubjects(),
    staleTime: 60000,
  });
};

export const useSubjectMaterials = (subjectId?: number) => {
  return useQuery<SubjectMaterial[]>({
    queryKey: ['student-subject-materials', subjectId],
    queryFn: () => studentAPI.getSubjectMaterials(subjectId!),
    enabled: !!subjectId,
    staleTime: 30000,
  });
};

export const useSubmitHomework = (materialId: number) => {
  const qc = useQueryClient();
  return useMutation<SubmissionResponse, Error, FormData>({
    mutationFn: (formData) => studentAPI.submitHomework(materialId, formData),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['student-submissions'] });
    },
  });
};

export const useStudentSubmissions = () => {
  return useQuery<SubmissionResponse[]>({
    queryKey: ['student-submissions'],
    queryFn: () => studentAPI.getSubmissions(),
    staleTime: 30000,
  });
};

export const useSubmissionFeedback = (submissionId?: number) => {
  return useQuery<FeedbackItem>({
    queryKey: ['submission-feedback', submissionId],
    queryFn: () => studentAPI.getFeedback(submissionId!),
    enabled: !!submissionId,
    staleTime: 30000,
  });
};

export const useStudentDashboardRealTime = (userId: string | number | undefined) => {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      const eventTypes = [
        'new_assignment',
        'grade_posted',
        'material_added',
        'progress_updated',
        'tutor_message',
      ];

      if (eventTypes.includes(data.type)) {
        queryClient.invalidateQueries({ queryKey: ['student-dashboard'] });
        queryClient.invalidateQueries({ queryKey: ['student-submissions'] });
        queryClient.invalidateQueries({ queryKey: ['student-subjects'] });
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      errorLoggingService.logError({
        level: 'error',
        category: 'websocket',
        message: 'Failed to parse WebSocket message',
        stack: error.stack,
        context: { error: error.message },
      });
    }
  }, [queryClient]);

  const connect = useCallback(() => {
    if (!userId) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/dashboard/${userId}/`;

    try {
      if (wsRef.current) {
        wsRef.current.close();
      }

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        reconnectAttemptsRef.current = 0;
      };

      wsRef.current.onmessage = handleMessage;

      wsRef.current.onerror = (event) => {
        const error = event instanceof Error ? event : new Error('WebSocket error');
        errorLoggingService.logError({
          level: 'error',
          category: 'websocket',
          message: 'WebSocket connection error',
          stack: error.stack,
          context: { url: wsUrl },
        });
      };

      wsRef.current.onclose = () => {
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      errorLoggingService.logError({
        level: 'error',
        category: 'websocket',
        message: 'Failed to establish WebSocket connection',
        stack: error.stack,
        context: { userId, error: error.message },
      });
    }
  }, [userId, handleMessage]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);
};
