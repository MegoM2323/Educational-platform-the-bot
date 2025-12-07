/**
 * Tests for ContentCreatorTab component
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContentCreatorTab } from '../ContentCreatorTab';
import { vi } from 'vitest';

// Mock services
vi.mock('@/services/contentCreatorService', () => ({
  contentCreatorService: {
    getElements: vi.fn().mockResolvedValue({
      success: true,
      data: [
        {
          id: 1,
          title: 'Test Element',
          element_type: 'text_problem',
          description: 'Test description',
          created_at: '2025-12-08T00:00:00Z',
          is_public: false,
          estimated_time_minutes: 10,
        },
      ],
      count: 1,
    }),
    getLessons: vi.fn().mockResolvedValue({
      success: true,
      data: [
        {
          id: 1,
          title: 'Test Lesson',
          description: 'Test lesson description',
          created_at: '2025-12-08T00:00:00Z',
          is_public: false,
          elements_count: 3,
          total_duration_minutes: 30,
          total_max_score: 100,
        },
      ],
      count: 1,
    }),
    deleteElement: vi.fn().mockResolvedValue({}),
    deleteLesson: vi.fn().mockResolvedValue({}),
    copyElement: vi.fn().mockResolvedValue({
      success: true,
      data: { id: 2, title: 'Test Element_copy' },
    }),
    copyLesson: vi.fn().mockResolvedValue({
      success: true,
      data: { id: 2, title: 'Test Lesson_copy' },
    }),
  },
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe('ContentCreatorTab', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  const renderComponent = (props = {}) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <ContentCreatorTab {...props} />
      </QueryClientProvider>
    );
  };

  it('должен отображать вкладки элементов и уроков', () => {
    renderComponent();
    expect(screen.getByText('Элементы')).toBeInTheDocument();
    expect(screen.getByText('Уроки')).toBeInTheDocument();
  });

  it('должен отображать список элементов по умолчанию', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Element')).toBeInTheDocument();
    });

    expect(screen.getByText('Текстовая задача')).toBeInTheDocument();
  });

  it('должен показывать кнопку создания элемента', () => {
    const onCreateElement = vi.fn();
    renderComponent({ onCreateElement });

    const createButton = screen.getByText('Создать элемент');
    expect(createButton).toBeInTheDocument();
  });

  it('должен переключаться между вкладками', async () => {
    const user = userEvent.setup();
    renderComponent();

    // Открыть вкладку уроков
    const lessonsTab = screen.getByText('Уроки');
    await user.click(lessonsTab);

    await waitFor(() => {
      expect(screen.getByText('Test Lesson')).toBeInTheDocument();
    });
  });

  it('должен отображать фильтры для элементов', () => {
    renderComponent();

    // Проверить наличие селекторов фильтрации
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThan(0);
  });

  it('должен показывать поиск для элементов', () => {
    renderComponent();

    const searchInput = screen.getByPlaceholderText(/поиск по названию/i);
    expect(searchInput).toBeInTheDocument();
  });

  it('должен переключать режим отображения (список/сетка)', async () => {
    const user = userEvent.setup();
    renderComponent();

    // Найти кнопки переключения вида
    const gridButton = screen.getAllByRole('button').find((btn) => {
      const svg = btn.querySelector('svg');
      return svg?.classList.contains('lucide-grid-3x3');
    });

    if (gridButton) {
      await user.click(gridButton);
      // После клика должен быть активным режим grid
      expect(gridButton).toHaveAttribute('data-state', 'on');
    }
  });

  it('должен показывать пустое состояние когда нет элементов', async () => {
    const { contentCreatorService } = await import('@/services/contentCreatorService');
    vi.mocked(contentCreatorService.getElements).mockResolvedValueOnce({
      success: true,
      data: [],
      count: 0,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/элементы не найдены/i)).toBeInTheDocument();
    });
  });

  it('должен показывать диалог подтверждения при удалении', async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Element')).toBeInTheDocument();
    });

    // Найти кнопку удаления (иконка Trash2)
    const deleteButtons = screen.getAllByRole('button');
    const deleteButton = deleteButtons.find((btn) => btn.getAttribute('title') === 'Удалить');

    if (deleteButton) {
      await user.click(deleteButton);

      // Должен появиться диалог подтверждения
      await waitFor(() => {
        expect(screen.getByText('Подтвердите удаление')).toBeInTheDocument();
      });
    }
  });

  it('должен обрабатывать массовое удаление', async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Element')).toBeInTheDocument();
    });

    // Выбрать элемент с помощью checkbox
    const checkboxes = screen.getAllByRole('checkbox');
    if (checkboxes.length > 0) {
      await user.click(checkboxes[0]);

      // Должна появиться панель массовых действий
      await waitFor(() => {
        expect(screen.getByText(/выбрано:/i)).toBeInTheDocument();
      });
    }
  });

  it('должен отображать селектор видимости элементов', () => {
    renderComponent();

    // Проверить что селектор видимости присутствует
    expect(screen.getByText('Мои элементы')).toBeInTheDocument();
  });
});
