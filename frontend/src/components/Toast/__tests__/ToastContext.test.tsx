import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ToastProvider, useToast } from '../ToastContext';

const TestComponent = () => {
  const toast = useToast();

  return (
    <div>
      <button onClick={() => toast.showSuccess('Success message')}>
        Show Success
      </button>
      <button onClick={() => toast.showError('Error message')}>
        Show Error
      </button>
      <button onClick={() => toast.showWarning('Warning message')}>
        Show Warning
      </button>
      <button onClick={() => toast.showInfo('Info message')}>
        Show Info
      </button>
      <button onClick={() => toast.showLoading('Loading...')}>
        Show Loading
      </button>
      <button onClick={() => toast.clearAll()}>
        Clear All
      </button>
    </div>
  );
};

describe('ToastContext and useToast Hook', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe('useToast Hook', () => {
    it('should throw error when used outside provider', () => {
      expect(() => {
        render(<TestComponent />);
      }).toThrow('useToast must be used within a ToastProvider');
    });
  });

  describe('ToastProvider', () => {
    it('should provide toast context to children', () => {
      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      expect(screen.getByText('Show Success')).toBeInTheDocument();
    });

    it('should render toast container', () => {
      const { container } = render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      const toastRegion = container.querySelector('[role="region"]');
      expect(toastRegion).toBeInTheDocument();
      expect(toastRegion).toHaveAttribute('aria-label', 'Toast notifications');
    });

    it('should respect position prop', () => {
      const { container } = render(
        <ToastProvider position="bottom-left">
          <TestComponent />
        </ToastProvider>
      );

      const toastRegion = container.querySelector('[role="region"]');
      expect(toastRegion).toHaveClass('bottom-4', 'left-4');
    });

    it('should respect maxToasts prop', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider maxToasts={2}>
          <TestComponent />
        </ToastProvider>
      );

      const successButton = screen.getByText('Show Success');

      await user.click(successButton);
      await user.click(successButton);
      await user.click(successButton);

      const toasts = screen.getAllByRole('alert');
      expect(toasts.length).toBe(2);
    });
  });

  describe('showSuccess method', () => {
    it('should create and display success toast', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Success'));

      expect(screen.getByText('Success message')).toBeInTheDocument();
    });

    it('should auto-dismiss after default duration', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Success'));

      expect(screen.getByText('Success message')).toBeInTheDocument();

      vi.advanceTimersByTime(3000);
      vi.advanceTimersByTime(300);

      await waitFor(() => {
        expect(screen.queryByText('Success message')).not.toBeInTheDocument();
      });
    });
  });

  describe('showError method', () => {
    it('should create and display error toast', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Error'));

      expect(screen.getByText('Error message')).toBeInTheDocument();
    });

    it('should auto-dismiss after error duration (5000ms)', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Error'));

      expect(screen.getByText('Error message')).toBeInTheDocument();

      vi.advanceTimersByTime(5000);
      vi.advanceTimersByTime(300);

      await waitFor(() => {
        expect(screen.queryByText('Error message')).not.toBeInTheDocument();
      });
    });
  });

  describe('showWarning method', () => {
    it('should create and display warning toast', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Warning'));

      expect(screen.getByText('Warning message')).toBeInTheDocument();
    });
  });

  describe('showInfo method', () => {
    it('should create and display info toast', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Info'));

      expect(screen.getByText('Info message')).toBeInTheDocument();
    });
  });

  describe('showLoading method', () => {
    it('should create and display loading toast', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Loading'));

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should not auto-dismiss loading toast', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Loading'));

      expect(screen.getByText('Loading...')).toBeInTheDocument();

      vi.advanceTimersByTime(10000);

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('clearAll method', () => {
    it('should remove all toasts', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Success'));
      await user.click(screen.getByText('Show Error'));

      expect(screen.getByText('Success message')).toBeInTheDocument();
      expect(screen.getByText('Error message')).toBeInTheDocument();

      await user.click(screen.getByText('Clear All'));

      await waitFor(() => {
        expect(screen.queryByText('Success message')).not.toBeInTheDocument();
        expect(screen.queryByText('Error message')).not.toBeInTheDocument();
      });
    });
  });

  describe('Multiple toasts', () => {
    it('should display multiple toasts simultaneously', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Success'));
      await user.click(screen.getByText('Show Error'));
      await user.click(screen.getByText('Show Warning'));

      expect(screen.getByText('Success message')).toBeInTheDocument();
      expect(screen.getByText('Error message')).toBeInTheDocument();
      expect(screen.getByText('Warning message')).toBeInTheDocument();
    });

    it('should respect maxToasts limit with multiple toasts', async () => {
      const user = userEvent.setup({ delay: null });

      render(
        <ToastProvider maxToasts={2}>
          <TestComponent />
        </ToastProvider>
      );

      await user.click(screen.getByText('Show Success'));
      await user.click(screen.getByText('Show Error'));
      await user.click(screen.getByText('Show Warning'));

      const alerts = screen.getAllByRole('alert');
      expect(alerts.length).toBe(2);
    });
  });
});
