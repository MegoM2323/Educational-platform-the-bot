import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StudentMultiSelect } from '../StudentMultiSelect';
import { adminAPI } from '@/integrations/api/adminAPI';

vi.mock('@/integrations/api/adminAPI');

const mockStudents = [
  {
    id: 1,
    user: {
      id: 1,
      first_name: 'Alice',
      last_name: 'Johnson',
      email: 'alice@test.com',
      is_active: true,
    },
    grade: '10',
  },
  {
    id: 2,
    user: {
      id: 2,
      first_name: 'Bob',
      last_name: 'Smith',
      email: 'bob@test.com',
      is_active: true,
    },
    grade: '11',
  },
  {
    id: 3,
    user: {
      id: 3,
      first_name: 'Charlie',
      last_name: 'Brown',
      email: 'charlie@test.com',
      is_active: true,
    },
    grade: '9',
  },
];

describe('StudentMultiSelect', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (adminAPI.getStudents as any).mockResolvedValue({
      success: true,
      data: {
        count: mockStudents.length,
        results: mockStudents,
        next: null,
        previous: null,
      },
    });
  });

  describe('test_StudentMultiSelect_renders', () => {
    it('test_StudentMultiSelect_rendersComponent', async () => {
      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText(/Выбрано: 0 из 3/)).toBeInTheDocument();
      });
    });

    it('test_StudentMultiSelect_showsLoadingState', () => {
      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      expect(screen.getByText('Загрузка студентов...')).toBeInTheDocument();
    });

    it('test_StudentMultiSelect_displaysStudents', async () => {
      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
        expect(screen.getByText('Bob Smith')).toBeInTheDocument();
        expect(screen.getByText('Charlie Brown')).toBeInTheDocument();
      });
    });

    it('test_StudentMultiSelect_displaysGrades', async () => {
      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText('Класс: 10')).toBeInTheDocument();
        expect(screen.getByText('Класс: 11')).toBeInTheDocument();
        expect(screen.getByText('Класс: 9')).toBeInTheDocument();
      });
    });
  });

  describe('test_StudentMultiSelect_onChange', () => {
    it('test_StudentMultiSelect_callsOnChangeOnSelect', async () => {
      const user = userEvent.setup();
      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      });

      const checkbox = screen.getByLabelText(/Alice Johnson/);
      await user.click(checkbox);

      expect(mockOnChange).toHaveBeenCalledWith([1]);
    });

    it('test_StudentMultiSelect_callsOnChangeOnDeselect', async () => {
      const user = userEvent.setup();
      render(<StudentMultiSelect value={[1, 2]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getAllByText('Alice Johnson').length).toBeGreaterThan(0);
      });

      const checkbox = screen.getByLabelText(/Alice Johnson/);
      await user.click(checkbox);

      expect(mockOnChange).toHaveBeenCalledWith([2]);
    });

    it('test_StudentMultiSelect_multipleSelections', async () => {
      const user = userEvent.setup();
      const { rerender } = render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getAllByText('Alice Johnson').length).toBeGreaterThan(0);
      });

      const checkbox1 = screen.getByLabelText(/Alice Johnson/);
      await user.click(checkbox1);

      expect(mockOnChange).toHaveBeenCalledWith([1]);

      rerender(<StudentMultiSelect value={[1]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getAllByText('Bob Smith').length).toBeGreaterThan(0);
      });

      const checkbox2 = screen.getByLabelText(/Bob Smith/);
      await user.click(checkbox2);

      expect(mockOnChange).toHaveBeenLastCalledWith([1, 2]);
    });
  });

  describe('test_StudentMultiSelect_loadsOptions', () => {
    it('test_StudentMultiSelect_fetchesStudentsOnMount', async () => {
      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(adminAPI.getStudents).toHaveBeenCalledWith({
          is_active: true,
          page_size: 1000,
        });
      });
    });

    it('test_StudentMultiSelect_handlesEmptyResponse', async () => {
      (adminAPI.getStudents as any).mockResolvedValue({
        success: true,
        data: {
          count: 0,
          results: [],
          next: null,
          previous: null,
        },
      });

      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText('Студенты не найдены')).toBeInTheDocument();
      });
    });

    it('test_StudentMultiSelect_handlesLoadError', async () => {
      (adminAPI.getStudents as any).mockResolvedValue({
        success: false,
        error: 'Failed to load students',
      });

      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load students/)).toBeInTheDocument();
      });
    });

    it('test_StudentMultiSelect_handlesNetworkError', async () => {
      (adminAPI.getStudents as any).mockRejectedValue(new Error('Network error'));

      render(<StudentMultiSelect value={[]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText(/Network error/)).toBeInTheDocument();
      });
    });
  });

  describe('test_StudentMultiSelect_showsSelectedCount', () => {
    it('test_StudentMultiSelect_displaysSelectedCount', async () => {
      render(<StudentMultiSelect value={[1, 2]} onChange={mockOnChange} />);

      await waitFor(() => {
        expect(screen.getByText(/Выбрано: 2 из 3/)).toBeInTheDocument();
      });
    });

    it('test_StudentMultiSelect_showsSelectedBadges', async () => {
      render(<StudentMultiSelect value={[1, 3]} onChange={mockOnChange} />);

      await waitFor(() => {
        const aliceElements = screen.getAllByText('Alice Johnson');
        const charlieElements = screen.getAllByText('Charlie Brown');
        expect(aliceElements.length).toBeGreaterThanOrEqual(2); // badge + label
        expect(charlieElements.length).toBeGreaterThanOrEqual(2); // badge + label
      });
    });
  });

  describe('test_StudentMultiSelect_disabled', () => {
    it('test_StudentMultiSelect_disablesCheckboxes', async () => {
      render(<StudentMultiSelect value={[]} onChange={mockOnChange} disabled={true} />);

      await waitFor(() => {
        expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      });

      const checkbox = screen.getByLabelText(/Alice Johnson/);
      expect(checkbox).toBeDisabled();
    });
  });
});
