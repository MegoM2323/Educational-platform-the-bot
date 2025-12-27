import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ToastContainer, ToastItem } from '../ToastContainer';

describe('ToastContainer Component', () => {
  const mockOnRemove = vi.fn();

  beforeEach(() => {
    mockOnRemove.mockClear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  const mockToasts: ToastItem[] = [
    {
      id: 'toast-1',
      type: 'success',
      title: 'Success 1',
      description: 'First success toast',
    },
    {
      id: 'toast-2',
      type: 'error',
      title: 'Error 1',
      description: 'First error toast',
    },
  ];

  describe('Rendering', () => {
    it('should render multiple toasts', () => {
      render(
        <ToastContainer toasts={mockToasts} onRemove={mockOnRemove} />
      );

      expect(screen.getByText('Success 1')).toBeInTheDocument();
      expect(screen.getByText('Error 1')).toBeInTheDocument();
    });

    it('should render empty when no toasts', () => {
      const { container } = render(
        <ToastContainer toasts={[]} onRemove={mockOnRemove} />
      );

      const toastRegion = container.querySelector('[role="region"]');
      expect(toastRegion).toBeEmptyDOMElement();
    });

    it('should render toasts with correct position classes', () => {
      const { container } = render(
        <ToastContainer
          toasts={mockToasts}
          onRemove={mockOnRemove}
          position="bottom-right"
        />
      );

      const toastRegion = container.querySelector('[role="region"]');
      expect(toastRegion).toHaveClass('bottom-4', 'right-4');
    });

    it('should respect maxToasts limit', () => {
      const manyToasts: ToastItem[] = Array.from({ length: 10 }, (_, i) => ({
        id: `toast-${i}`,
        type: 'info' as const,
        title: `Toast ${i}`,
      }));

      render(
        <ToastContainer
          toasts={manyToasts}
          onRemove={mockOnRemove}
          maxToasts={3}
        />
      );

      expect(screen.getByText('Toast 0')).toBeInTheDocument();
      expect(screen.getByText('Toast 1')).toBeInTheDocument();
      expect(screen.getByText('Toast 2')).toBeInTheDocument();
      expect(screen.queryByText('Toast 3')).not.toBeInTheDocument();
    });
  });

  describe('Positioning', () => {
    const positions = [
      'top-right',
      'top-left',
      'bottom-right',
      'bottom-left',
      'top-center',
      'bottom-center',
    ] as const;

    positions.forEach((position) => {
      it(`should apply correct classes for ${position}`, () => {
        const { container } = render(
          <ToastContainer
            toasts={mockToasts}
            onRemove={mockOnRemove}
            position={position}
          />
        );

        const toastRegion = container.querySelector('[role="region"]');
        expect(toastRegion).toHaveClass(
          position.split('-')[0],
          position.split('-')[1]
        );
      });
    });

    it('should apply max-width for center positions', () => {
      const { container } = render(
        <ToastContainer
          toasts={mockToasts}
          onRemove={mockOnRemove}
          position="top-center"
        />
      );

      const toastRegion = container.querySelector('[role="region"]');
      expect(toastRegion).toHaveClass('max-w-sm');
    });

    it('should apply max-width for side positions', () => {
      const { container } = render(
        <ToastContainer
          toasts={mockToasts}
          onRemove={mockOnRemove}
          position="top-right"
        />
      );

      const toastRegion = container.querySelector('[role="region"]');
      expect(toastRegion).toHaveClass('max-w-md');
    });
  });

  describe('Toast Interaction', () => {
    it('should call onRemove when close button is clicked', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastContainer toasts={mockToasts} onRemove={mockOnRemove} />
      );

      const closeButtons = screen.getAllByLabelText('Close notification');
      await user.click(closeButtons[0]);

      vi.advanceTimersByTime(300);

      expect(mockOnRemove).toHaveBeenCalledWith('toast-1');
    });

    it('should handle action button clicks', async () => {
      const user = userEvent.setup({ delay: null });
      const mockAction = vi.fn();

      const toastsWithAction: ToastItem[] = [
        {
          id: 'toast-1',
          type: 'success',
          title: 'Success',
          action: {
            label: 'Undo',
            onClick: mockAction,
          },
        },
      ];

      render(
        <ToastContainer
          toasts={toastsWithAction}
          onRemove={mockOnRemove}
        />
      );

      await user.click(screen.getByText('Undo'));
      expect(mockAction).toHaveBeenCalled();
    });
  });

  describe('Toast Updates', () => {
    it('should add new toast when toasts array is updated', () => {
      const { rerender } = render(
        <ToastContainer toasts={[mockToasts[0]]} onRemove={mockOnRemove} />
      );

      expect(screen.getByText('Success 1')).toBeInTheDocument();
      expect(screen.queryByText('Error 1')).not.toBeInTheDocument();

      rerender(
        <ToastContainer toasts={mockToasts} onRemove={mockOnRemove} />
      );

      expect(screen.getByText('Success 1')).toBeInTheDocument();
      expect(screen.getByText('Error 1')).toBeInTheDocument();
    });

    it('should remove toast when it is removed from array', () => {
      const { rerender } = render(
        <ToastContainer toasts={mockToasts} onRemove={mockOnRemove} />
      );

      expect(screen.getByText('Success 1')).toBeInTheDocument();
      expect(screen.getByText('Error 1')).toBeInTheDocument();

      rerender(
        <ToastContainer
          toasts={[mockToasts[0]]}
          onRemove={mockOnRemove}
        />
      );

      expect(screen.getByText('Success 1')).toBeInTheDocument();
      expect(screen.queryByText('Error 1')).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper region role', () => {
      const { container } = render(
        <ToastContainer toasts={mockToasts} onRemove={mockOnRemove} />
      );

      const toastRegion = container.querySelector('[role="region"]');
      expect(toastRegion).toHaveAttribute('aria-label', 'Toast notifications');
    });

    it('should have pointer-events-auto on individual toasts', () => {
      const { container } = render(
        <ToastContainer toasts={mockToasts} onRemove={mockOnRemove} />
      );

      const toastDivs = container.querySelectorAll('.pointer-events-auto');
      expect(toastDivs.length).toBe(mockToasts.length);
    });
  });
});
