import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { Toast, ToastType } from '../Toast';

describe('Toast Component', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('Rendering', () => {
    it('should render success toast with correct styling', () => {
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success Message"
          onClose={mockOnClose}
        />
      );

      const toast = screen.getByText('Success Message');
      expect(toast).toBeInTheDocument();
      expect(toast.closest('[role="alert"]')).toHaveClass('bg-green-50');
    });

    it('should render error toast with correct styling', () => {
      render(
        <Toast
          id="test-1"
          type="error"
          title="Error Message"
          onClose={mockOnClose}
        />
      );

      const toast = screen.getByText('Error Message');
      expect(toast.closest('[role="alert"]')).toHaveClass('bg-red-50');
    });

    it('should render warning toast with correct styling', () => {
      render(
        <Toast
          id="test-1"
          type="warning"
          title="Warning Message"
          onClose={mockOnClose}
        />
      );

      const toast = screen.getByText('Warning Message');
      expect(toast.closest('[role="alert"]')).toHaveClass('bg-yellow-50');
    });

    it('should render info toast with correct styling', () => {
      render(
        <Toast
          id="test-1"
          type="info"
          title="Info Message"
          onClose={mockOnClose}
        />
      );

      const toast = screen.getByText('Info Message');
      expect(toast.closest('[role="alert"]')).toHaveClass('bg-blue-50');
    });

    it('should render loading toast with spinner', () => {
      render(
        <Toast
          id="test-1"
          type="loading"
          title="Loading..."
          onClose={mockOnClose}
        />
      );

      const toast = screen.getByText('Loading...');
      expect(toast).toBeInTheDocument();
      expect(toast.closest('[role="alert"]')).toHaveClass('bg-gray-50');
    });

    it('should display description when provided', () => {
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          description="This is a detailed description"
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('This is a detailed description')).toBeInTheDocument();
    });

    it('should not display description when not provided', () => {
      const { container } = render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          onClose={mockOnClose}
        />
      );

      const descriptions = container.querySelectorAll('[class*="text-gray-700"]');
      expect(descriptions.length).toBe(0);
    });
  });

  describe('Action Button', () => {
    it('should display action button when action is provided', () => {
      const mockAction = vi.fn();
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          action={{ label: 'Undo', onClick: mockAction }}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('Undo')).toBeInTheDocument();
    });

    it('should call action onClick when action button is clicked', async () => {
      const user = userEvent.setup({ delay: null });
      const mockAction = vi.fn();

      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          action={{ label: 'Retry', onClick: mockAction }}
          onClose={mockOnClose}
        />
      );

      await user.click(screen.getByText('Retry'));
      expect(mockAction).toHaveBeenCalledTimes(1);
    });

    it('should not display action button when action is not provided', () => {
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          onClose={mockOnClose}
        />
      );

      expect(screen.queryByRole('button', { name: /Undo|Retry/ })).not.toBeInTheDocument();
    });
  });

  describe('Close Button', () => {
    it('should display close button', () => {
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          onClose={mockOnClose}
        />
      );

      const closeButton = screen.getByLabelText('Close notification');
      expect(closeButton).toBeInTheDocument();
    });

    it('should call onClose when close button is clicked', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          onClose={mockOnClose}
        />
      );

      const closeButton = screen.getByLabelText('Close notification');
      await user.click(closeButton);

      vi.advanceTimersByTime(300);

      expect(mockOnClose).toHaveBeenCalledWith('test-1');
    });
  });

  describe('Auto-dismiss', () => {
    it('should auto-dismiss after default duration for success', () => {
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          onClose={mockOnClose}
        />
      );

      vi.advanceTimersByTime(3000);
      vi.advanceTimersByTime(300);

      expect(mockOnClose).toHaveBeenCalledWith('test-1');
    });

    it('should auto-dismiss after default duration for error', () => {
      render(
        <Toast
          id="test-1"
          type="error"
          title="Error"
          onClose={mockOnClose}
        />
      );

      vi.advanceTimersByTime(5000);
      vi.advanceTimersByTime(300);

      expect(mockOnClose).toHaveBeenCalledWith('test-1');
    });

    it('should auto-dismiss after custom duration', () => {
      render(
        <Toast
          id="test-1"
          type="info"
          title="Info"
          duration={2000}
          onClose={mockOnClose}
        />
      );

      vi.advanceTimersByTime(2000);
      vi.advanceTimersByTime(300);

      expect(mockOnClose).toHaveBeenCalledWith('test-1');
    });

    it('should not auto-dismiss when autoClose is false', () => {
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          autoClose={false}
          onClose={mockOnClose}
        />
      );

      vi.advanceTimersByTime(10000);

      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it('should not auto-dismiss loading toast', () => {
      render(
        <Toast
          id="test-1"
          type="loading"
          title="Loading..."
          onClose={mockOnClose}
        />
      );

      vi.advanceTimersByTime(10000);

      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper role for error toast', () => {
      const { container } = render(
        <Toast
          id="test-1"
          type="error"
          title="Error"
          onClose={mockOnClose}
        />
      );

      const alert = container.querySelector('[role="alert"]');
      expect(alert).toHaveAttribute('aria-live', 'assertive');
      expect(alert).toHaveAttribute('aria-atomic', 'true');
    });

    it('should have proper role for info toast', () => {
      const { container } = render(
        <Toast
          id="test-1"
          type="info"
          title="Info"
          onClose={mockOnClose}
        />
      );

      const alert = container.querySelector('[role="alert"]');
      expect(alert).toHaveAttribute('aria-live', 'polite');
      expect(alert).toHaveAttribute('aria-atomic', 'true');
    });

    it('should have label for close button', () => {
      render(
        <Toast
          id="test-1"
          type="success"
          title="Success"
          onClose={mockOnClose}
        />
      );

      const closeButton = screen.getByLabelText('Close notification');
      expect(closeButton).toHaveAttribute('aria-label');
    });
  });
});
