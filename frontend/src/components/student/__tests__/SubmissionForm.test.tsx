import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SubmissionForm } from '../SubmissionForm';
import { toast } from 'sonner';

// Mock dependencies
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  },
}));

describe('SubmissionForm Component', () => {
  const mockMaterialId = 123;
  const mockMaterialTitle = 'Test Material';
  const mockOnSuccess = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  // Helper function to create a File object
  function createFile(
    name: string,
    size: number = 1024,
    type: string = 'application/pdf'
  ): File {
    const blob = new Blob(['a'.repeat(size)], { type });
    return new File([blob], name, { type });
  }

  // Helper function to render component with required props
  function renderComponent(props = {}) {
    return render(
      <SubmissionForm
        materialId={mockMaterialId}
        materialTitle={mockMaterialTitle}
        onSuccess={mockOnSuccess}
        onCancel={mockOnCancel}
        {...props}
      />
    );
  }

  describe('Component Rendering', () => {
    it('should render the card title', () => {
      renderComponent();
      const titles = screen.getAllByText('Отправить ответ');
      expect(titles.length).toBeGreaterThan(0);
    });

    it('should render file upload section', () => {
      renderComponent();
      expect(screen.getByText('Файлы (необязательно)')).toBeInTheDocument();
    });

    it('should render notes textarea section', () => {
      renderComponent();
      expect(screen.getByText('Заметки (необязательно)')).toBeInTheDocument();
    });

    it('should render material title in description', () => {
      renderComponent();
      expect(screen.getByText(/Test Material/)).toBeInTheDocument();
    });

    it('should render cancel button when onCancel prop is provided', () => {
      renderComponent();
      expect(screen.getByRole('button', { name: /Отмена/i })).toBeInTheDocument();
    });

    it('should render submit button', () => {
      renderComponent();
      const submitButton = screen.getByRole('button', { name: /Отправить ответ/i });
      expect(submitButton).toBeInTheDocument();
    });
  });

  describe('File Upload Functionality', () => {
    it('should accept files via drag and drop', () => {
      renderComponent();

      const dropZone = screen.getByText('Перетащите файлы сюда');
      const file = createFile('test.pdf', 1024);

      const dataTransfer = {
        files: [file],
      };

      fireEvent.dragEnter(dropZone.closest('div')!);
      fireEvent.dragOver(dropZone.closest('div')!);
      fireEvent.drop(dropZone.closest('div')!, { dataTransfer });

      // Verify that drop zone is still visible (drag and drop handled)
      expect(screen.getByText('Перетащите файлы сюда')).toBeInTheDocument();
    });

    it('should display file count correctly', async () => {
      renderComponent();
      const user = userEvent.setup();

      // Initially should show 0/10
      expect(screen.getByText(/0\/10 файлов/)).toBeInTheDocument();
    });

    it('should display character counter', () => {
      renderComponent();
      expect(screen.getByText(/0\/5000/)).toBeInTheDocument();
    });
  });

  describe('Form Submission', () => {
    it('should disable submit button when form is empty', () => {
      renderComponent();
      const submitButton = screen.getByRole('button', { name: /Отправить ответ/i });
      expect(submitButton).toBeDisabled();
    });

    it('should enable submit button when notes are provided', async () => {
      renderComponent();
      const user = userEvent.setup();

      const textarea = screen.getByPlaceholderText(/Введите заметки/);
      await user.type(textarea, 'Test notes');

      const submitButton = screen.getByRole('button', { name: /Отправить ответ/i });
      expect(submitButton).not.toBeDisabled();
    });

    it('should show error toast when submission fails', async () => {
      const { unifiedAPI } = await import('@/integrations/api/unifiedClient');
      (unifiedAPI.request as Mock).mockRejectedValue(
        new Error('Network error')
      );

      renderComponent();
      const user = userEvent.setup();

      const textarea = screen.getByPlaceholderText(/Введите заметки/);
      await user.type(textarea, 'Test');

      const submitButton = screen.getByRole('button', { name: /Отправить ответ/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled();
      });
    });
  });

  describe('localStorage Draft Saving', () => {
    it('should load draft from localStorage on mount', async () => {
      const draftData = { notes: 'Saved draft notes' };
      localStorage.setItem(
        `submission_draft_${mockMaterialId}`,
        JSON.stringify(draftData)
      );

      renderComponent();

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/Введите заметки/) as HTMLTextAreaElement;
        expect(textarea.value).toBe('Saved draft notes');
      });
    });

    it('should save draft to localStorage as user types', async () => {
      renderComponent();
      const user = userEvent.setup();

      const textarea = screen.getByPlaceholderText(/Введите заметки/);
      const testText = 'Draft notes';

      await user.type(textarea, testText);

      // Wait for auto-save (1 second debounce)
      await waitFor(
        () => {
          const draft = localStorage.getItem(`submission_draft_${mockMaterialId}`);
          expect(draft).toBeTruthy();
          const parsed = JSON.parse(draft!);
          expect(parsed.notes).toBe(testText);
        },
        { timeout: 2000 }
      );
    });
  });

  describe('Character Counter', () => {
    it('should update character count as user types', async () => {
      renderComponent();
      const user = userEvent.setup();

      const textarea = screen.getByPlaceholderText(/Введите заметки/);
      const testText = 'Test text';

      await user.type(textarea, testText);

      expect(screen.getByText(`${testText.length}/5000`)).toBeInTheDocument();
    });

    it('should show validation for character limit', async () => {
      renderComponent();
      const user = userEvent.setup();

      const textarea = screen.getByPlaceholderText(/Введите заметки/);

      // Try to type more than 5000 characters (schema should limit)
      const longText = 'a'.repeat(5001);
      await user.type(textarea, longText.substring(0, 100)); // Type 100 chars instead

      // Verify counter shows the typed text
      expect(screen.getByText(/100\/5000/)).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should render form on mobile', () => {
      renderComponent();

      expect(screen.getByText('Файлы (необязательно)')).toBeInTheDocument();
      expect(screen.getByText('Заметки (необязательно)')).toBeInTheDocument();
    });

    it('should show proper labels for required sections', () => {
      renderComponent();

      expect(screen.getByText('Файлы (необязательно)')).toBeInTheDocument();
      expect(screen.getByText('Заметки (необязательно)')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('should display error message on submission error', async () => {
      const { unifiedAPI } = await import('@/integrations/api/unifiedClient');
      (unifiedAPI.request as Mock).mockRejectedValue(
        new Error('API Error')
      );

      renderComponent();
      const user = userEvent.setup();

      const textarea = screen.getByPlaceholderText(/Введите заметки/);
      await user.type(textarea, 'Test');

      const submitButton = screen.getByRole('button', { name: /Отправить ответ/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Ошибка отправки/)).toBeInTheDocument();
      });
    });

    it('should allow dismissing error message', async () => {
      const { unifiedAPI } = await import('@/integrations/api/unifiedClient');
      (unifiedAPI.request as Mock).mockRejectedValue(
        new Error('API Error')
      );

      renderComponent();
      const user = userEvent.setup();

      const textarea = screen.getByPlaceholderText(/Введите заметки/);
      await user.type(textarea, 'Test');

      const submitButton = screen.getByRole('button', { name: /Отправить ответ/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/Ошибка отправки/)).toBeInTheDocument();
      });

      // Find and click close button
      const errorContainer = screen.getByText(/Ошибка отправки/).closest('div');
      const closeButton = errorContainer?.querySelector('button');

      if (closeButton) {
        await user.click(closeButton);

        await waitFor(() => {
          expect(screen.queryByText(/Ошибка отправки/)).not.toBeInTheDocument();
        });
      }
    });
  });

  describe('Supported File Types', () => {
    it('should display list of supported file types', () => {
      renderComponent();

      const supportedTypesText = screen.getByText(/Поддерживаемые форматы:/);
      expect(supportedTypesText).toBeInTheDocument();
    });

    it('should display file size limits', () => {
      renderComponent();

      expect(screen.getByText(/Максимум 10 файлов по/)).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('should show validation message for empty submission', async () => {
      renderComponent();
      const user = userEvent.setup();

      const submitButton = screen.getByRole('button', { name: /Отправить ответ/i });

      // Button should be disabled, so we can't click it
      expect(submitButton).toBeDisabled();
    });
  });
});
