import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import SystemSettings from '../SystemSettings';
import * as sonner from 'sonner';

// Mock dependencies
vi.mock('sonner');
vi.mock('@/integrations/api/unifiedClient');
vi.mock('@/utils/logger');

const mockUnifiedAPI = {
  request: vi.fn(),
};

vi.doMock('@/integrations/api/unifiedClient', () => ({
  unifiedAPI: mockUnifiedAPI,
}));

const mockLogger = {
  info: vi.fn(),
  error: vi.fn(),
  warn: vi.fn(),
};

vi.doMock('@/utils/logger', () => ({
  logger: mockLogger,
}));

describe('SystemSettings Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (sonner.toast.success as any).mockImplementation(() => {});
    (sonner.toast.error as any).mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Loading State', () => {
    it('should show loading text when component mounts', async () => {
      mockUnifiedAPI.request.mockImplementation(
        () =>
          new Promise(() => {
            /* Never resolves */
          })
      );

      render(<SystemSettings />);
      expect(screen.getByText(/Loading settings/i)).toBeInTheDocument();
    });

    it('should load settings from API on mount', async () => {
      const mockSettings = {
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      };

      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);

      render(<SystemSettings />);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith('/admin/config/');
      });
    });
  });

  describe('Feature Flags Tab', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render all feature flag toggles', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        expect(screen.getByText('Assignments Enabled')).toBeInTheDocument();
        expect(screen.getByText('Payments Enabled')).toBeInTheDocument();
        expect(screen.getByText('Notifications Enabled')).toBeInTheDocument();
        expect(screen.getByText('Chat Enabled')).toBeInTheDocument();
        expect(screen.getByText('Knowledge Graph Enabled')).toBeInTheDocument();
      });
    });

    it('should save feature flag changes', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      });

      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: { message: 'Settings saved' },
      });

      render(<SystemSettings />);

      await waitFor(() => {
        expect(screen.getByText('Assignments Enabled')).toBeInTheDocument();
      });

      const saveButton = screen.getByRole('button', {
        name: /Save Changes/i,
      });

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/feature-flags/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });
  });

  describe('Rate Limits Tab', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          rate_limits: {
            api_requests_per_minute: 60,
            login_attempts_per_minute: 5,
            brute_force_lockout_duration: 30,
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render rate limit inputs', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const rateLimitsTab = tabs.find((tab) =>
          tab.textContent?.includes('Rate Limits')
        );
        if (rateLimitsTab) {
          fireEvent.click(rateLimitsTab);
        }
      });

      await waitFor(() => {
        expect(
          screen.getByLabelText(/API Requests Per Minute/)
        ).toBeInTheDocument();
        expect(
          screen.getByLabelText(/Login Attempts Per Minute/)
        ).toBeInTheDocument();
        expect(
          screen.getByLabelText(/Brute Force Lockout Duration/)
        ).toBeInTheDocument();
      });
    });

    it('should validate rate limit inputs', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          rate_limits: {
            api_requests_per_minute: 60,
            login_attempts_per_minute: 5,
            brute_force_lockout_duration: 30,
          },
        },
      });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const rateLimitsTab = tabs.find((tab) =>
          tab.textContent?.includes('Rate Limits')
        );
        if (rateLimitsTab) {
          fireEvent.click(rateLimitsTab);
        }
      });

      await waitFor(() => {
        const input = screen.getByLabelText(
          /API Requests Per Minute/
        ) as HTMLInputElement;
        expect(input).toHaveAttribute('min', '1');
        expect(input).toHaveAttribute('max', '1000');
      });
    });

    it('should save rate limit changes', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            rate_limits: {
              api_requests_per_minute: 60,
              login_attempts_per_minute: 5,
              brute_force_lockout_duration: 30,
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Settings saved' },
        });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const rateLimitsTab = tabs.find((tab) =>
          tab.textContent?.includes('Rate Limits')
        );
        if (rateLimitsTab) {
          fireEvent.click(rateLimitsTab);
        }
      });

      await waitFor(() => {
        const input = screen.getByLabelText(/API Requests Per Minute/);
        expect(input).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button', { name: /Save Changes/i });
      const saveButton = buttons[buttons.length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/rate-limits/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });
  });

  describe('Email Settings Tab', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          email_settings: {
            smtp_host: 'smtp.gmail.com',
            smtp_port: 587,
            from_address: 'noreply@example.com',
            use_tls: true,
            test_email: '',
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render email settings inputs', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const emailTab = tabs.find((tab) => tab.textContent?.includes('Email'));
        if (emailTab) {
          fireEvent.click(emailTab);
        }
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/SMTP Host/)).toBeInTheDocument();
        expect(screen.getByLabelText(/SMTP Port/)).toBeInTheDocument();
        expect(screen.getByLabelText(/From Address/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Use TLS/)).toBeInTheDocument();
      });
    });

    it('should test email connection', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            email_settings: {
              smtp_host: 'smtp.gmail.com',
              smtp_port: 587,
              from_address: 'noreply@example.com',
              use_tls: true,
              test_email: '',
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Email sent' },
        });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const emailTab = tabs.find((tab) => tab.textContent?.includes('Email'));
        if (emailTab) {
          fireEvent.click(emailTab);
        }
      });

      await waitFor(() => {
        const testEmailInput = screen.getByPlaceholderText(/test@example.com/);
        expect(testEmailInput).toBeInTheDocument();
      });

      const testEmailInput = screen.getByPlaceholderText(
        /test@example.com/
      ) as HTMLInputElement;
      await userEvent.clear(testEmailInput);
      await userEvent.type(testEmailInput, 'admin@example.com');

      const testButton = screen.getByRole('button', {
        name: /Send Test Email/i,
      });
      await userEvent.click(testButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/test-email/',
          expect.objectContaining({
            method: 'POST',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });

    it('should show error when test email address is missing', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          email_settings: {
            smtp_host: 'smtp.gmail.com',
            smtp_port: 587,
            from_address: 'noreply@example.com',
            use_tls: true,
            test_email: '',
          },
        },
      });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const emailTab = tabs.find((tab) => tab.textContent?.includes('Email'));
        if (emailTab) {
          fireEvent.click(emailTab);
        }
      });

      await waitFor(() => {
        const testButton = screen.getByRole('button', {
          name: /Send Test Email/i,
        });
        expect(testButton).toBeInTheDocument();
      });

      const testButton = screen.getByRole('button', {
        name: /Send Test Email/i,
      });
      await userEvent.click(testButton);

      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalled();
      });
    });

    it('should save email settings', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            email_settings: {
              smtp_host: 'smtp.gmail.com',
              smtp_port: 587,
              from_address: 'noreply@example.com',
              use_tls: true,
              test_email: '',
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Settings saved' },
        });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const emailTab = tabs.find((tab) => tab.textContent?.includes('Email'));
        if (emailTab) {
          fireEvent.click(emailTab);
        }
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/SMTP Host/)).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button', { name: /Save Changes/i });
      const saveButton = buttons[buttons.length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/email-settings/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });
  });

  describe('Payment Settings Tab', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          payment_settings: {
            yookassa_shop_id: '12345',
            yookassa_enabled: true,
            payment_methods: ['card'],
            currency: 'RUB',
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render payment settings controls', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const paymentTab = tabs.find((tab) =>
          tab.textContent?.includes('Payment')
        );
        if (paymentTab) {
          fireEvent.click(paymentTab);
        }
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/YooKassa Shop ID/)).toBeInTheDocument();
        expect(screen.getByLabelText(/YooKassa Enabled/)).toBeInTheDocument();
        expect(
          screen.getByLabelText(/Supported Payment Methods/)
        ).toBeInTheDocument();
        expect(screen.getByLabelText(/Currency/)).toBeInTheDocument();
      });
    });

    it('should toggle payment methods', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          payment_settings: {
            yookassa_shop_id: '12345',
            yookassa_enabled: true,
            payment_methods: ['card'],
            currency: 'RUB',
          },
        },
      });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const paymentTab = tabs.find((tab) =>
          tab.textContent?.includes('Payment')
        );
        if (paymentTab) {
          fireEvent.click(paymentTab);
        }
      });

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

      expect(walletCheckbox).toBeChecked();
    });

    it('should save payment settings', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            payment_settings: {
              yookassa_shop_id: '12345',
              yookassa_enabled: true,
              payment_methods: ['card'],
              currency: 'RUB',
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Settings saved' },
        });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const paymentTab = tabs.find((tab) =>
          tab.textContent?.includes('Payment')
        );
        if (paymentTab) {
          fireEvent.click(paymentTab);
        }
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/YooKassa Shop ID/)).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button', { name: /Save Changes/i });
      const saveButton = buttons[buttons.length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/payment-settings/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });
  });

  describe('Notifications Tab', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          notifications: {
            email_notifications_enabled: true,
            sms_notifications_enabled: false,
            push_notifications_enabled: true,
            notify_on_assignment_submission: true,
            notify_on_chat_message: true,
            notify_on_grade_posted: true,
            notify_on_schedule_change: true,
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render notification toggles and checkboxes', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const notifyTab = tabs.find((tab) =>
          tab.textContent?.includes('Notify')
        );
        if (notifyTab) {
          fireEvent.click(notifyTab);
        }
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/Email Notifications/)).toBeInTheDocument();
        expect(screen.getByLabelText(/SMS Notifications/)).toBeInTheDocument();
        expect(
          screen.getByLabelText(/Push Notifications/)
        ).toBeInTheDocument();
      });
    });

    it('should save notification preferences', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            notifications: {
              email_notifications_enabled: true,
              sms_notifications_enabled: false,
              push_notifications_enabled: true,
              notify_on_assignment_submission: true,
              notify_on_chat_message: true,
              notify_on_grade_posted: true,
              notify_on_schedule_change: true,
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Settings saved' },
        });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const notifyTab = tabs.find((tab) =>
          tab.textContent?.includes('Notify')
        );
        if (notifyTab) {
          fireEvent.click(notifyTab);
        }
      });

      await waitFor(() => {
        expect(
          screen.getByLabelText(/Email Notifications/)
        ).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button', { name: /Save Changes/i });
      const saveButton = buttons[buttons.length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/notifications/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });
  });

  describe('UI Settings Tab', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          ui_settings: {
            company_name: 'THE_BOT',
            logo_url: 'https://example.com/logo.png',
            primary_color: '#3b82f6',
            theme: 'auto',
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render UI settings inputs', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const uiTab = tabs.find((tab) => tab.textContent?.includes('UI'));
        if (uiTab) {
          fireEvent.click(uiTab);
        }
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/Company Name/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Logo URL/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Primary Color/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Theme/)).toBeInTheDocument();
      });
    });

    it('should show logo preview', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          ui_settings: {
            company_name: 'THE_BOT',
            logo_url: 'https://example.com/logo.png',
            primary_color: '#3b82f6',
            theme: 'auto',
          },
        },
      });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const uiTab = tabs.find((tab) => tab.textContent?.includes('UI'));
        if (uiTab) {
          fireEvent.click(uiTab);
        }
      });

      await waitFor(() => {
        const logoInput = screen.getByLabelText(/Logo URL/);
        expect(logoInput).toHaveValue('https://example.com/logo.png');
      });
    });

    it('should save UI settings', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            ui_settings: {
              company_name: 'THE_BOT',
              logo_url: 'https://example.com/logo.png',
              primary_color: '#3b82f6',
              theme: 'auto',
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Settings saved' },
        });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const uiTab = tabs.find((tab) => tab.textContent?.includes('UI'));
        if (uiTab) {
          fireEvent.click(uiTab);
        }
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/Company Name/)).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button', { name: /Save Changes/i });
      const saveButton = buttons[buttons.length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/ui-settings/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });
  });

  describe('Security Settings Tab', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          security_settings: {
            password_min_length: 12,
            require_uppercase: true,
            require_numbers: true,
            require_special_characters: true,
            session_timeout_minutes: 30,
            https_enforcement: true,
            require_2fa_for_admins: true,
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render security settings controls', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const securityTab = tabs.find((tab) =>
          tab.textContent?.includes('Security')
        );
        if (securityTab) {
          fireEvent.click(securityTab);
        }
      });

      await waitFor(() => {
        expect(
          screen.getByLabelText(/Minimum Password Length/)
        ).toBeInTheDocument();
        expect(screen.getByLabelText(/Require Uppercase/)).toBeInTheDocument();
        expect(screen.getByLabelText(/Require Numbers/)).toBeInTheDocument();
        expect(
          screen.getByLabelText(/Require Special Characters/)
        ).toBeInTheDocument();
      });
    });

    it('should save security settings', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            security_settings: {
              password_min_length: 12,
              require_uppercase: true,
              require_numbers: true,
              require_special_characters: true,
              session_timeout_minutes: 30,
              https_enforcement: true,
              require_2fa_for_admins: true,
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Settings saved' },
        });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const securityTab = tabs.find((tab) =>
          tab.textContent?.includes('Security')
        );
        if (securityTab) {
          fireEvent.click(securityTab);
        }
      });

      await waitFor(() => {
        expect(
          screen.getByLabelText(/Minimum Password Length/)
        ).toBeInTheDocument();
      });

      const buttons = screen.getAllByRole('button', { name: /Save Changes/i });
      const saveButton = buttons[buttons.length - 1];

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/security-settings/',
          expect.objectContaining({
            method: 'PUT',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });
    });

    it('should validate password length input', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          security_settings: {
            password_min_length: 12,
            require_uppercase: true,
            require_numbers: true,
            require_special_characters: true,
            session_timeout_minutes: 30,
            https_enforcement: true,
            require_2fa_for_admins: true,
          },
        },
      });

      render(<SystemSettings />);

      await waitFor(() => {
        const tabs = screen.getAllByRole('tab');
        const securityTab = tabs.find((tab) =>
          tab.textContent?.includes('Security')
        );
        if (securityTab) {
          fireEvent.click(securityTab);
        }
      });

      await waitFor(() => {
        const input = screen.getByLabelText(
          /Minimum Password Length/
        ) as HTMLInputElement;
        expect(input).toHaveAttribute('min', '8');
        expect(input).toHaveAttribute('max', '20');
      });
    });
  });

  describe('Reset to Defaults', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should show reset button', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        expect(
          screen.getByRole('button', { name: /Reset All Settings/ })
        ).toBeInTheDocument();
      });
    });

    it('should confirm before resetting', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      });

      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

      render(<SystemSettings />);

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

      expect(confirmSpy).toHaveBeenCalled();
      confirmSpy.mockRestore();
    });

    it('should reset all settings after confirmation', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            feature_flags: {
              assignments_enabled: true,
              payments_enabled: true,
              notifications_enabled: true,
              chat_enabled: true,
              knowledge_graph_enabled: true,
            },
          },
        })
        .mockResolvedValueOnce({
          success: true,
          data: { message: 'Reset complete' },
        })
        .mockResolvedValueOnce({
          success: true,
          data: {
            feature_flags: {
              assignments_enabled: true,
              payments_enabled: true,
              notifications_enabled: true,
              chat_enabled: true,
              knowledge_graph_enabled: true,
            },
          },
        });

      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

      render(<SystemSettings />);

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
        expect(mockUnifiedAPI.request).toHaveBeenCalledWith(
          '/admin/config/reset/',
          expect.objectContaining({
            method: 'POST',
          })
        );
        expect(sonner.toast.success).toHaveBeenCalled();
      });

      confirmSpy.mockRestore();
    });
  });

  describe('Error Handling', () => {
    it('should show error toast when loading settings fails', async () => {
      mockUnifiedAPI.request.mockRejectedValueOnce(
        new Error('API Error')
      );

      render(<SystemSettings />);

      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalled();
      });
    });

    it('should show error toast when saving fails', async () => {
      mockUnifiedAPI.request
        .mockResolvedValueOnce({
          success: true,
          data: {
            feature_flags: {
              assignments_enabled: true,
              payments_enabled: true,
              notifications_enabled: true,
              chat_enabled: true,
              knowledge_graph_enabled: true,
            },
          },
        })
        .mockResolvedValueOnce({
          success: false,
          error: 'Save failed',
        });

      render(<SystemSettings />);

      await waitFor(() => {
        expect(screen.getByText('Assignments Enabled')).toBeInTheDocument();
      });

      const saveButton = screen.getByRole('button', {
        name: /Save Changes/i,
      });

      await userEvent.click(saveButton);

      await waitFor(() => {
        expect(sonner.toast.error).toHaveBeenCalled();
      });
    });
  });

  describe('Unsaved Changes Warning', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should not show warning initially', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        expect(
          screen.queryByText(/unsaved changes/i)
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Responsive Design', () => {
    beforeEach(() => {
      const mockSettings = {
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      };
      mockUnifiedAPI.request.mockResolvedValueOnce(mockSettings);
    });

    it('should render tabs with proper layout', async () => {
      render(<SystemSettings />);

      await waitFor(() => {
        const tabsList = screen.getByRole('tablist');
        expect(tabsList).toBeInTheDocument();
        expect(tabsList).toHaveClass('grid');
      });
    });

    it('should render responsive button layout', async () => {
      mockUnifiedAPI.request.mockResolvedValueOnce({
        success: true,
        data: {
          feature_flags: {
            assignments_enabled: true,
            payments_enabled: true,
            notifications_enabled: true,
            chat_enabled: true,
            knowledge_graph_enabled: true,
          },
        },
      });

      render(<SystemSettings />);

      await waitFor(() => {
        const saveButtons = screen.getAllByRole('button', {
          name: /Save Changes/i,
        });
        expect(saveButtons.length).toBeGreaterThan(0);
      });
    });
  });
});
