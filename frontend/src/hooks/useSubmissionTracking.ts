import { useEffect, useState, useCallback } from 'react';

export interface SubmissionAttempt {
  id: string;
  startTime: number;
  endTime?: number;
  answers: Record<string, any>;
  files: File[];
  status: 'in_progress' | 'submitted' | 'failed';
}

export interface SubmissionTracking {
  assignmentId: number;
  currentAttempt: SubmissionAttempt | null;
  attempts: SubmissionAttempt[];
  totalTimeSpent: number;
  currentTimeSpent: number;
}

const STORAGE_KEY_PREFIX = 'submission-tracking-';

export const useSubmissionTracking = (assignmentId: number) => {
  const [tracking, setTracking] = useState<SubmissionTracking>({
    assignmentId,
    currentAttempt: null,
    attempts: [],
    totalTimeSpent: 0,
    currentTimeSpent: 0,
  });

  const storageKey = `${STORAGE_KEY_PREFIX}${assignmentId}`;

  // Load tracking data from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const data = JSON.parse(stored);
        setTracking(data);
      }
    } catch (error) {
      console.error('Error loading submission tracking:', error);
    }
  }, [assignmentId, storageKey]);

  // Update current time spent
  useEffect(() => {
    if (!tracking.currentAttempt) return;

    const interval = setInterval(() => {
      setTracking((prev) => ({
        ...prev,
        currentTimeSpent: Date.now() - prev.currentAttempt!.startTime,
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, [tracking.currentAttempt]);

  // Save tracking to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(tracking));
    } catch (error) {
      console.error('Error saving submission tracking:', error);
    }
  }, [tracking, storageKey]);

  const startAttempt = useCallback(() => {
    const newAttempt: SubmissionAttempt = {
      id: `${Date.now()}`,
      startTime: Date.now(),
      answers: {},
      files: [],
      status: 'in_progress',
    };

    setTracking((prev) => ({
      ...prev,
      currentAttempt: newAttempt,
      attempts: [...prev.attempts, newAttempt],
    }));
  }, []);

  const updateAnswer = useCallback((questionId: string | number, answer: any) => {
    setTracking((prev) => ({
      ...prev,
      currentAttempt: prev.currentAttempt
        ? {
          ...prev.currentAttempt,
          answers: {
            ...prev.currentAttempt.answers,
            [questionId]: answer,
          },
        }
        : null,
    }));
  }, []);

  const addFile = useCallback((file: File) => {
    setTracking((prev) => ({
      ...prev,
      currentAttempt: prev.currentAttempt
        ? {
          ...prev.currentAttempt,
          files: [...prev.currentAttempt.files, file],
        }
        : null,
    }));
  }, []);

  const removeFile = useCallback((fileName: string) => {
    setTracking((prev) => ({
      ...prev,
      currentAttempt: prev.currentAttempt
        ? {
          ...prev.currentAttempt,
          files: prev.currentAttempt.files.filter((f) => f.name !== fileName),
        }
        : null,
    }));
  }, []);

  const completeAttempt = useCallback((submitted = true) => {
    setTracking((prev) => {
      if (!prev.currentAttempt) return prev;

      const endedAttempt: SubmissionAttempt = {
        ...prev.currentAttempt,
        endTime: Date.now(),
        status: submitted ? 'submitted' : 'failed',
      };

      const timeSpent = (endedAttempt.endTime - endedAttempt.startTime) / 1000; // in seconds

      return {
        ...prev,
        currentAttempt: null,
        attempts: prev.attempts.map((a) => (a.id === endedAttempt.id ? endedAttempt : a)),
        totalTimeSpent: prev.totalTimeSpent + timeSpent,
        currentTimeSpent: 0,
      };
    });
  }, []);

  const clearTracking = useCallback(() => {
    setTracking({
      assignmentId,
      currentAttempt: null,
      attempts: [],
      totalTimeSpent: 0,
      currentTimeSpent: 0,
    });
    localStorage.removeItem(storageKey);
  }, [assignmentId, storageKey]);

  const formatTimeSpent = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    const parts = [];
    if (hours > 0) parts.push(`${hours}ч`);
    if (minutes > 0) parts.push(`${minutes}м`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}с`);

    return parts.join(' ');
  };

  return {
    tracking,
    startAttempt,
    updateAnswer,
    addFile,
    removeFile,
    completeAttempt,
    clearTracking,
    formatTimeSpent,
    currentTimeSpentFormatted: formatTimeSpent(tracking.currentTimeSpent / 1000),
    totalTimeSpentFormatted: formatTimeSpent(tracking.totalTimeSpent),
  };
};
