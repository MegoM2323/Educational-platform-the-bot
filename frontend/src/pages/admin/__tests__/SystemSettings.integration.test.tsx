import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import SystemSettings from '../SystemSettings';

// Mock the API
vi.mock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: {
    request: vi.fn(),
  },
}));

vi.mock('@/utils/logger', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { unifiedAPI } from '@/integrations/api/unifiedClient';
import * as sonner from 'sonner';

const mockRequest = unifiedAPI.request as any;

describe('SystemSettings Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (component: React.ReactElement) => {
    return render(<BrowserRouter>{component}</BrowserRouter>);
  };

  const mockCompleteSettings = {
    success: true,
    data: {
      feature_flags: {
        assignments_enabled: true,
        payments_enabled: true,
        notifications_enabled: true,
        chat_enabled: true,
        knowledge_graph_enabled: true,
      },
      rate_limits: {
        api_requests_per_minute: 60,
        login_attempts_per_minute: 5,
        brute_force_lockout_duration: 30,
      },
      email_settings: {
        smtp_host: 'smtp.gmail.com',
        smtp_port: 587,
        from_address: 'noreply@example.com',
        use_tls: true,
      },
      payment_settings: {
        yookassa_shop_id: '12345',
        yookassa_enabled: true,
        payment_methods: ['card'],
        currency: 'RUB',
      },
      notifications: {
        email_notifications_enabled: true,
        sms_notifications_enabled: false,
        push_notifications_enabled: true,
        notify_on_assignment_submission: true,
        notify_on_chat_message: true,
        notify_on_grade_posted: true,
        notify_on_schedule_change: true,
      },
      ui_settings: {
        company_name: 'THE_BOT',
        logo_url: 'https://example.com/logo.png',
        primary_color: '#3b82f6',
        theme: 'auto',
      },
      security_settings: {
        password_min_length: 12,
        require_uppercase: true,
        require_numbers: true,
        require_special_characters: true,
        session_timeout_minutes: 30,
        https_enforcement: true,
        require_2fa_for_admins: true,
      },
      metadata: {},
    },
  };

  describe('Full Settings Workflow', () => {
    it('should load all settings tabs on mount', async () => {
      mockRequest.mockResolvedValueOnce(mockCompleteSettings);

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        expect(
          screen.getByRole('tab', { name: /Features/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole('tab', { name: /Rate Limits/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole('tab', { name: /Email/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole('tab', { name: /Payment/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole('tab', { name: /Notify/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole('tab', { name: /UI/i })
        ).toBeInTheDocument();
        expect(
          screen.getByRole('tab', { name: /Security/i })
        ).toBeInTheDocument();
      });
    });

    it('should navigate between tabs and load content', async () => {
      mockRequest.mockResolvedValueOnce(mockCompleteSettings);

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        expect(screen.getByText('Assignments Enabled')).toBeInTheDocument();
      });

      const rateLimitsTab = screen.getByRole('tab', { name: /Rate Limits/i });
      await userEvent.click(rateLimitsTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/API Requests Per Minute/)
        ).toBeInTheDocument();
      });

      const emailTab = screen.getByRole('tab', { name: /Email/i });
      await userEvent.click(emailTab);

      await waitFor(() => {
        expect(screen.getByLabelText(/SMTP Host/)).toBeInTheDocument();
      });
    });

    it('should save multiple settings across different tabs', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({ success: true, data: {} })
        .mockResolvedValueOnce({ success: true, data: {} });

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        expect(screen.getByText('Assignments Enabled')).toBeInTheDocument();
      });

      // Save feature flags
      let saveButtons = screen.getAllByRole('button', { name: /Save Changes/i });
      await userEvent.click(saveButtons[0]);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/feature-flags/',
          expect.any(Object)
        );
      });

      // Switch to rate limits tab
      const rateLimitsTab = screen.getByRole('tab', { name: /Rate Limits/i });
      await userEvent.click(rateLimitsTab);

      await waitFor(() => {
        expect(
          screen.getByLabelText(/API Requests Per Minute/)
        ).toBeInTheDocument();
      });

      // Save rate limits
      saveButtons = screen.getAllByRole('button', { name: /Save Changes/i });
      await userEvent.click(saveButtons[saveButtons.length - 1]);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/rate-limits/',
          expect.any(Object)
        );
      });
    });
  });

  describe('Settings Validation', () => {
    it('should validate number inputs in rate limits tab', async () => {
      mockRequest.mockResolvedValueOnce(mockCompleteSettings);

      renderWithRouter(<SystemSettings />);

      const rateLimitsTab = screen.getByRole('tab', { name: /Rate Limits/i });
      await userEvent.click(rateLimitsTab);

      await waitFor(() => {
        const input = screen.getByLabelText(
          /API Requests Per Minute/
        ) as HTMLInputElement;
        expect(input).toHaveAttribute('type', 'number');
        expect(input).toHaveAttribute('min', '1');
        expect(input).toHaveAttribute('max', '1000');
      });
    });

    it('should validate email format in email settings', async () => {
      mockRequest.mockResolvedValueOnce(mockCompleteSettings);

      renderWithRouter(<SystemSettings />);

      const emailTab = screen.getByRole('tab', { name: /Email/i });
      await userEvent.click(emailTab);

      await waitFor(() => {
        const fromAddressInput = screen.getByLabelText(
          /From Address/
        ) as HTMLInputElement;
        expect(fromAddressInput).toHaveAttribute('type', 'email');
      });
    });

    it('should validate color format in UI settings', async () => {
      mockRequest.mockResolvedValueOnce(mockCompleteSettings);

      renderWithRouter(<SystemSettings />);

      const uiTab = screen.getByRole('tab', { name: /UI/i });
      await userEvent.click(uiTab);

      await waitFor(() => {
        const colorInput = screen.getByLabelText(
          /Primary Color/
        ) as HTMLInputElement;
        expect(colorInput).toHaveAttribute('type', 'color');
      });
    });
  });

  describe('Error Recovery', () => {
    it('should handle API errors gracefully', async () => {
      mockRequest.mockRejectedValueOnce(new Error('API Error'));

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalledWith(
          'Failed to load settings'
        );
      });
    });

    it('should handle save failures', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({
          success: false,
          error: 'Validation failed',
        });

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        expect(screen.getByText('Assignments Enabled')).toBeInTheDocument();
      });

      const saveButton = screen.getByRole('button', { name: /Save Changes/i });
      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalled();
      });
    });
  });

  describe('Responsive Design Tests', () => {
    it('should render mobile-friendly form layout', async () => {
      mockRequest.mockResolvedValueOnce(mockCompleteSettings);

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        const forms = screen.getAllByRole('form', { hidden: true });
        expect(forms.length).toBeGreaterThan(0);
      });
    });

    it('should have responsive tab navigation', async () => {
      mockRequest.mockResolvedValueOnce(mockCompleteSettings);

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        const tablist = screen.getByRole('tablist');
        expect(tablist).toHaveClass('grid');
      });
    });
  });

  describe('Feature Flags Workflow', () => {
    it('should disable/enable features', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({ success: true, data: {} });

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        const assignmentsToggle = screen.getByRole('switch', {
          name: /Assignments Enabled/i,
        }) as HTMLInputElement;
        expect(assignmentsToggle.checked).toBe(true);
      });

      const assignmentsToggle = screen.getByRole('switch', {
        name: /Assignments Enabled/i,
      });

      await userEvent.click(assignmentsToggle);

      const saveButton = screen.getByRole('button', { name: /Save Changes/i });
      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/feature-flags/',
          expect.objectContaining({
            method: 'PUT',
            body: expect.stringContaining('assignments_enabled'),
          })
        );
      });
    });
  });

  describe('Email Testing Workflow', () => {
    it('should test email connection with valid address', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({ success: true, data: {} });

      renderWithRouter(<SystemSettings />);

      const emailTab = screen.getByRole('tab', { name: /Email/i });
      await userEvent.click(emailTab);

      await waitFor(() => {
        const testEmailInput = screen.getByPlaceholderText(
          /test@example.com/
        );
        expect(testEmailInput).toBeInTheDocument();
      });

      const testEmailInput = screen.getByPlaceholderText(
        /test@example.com/
      ) as HTMLInputElement;

      await userEvent.clear(testEmailInput);
      await userEvent.type(testEmailInput, 'test@example.com');

      const testButton = screen.getByRole('button', {
        name: /Send Test Email/i,
      });

      await userEvent.click(testButton);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/test-email/',
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });
  });

  describe('Payment Settings Workflow', () => {
    it('should toggle payment methods', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({ success: true, data: {} });

      renderWithRouter(<SystemSettings />);

      const paymentTab = screen.getByRole('tab', { name: /Payment/i });
      await userEvent.click(paymentTab);

      await waitFor(() => {
        const cardCheckbox = screen.getByRole('checkbox', {
          name: /Credit\/Debit Card/i,
        });
        expect(cardCheckbox).toBeChecked();
      });

      const walletCheckbox = screen.getByRole('checkbox', {
        name: /Digital Wallet/i,
      });

      await userEvent.click(walletCheckbox);

      const saveButton = screen.getAllByRole('button', {
        name: /Save Changes/i,
      })[screen.getAllByRole('button', { name: /Save Changes/i }).length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/payment-settings/',
          expect.any(Object)
        );
      });
    });
  });

  describe('UI Settings Workflow', () => {
    it('should update company name and theme', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({ success: true, data: {} });

      renderWithRouter(<SystemSettings />);

      const uiTab = screen.getByRole('tab', { name: /UI/i });
      await userEvent.click(uiTab);

      await waitFor(() => {
        const companyNameInput = screen.getByLabelText(/Company Name/);
        expect(companyNameInput).toHaveValue('THE_BOT');
      });

      const companyNameInput = screen.getByLabelText(
        /Company Name/
      ) as HTMLInputElement;

      await userEvent.clear(companyNameInput);
      await userEvent.type(companyNameInput, 'My Platform');

      const saveButton = screen.getAllByRole('button', {
        name: /Save Changes/i,
      })[screen.getAllByRole('button', { name: /Save Changes/i }).length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/ui-settings/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
      });
    });
  });

  describe('Security Settings Workflow', () => {
    it('should configure password policy', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({ success: true, data: {} });

      renderWithRouter(<SystemSettings />);

      const securityTab = screen.getByRole('tab', { name: /Security/i });
      await userEvent.click(securityTab);

      await waitFor(() => {
        const passwordLengthInput = screen.getByLabelText(
          /Minimum Password Length/
        );
        expect(passwordLengthInput).toHaveValue(12);
      });

      const uppercaseToggle = screen.getByRole('switch', {
        name: /Require Uppercase/i,
      });

      expect(uppercaseToggle).toBeChecked();

      const saveButton = screen.getAllByRole('button', {
        name: /Save Changes/i,
      })[screen.getAllByRole('button', { name: /Save Changes/i }).length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/security-settings/',
          expect.any(Object)
        );
      });
    });
  });

  describe('Reset to Defaults', () => {
    it('should reset all settings', async () => {
      mockRequest
        .mockResolvedValueOnce(mockCompleteSettings)
        .mockResolvedValueOnce({ success: true, data: {} })
        .mockResolvedValueOnce(mockCompleteSettings);

      const confirmSpy = vi
        .spyOn(window, 'confirm')
        .mockReturnValue(true);

      renderWithRouter(<SystemSettings />);

      await waitFor(() => {
        const resetButton = screen.getByRole('button', {
          name: /Reset All Settings/,
        });
        expect(resetButton).toBeInTheDocument();
      });

      const resetButton = screen.getByRole('button', {
        name: /Reset All Settings/,
      });

      await userEvent.click(resetButton);

      await waitFor(() => {
        expect(mockRequest).toHaveBeenCalledWith(
          '/admin/config/reset/',
          expect.objectContaining({
            method: 'POST',
          })
        );
      });

      confirmSpy.mockRestore();
    });
  });
});
