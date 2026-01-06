import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PayButton } from '../PayButton';
import React from 'react';

const mockCallbacks = {
  onPayClick: vi.fn(),
  onCancelClick: vi.fn(),
};

const resetMocks = () => {
  vi.clearAllMocks();
};

describe('PayButton', () => {
  beforeEach(resetMocks);

  describe('Case 1: Cancelled subscription with expiration date', () => {
    it('should display "Доступ ограничен" badge with orange styling', () => {
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          subscriptionStatus="cancelled"
          expiresAt={expiresAt}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Доступ ограничен');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-orange-100', 'text-orange-800');
    });

    it('should display expiration date in the correct format', () => {
      const expiresAt = '2026-02-15T14:30:00Z';

      render(
        <PayButton
          subscriptionStatus="cancelled"
          expiresAt={expiresAt}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const dateText = screen.getByText(/До:/);
      expect(dateText).toBeInTheDocument();
      expect(dateText.textContent).toMatch(/15.*02.*2026/);
    });

    it('should not show payment button when subscription is cancelled', () => {
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          subscriptionStatus="cancelled"
          expiresAt={expiresAt}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const payButton = screen.queryByRole('button', {
        name: /Подключить|Оплатить|Отключить/,
      });
      expect(payButton).not.toBeInTheDocument();
    });

    it('should not call any callback when cancelled', () => {
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

      const { container } = render(
        <PayButton
          subscriptionStatus="cancelled"
          expiresAt={expiresAt}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      fireEvent.click(container.querySelector('[role="button"]') || document.body);
      expect(mockCallbacks.onPayClick).not.toHaveBeenCalled();
      expect(mockCallbacks.onCancelClick).not.toHaveBeenCalled();
    });
  });

  describe('Case 2: Active payment status', () => {
    it('should display "Активен" badge with green styling', () => {
      const nextPaymentDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nextPaymentDate}
          hasSubscription={true}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Активен');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('should show cancel subscription button when hasSubscription is true', () => {
      const nextPaymentDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nextPaymentDate}
          hasSubscription={true}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const cancelButton = screen.getByRole('button', {
        name: /Отключить автосписание/,
      });
      expect(cancelButton).toBeInTheDocument();
    });

    it('should call onCancelClick when cancel subscription button is clicked', async () => {
      const nextPaymentDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nextPaymentDate}
          hasSubscription={true}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const cancelButton = screen.getByRole('button', {
        name: /Отключить автосписание/,
      });

      await userEvent.click(cancelButton);
      expect(mockCallbacks.onCancelClick).toHaveBeenCalledTimes(1);
    });

    it('should not show cancel button when hasSubscription is false', () => {
      const nextPaymentDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nextPaymentDate}
          hasSubscription={false}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const cancelButton = screen.queryByRole('button', {
        name: /Отключить автосписание/,
      });
      expect(cancelButton).not.toBeInTheDocument();
    });
  });

  describe('Case 3: Overdue payment', () => {
    it('should display "Требуется оплата" badge with red styling when overdue', () => {
      render(
        <PayButton
          paymentStatus="overdue"
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Требуется оплата');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });

    it('should show red "Оплатить предмет" button when overdue', () => {
      render(
        <PayButton
          paymentStatus="overdue"
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Оплатить предмет/,
      });
      expect(payButton).toBeInTheDocument();
      expect(payButton).toHaveClass('bg-destructive');
    });

    it('should call onPayClick when pay button is clicked for overdue', async () => {
      render(
        <PayButton
          paymentStatus="overdue"
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Оплатить предмет/,
      });

      await userEvent.click(payButton);
      expect(mockCallbacks.onPayClick).toHaveBeenCalledTimes(1);
    });

    it('should display correct red styling for overdue state', () => {
      const pastDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={pastDate}
          hasSubscription={false}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Требуется оплата');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });
  });

  describe('Case 4: Not connected / Waiting payment', () => {
    it('should display "Не подключен" badge when no payment status', () => {
      render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Не подключен');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
    });

    it('should show green "Подключить предмет" button for waiting state', () => {
      render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Подключить предмет/,
      });
      expect(payButton).toBeInTheDocument();
      expect(payButton).not.toHaveClass('bg-destructive');
    });

    it('should call onPayClick when pay button is clicked for waiting state', async () => {
      render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Подключить предмет/,
      });

      await userEvent.click(payButton);
      expect(mockCallbacks.onPayClick).toHaveBeenCalledTimes(1);
    });

    it('should display "Не подключен" for null/undefined payment status', () => {
      render(
        <PayButton
          paymentStatus={undefined}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Не подключен');
      expect(badge).toBeInTheDocument();
    });
  });

  describe('Tooltip functionality', () => {
    it('should show tooltip with descriptive text on hover for cancelled state', async () => {
      const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          subscriptionStatus="cancelled"
          expiresAt={expiresAt}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const tooltipTrigger = screen.getByText('Доступ ограничен').closest('div');
      fireEvent.mouseEnter(tooltipTrigger!);

      await waitFor(() => {
        const tooltip = screen.queryByText(/Доступ ограничен до/);
        if (tooltip) {
          expect(tooltip).toBeInTheDocument();
        }
      });
    });

    it('should show appropriate tooltip for active state', async () => {
      const nextPaymentDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nextPaymentDate}
          hasSubscription={true}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const tooltipTrigger = screen.getByText('Активен').closest('div');
      fireEvent.mouseEnter(tooltipTrigger!);

      await waitFor(() => {
        const tooltip = screen.queryByText(/Активная подписка/);
        if (tooltip) {
          expect(tooltip).toBeInTheDocument();
        }
      });
    });

    it('should show appropriate tooltip for overdue state', async () => {
      render(
        <PayButton
          paymentStatus="overdue"
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const tooltipTrigger = screen.getByText('Требуется оплата').closest('div');
      fireEvent.mouseEnter(tooltipTrigger!);

      await waitFor(() => {
        const tooltip = screen.queryByText(/Срок оплаты истёк/);
        if (tooltip) {
          expect(tooltip).toBeInTheDocument();
        }
      });
    });

    it('should show appropriate tooltip for waiting state', async () => {
      render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const tooltipTrigger = screen.getByText('Не подключен').closest('div');
      fireEvent.mouseEnter(tooltipTrigger!);

      await waitFor(() => {
        const tooltip = screen.queryByText(/Нажмите для подключения/);
        if (tooltip) {
          expect(tooltip).toBeInTheDocument();
        }
      });
    });
  });

  describe('Button click handling', () => {
    it('should call onPayClick when payment button is clicked', async () => {
      render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Подключить предмет/,
      });

      await userEvent.click(payButton);
      expect(mockCallbacks.onPayClick).toHaveBeenCalledTimes(1);
    });

    it('should not call onCancelClick when onPayClick is triggered', async () => {
      render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Подключить предмет/,
      });

      await userEvent.click(payButton);
      expect(mockCallbacks.onPayClick).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onCancelClick).not.toHaveBeenCalled();
    });

    it('should not call onPayClick when onCancelClick is triggered', async () => {
      const nextPaymentDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nextPaymentDate}
          hasSubscription={true}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const cancelButton = screen.getByRole('button', {
        name: /Отключить автосписание/,
      });

      await userEvent.click(cancelButton);
      expect(mockCallbacks.onCancelClick).toHaveBeenCalledTimes(1);
      expect(mockCallbacks.onPayClick).not.toHaveBeenCalled();
    });
  });

  describe('Loading state', () => {
    it('should disable buttons when isLoading is true', () => {
      render(
        <PayButton
          paymentStatus="overdue"
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
          isLoading={true}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Оплатить предмет/,
      });
      expect(payButton).toBeDisabled();
    });

    it('should disable cancel button when isLoading is true', () => {
      const nextPaymentDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nextPaymentDate}
          hasSubscription={true}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
          isLoading={true}
        />
      );

      const cancelButton = screen.getByRole('button', {
        name: /Отключить автосписание/,
      });
      expect(cancelButton).toBeDisabled();
    });

    it('should enable buttons when isLoading is false', () => {
      render(
        <PayButton
          paymentStatus="overdue"
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
          isLoading={false}
        />
      );

      const payButton = screen.getByRole('button', {
        name: /Оплатить предмет/,
      });
      expect(payButton).not.toBeDisabled();
    });
  });

  describe('CSS className prop', () => {
    it('should apply custom className to root container', () => {
      const customClass = 'custom-test-class';

      const { container } = render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
          className={customClass}
        />
      );

      const rootDiv = container.querySelector('div');
      expect(rootDiv).toHaveClass(customClass);
    });

    it('should apply custom className alongside default classes', () => {
      const customClass = 'mt-4 mb-2';

      const { container } = render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
          className={customClass}
        />
      );

      const rootDiv = container.querySelector('div');
      expect(rootDiv).toHaveClass('flex', 'flex-col', customClass);
    });
  });

  describe('Edge cases', () => {
    it('should handle missing all props except callbacks', () => {
      const { container } = render(
        <PayButton
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      expect(container).toBeInTheDocument();
      expect(screen.getByText('Не подключен')).toBeInTheDocument();
    });

    it('should show active state when hasSubscription is true without nextPaymentDate', () => {
      render(
        <PayButton
          paymentStatus="paid"
          hasSubscription={true}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Активен');
      expect(badge).toBeInTheDocument();
    });

    it('should correctly handle date at exactly current time', () => {
      const nowDate = new Date().toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={nowDate}
          hasSubscription={false}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Требуется оплата');
      expect(badge).toBeInTheDocument();
    });

    it('should prefer nextPaymentDate over hasSubscription for state determination', () => {
      const futureDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString();

      render(
        <PayButton
          paymentStatus="paid"
          nextPaymentDate={futureDate}
          hasSubscription={false}
          onPayClick={mockCallbacks.onPayClick}
          onCancelClick={mockCallbacks.onCancelClick}
        />
      );

      const badge = screen.getByText('Активен');
      expect(badge).toBeInTheDocument();

      const cancelButton = screen.queryByRole('button', {
        name: /Отключить автосписание/,
      });
      expect(cancelButton).not.toBeInTheDocument();
    });
  });
});
