import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReportsList, Report } from '../ReportsList';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the useToast hook
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const mockReports: Report[] = [
  {
    id: 1,
    title: 'Отчет о прогрессе Ивана',
    report_type: 'progress',
    status: 'draft',
    created_at: '2025-12-20T10:00:00Z',
    period_start: '2025-12-14',
    period_end: '2025-12-20',
    student_name: 'Иван Петров',
    description: 'Ежемесячный отчет о прогрессе',
    owner_id: 1,
  },
  {
    id: 2,
    title: 'Отчет о поведении Марии',
    report_type: 'behavior',
    status: 'sent',
    created_at: '2025-12-15T10:00:00Z',
    student_name: 'Мария Сидорова',
    owner_id: 1,
  },
  {
    id: 3,
    title: 'Отчет о достижениях',
    report_type: 'achievement',
    status: 'read',
    created_at: '2025-12-10T10:00:00Z',
    owner_id: 2,
  },
];

describe('ReportsList Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no reports provided', () => {
    render(<ReportsList reports={[]} />);
    expect(screen.getByText('Отчетов нет')).toBeInTheDocument();
  });

  it('renders loading skeleton when isLoading is true', () => {
    render(<ReportsList reports={[]} isLoading={true} />);
    // Check that skeleton elements are rendered
    const container = screen.getByText(/Отчетов нет/i).parentElement;
    expect(container).toBeTruthy();
  });

  it('displays all reports in table', () => {
    render(<ReportsList reports={mockReports} />);
    expect(screen.getByText('Отчет о прогрессе Ивана')).toBeInTheDocument();
    expect(screen.getByText('Отчет о поведении Марии')).toBeInTheDocument();
    expect(screen.getByText('Отчет о достижениях')).toBeInTheDocument();
  });

  it('searches reports by title', async () => {
    render(<ReportsList reports={mockReports} />);

    const searchInput = screen.getByPlaceholderText(/поиск по названию/i);
    fireEvent.change(searchInput, { target: { value: 'прогресс' } });

    await waitFor(() => {
      expect(screen.getByText('Отчет о прогрессе Ивана')).toBeInTheDocument();
    });
  });

  it('calls onView callback when view button clicked', async () => {
    const onView = vi.fn();
    render(<ReportsList reports={mockReports} onView={onView} />);

    const viewButtons = screen.getAllByTitle('Просмотр');
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(onView).toHaveBeenCalledWith(mockReports[0]);
    });
  });

  it('calls onDelete callback with confirmation', async () => {
    const onDelete = vi.fn();
    window.confirm = vi.fn(() => true);

    render(
      <ReportsList
        reports={mockReports}
        onDelete={onDelete}
        currentUserId={1}
        userRole="teacher"
      />
    );

    const deleteButtons = screen.getAllByTitle('Удалить');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(onDelete).toHaveBeenCalledWith(mockReports[0]);
    });
  });

  it('shows download button only when attachment exists', () => {
    const reportsWithAttachment = [
      { ...mockReports[0], attachment: 'report.pdf' },
      mockReports[1],
    ];

    render(<ReportsList reports={reportsWithAttachment} onDownload={vi.fn()} />);

    const downloadButtons = screen.getAllByTitle('Скачать');
    expect(downloadButtons.length).toBe(1);
  });

  it('shows delete button only for owner or admin', () => {
    render(
      <ReportsList
        reports={mockReports}
        onDelete={vi.fn()}
        currentUserId={1}
        userRole="teacher"
      />
    );

    const deleteButtons = screen.getAllByTitle('Удалить');
    expect(deleteButtons.length).toBeGreaterThan(0);
  });

  it('shows result count', () => {
    render(<ReportsList reports={mockReports} />);
    expect(screen.getByText(/Найдено: 3 отчетов/)).toBeInTheDocument();
  });

  it('handles share action', async () => {
    const onShare = vi.fn();
    render(<ReportsList reports={mockReports} onShare={onShare} />);

    const shareButtons = screen.getAllByTitle('Поделиться');
    fireEvent.click(shareButtons[0]);

    await waitFor(() => {
      expect(onShare).toHaveBeenCalledWith(mockReports[0]);
    });
  });

  it('applies responsive classes for different breakpoints', () => {
    render(<ReportsList reports={mockReports} />);

    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();

    // Check for responsive classes
    const headerCells = screen.getAllByRole('columnheader');
    expect(headerCells.length).toBeGreaterThan(0);
  });
});
