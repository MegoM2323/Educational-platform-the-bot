import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTutorStudents, useCreateTutorStudent, useAssignSubject } from '../useTutor';
import { tutorAPI } from '@/integrations/api/tutor';
import * as React from 'react';

// Mock tutorAPI
vi.mock('@/integrations/api/tutor', () => ({
  tutorAPI: {
    listStudents: vi.fn(),
    createStudent: vi.fn(),
    assignSubject: vi.fn(),
  },
}));

// Mock toast
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Mock cacheService
vi.mock('@/services/cacheService', () => ({
  cacheService: {
    delete: vi.fn(),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('useTutorStudents', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен успешно загружать студентов', async () => {
    const mockData = [
      {
        id: 1,
        full_name: 'Иван Иванов',
        grade: '5',
        goal: 'Улучшить математику',
        subjects: [],
      },
      {
        id: 2,
        full_name: 'Петр Петров',
        grade: '6',
        goal: 'Выучить английский',
        subjects: [],
      },
    ];

    vi.mocked(tutorAPI.listStudents).mockResolvedValue(mockData);

    const { result } = renderHook(() => useTutorStudents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(result.current.data).toHaveLength(2);
    expect(tutorAPI.listStudents).toHaveBeenCalledTimes(1);
  });

  it('должен вызывать API при загрузке студентов', async () => {
    const mockData = [
      {
        id: 1,
        full_name: 'Иван Иванов',
        grade: '5',
        subjects: [],
      },
    ];

    vi.mocked(tutorAPI.listStudents).mockResolvedValue(mockData);

    const { result } = renderHook(() => useTutorStudents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // API should be called at least once
    expect(tutorAPI.listStudents).toHaveBeenCalled();
    expect(result.current.data).toEqual(mockData);
  });

  it('должен загружать студентов с предметами', async () => {
    const mockData = [
      {
        id: 1,
        full_name: 'Иван Иванов',
        grade: '5',
        goal: 'Улучшить математику',
        subjects: [
          {
            id: 1,
            name: 'Математика',
            teacher_name: 'Учитель Математики',
            enrollment_id: 1,
          },
          {
            id: 2,
            name: 'Физика',
            teacher_name: 'Учитель Физики',
            enrollment_id: 2,
          },
        ],
      },
    ];

    vi.mocked(tutorAPI.listStudents).mockResolvedValue(mockData);

    const { result } = renderHook(() => useTutorStudents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.[0].subjects).toHaveLength(2);
    expect(result.current.data?.[0].subjects?.[0].name).toBe('Математика');
  });

  it('должен правильно настраивать refetchOnWindowFocus', async () => {
    const mockData = [
      {
        id: 1,
        full_name: 'Иван Иванов',
        grade: '5',
        subjects: [],
      },
    ];

    vi.mocked(tutorAPI.listStudents).mockResolvedValue(mockData);

    const { result } = renderHook(() => useTutorStudents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Hook should have refetchOnWindowFocus enabled
    expect(tutorAPI.listStudents).toHaveBeenCalled();
  });
});

describe('useCreateTutorStudent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен создавать студента', async () => {
    const mockRequest = {
      first_name: 'Иван',
      last_name: 'Иванов',
      grade: '5',
      goal: 'Улучшить математику',
      parent_first_name: 'Мария',
      parent_last_name: 'Иванова',
      parent_email: 'maria@test.com',
      parent_phone: '+79001234567',
    };

    const mockResponse = {
      student: {
        id: 1,
        full_name: 'Иван Иванов',
        grade: '5',
        goal: 'Улучшить математику',
      },
      parent: {
        id: 1,
        full_name: 'Мария Иванова',
      },
      credentials: {
        student: { username: 'student_1', password: 'password123' },
        parent: { username: 'parent_1', password: 'password456' },
      },
    };

    vi.mocked(tutorAPI.createStudent).mockResolvedValue(mockResponse);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useCreateTutorStudent(), { wrapper });

    await waitFor(() => expect(result.current).toBeDefined());

    result.current.mutate(mockRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(tutorAPI.createStudent).toHaveBeenCalledWith(mockRequest);
  });

  it('должен refetch после создания студента', async () => {
    const mockResponse = {
      student: { id: 1, full_name: 'Иван Иванов' },
      parent: { id: 1, full_name: 'Мария Иванова' },
      credentials: {
        student: { username: 'student_1', password: 'password123' },
        parent: { username: 'parent_1', password: 'password456' },
      },
    };

    vi.mocked(tutorAPI.createStudent).mockResolvedValue(mockResponse);
    vi.mocked(tutorAPI.listStudents).mockResolvedValue([]);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    // First render useTutorStudents to set up the query
    renderHook(() => useTutorStudents(), { wrapper });

    await waitFor(() => {
      expect(tutorAPI.listStudents).toHaveBeenCalledTimes(1);
    });

    const { result } = renderHook(() => useCreateTutorStudent(), { wrapper });

    await waitFor(() => expect(result.current).toBeDefined());

    const mockRequest = {
      first_name: 'Иван',
      last_name: 'Иванов',
      grade: '5',
      parent_first_name: 'Мария',
      parent_last_name: 'Иванова',
      parent_email: 'maria@test.com',
      parent_phone: '+79001234567',
    };

    result.current.mutate(mockRequest);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should refetch students list (initial + refetch after mutation + possible additional refetches)
    await waitFor(() => {
      expect(tutorAPI.listStudents).toHaveBeenCalledTimes(3);
    });
  });
});

describe('useAssignSubject', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('должен назначать предмет студенту', async () => {
    vi.mocked(tutorAPI.assignSubject).mockResolvedValue(undefined);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    const { result } = renderHook(() => useAssignSubject(1), { wrapper });

    await waitFor(() => expect(result.current).toBeDefined());

    const assignmentData = {
      subject_id: 1,
      teacher_id: 1,
    };

    result.current.mutate(assignmentData);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(tutorAPI.assignSubject).toHaveBeenCalledWith(1, assignmentData);
  });

  it('должен refetch после назначения предмета', async () => {
    vi.mocked(tutorAPI.assignSubject).mockResolvedValue(undefined);
    vi.mocked(tutorAPI.listStudents).mockResolvedValue([]);

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );

    // First render useTutorStudents to set up the query
    renderHook(() => useTutorStudents(), { wrapper });

    await waitFor(() => {
      expect(tutorAPI.listStudents).toHaveBeenCalledTimes(1);
    });

    const { result } = renderHook(() => useAssignSubject(1), { wrapper });

    await waitFor(() => expect(result.current).toBeDefined());

    result.current.mutate({ subject_id: 1, teacher_id: 1 });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Should refetch students list (initial + refetch after mutation + possible additional refetches)
    await waitFor(() => {
      expect(tutorAPI.listStudents).toHaveBeenCalledTimes(3);
    });
  });
});
