import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';

import {
  AlertCircle,
  Save,
  RotateCcw,
  Settings,
  Shield,
  Bell,
  CreditCard,
  Mail,
  Flag,
  Palette,
} from 'lucide-react';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';

// Zod schemas for validation
const featureFlagsSchema = z.object({
  assignments_enabled: z.boolean().default(true),
  payments_enabled: z.boolean().default(true),
  notifications_enabled: z.boolean().default(true),
  chat_enabled: z.boolean().default(true),
  knowledge_graph_enabled: z.boolean().default(true),
});

const rateLimitsSchema = z.object({
  api_requests_per_minute: z
    .number()
    .min(1)
    .max(1000)
    .default(60),
  login_attempts_per_minute: z
    .number()
    .min(1)
    .max(60)
    .default(5),
  brute_force_lockout_duration: z
    .number()
    .min(1)
    .max(1440)
    .default(30),
});

const emailSettingsSchema = z.object({
  smtp_host: z.string().min(1, 'SMTP host is required'),
  smtp_port: z.number().min(1).max(65535).default(587),
  from_address: z.string().email('Invalid email address'),
  use_tls: z.boolean().default(true),
  test_email: z.string().email('Invalid email address').optional(),
});

const paymentSettingsSchema = z.object({
  yookassa_shop_id: z.string().min(1, 'Shop ID is required'),
  yookassa_enabled: z.boolean().default(true),
  payment_methods: z.array(z.string()).default(['card']),
  currency: z.enum(['RUB', 'USD', 'EUR']).default('RUB'),
});

const notificationsSchema = z.object({
  email_notifications_enabled: z.boolean().default(true),
  sms_notifications_enabled: z.boolean().default(false),
  push_notifications_enabled: z.boolean().default(true),
  notify_on_assignment_submission: z.boolean().default(true),
  notify_on_chat_message: z.boolean().default(true),
  notify_on_grade_posted: z.boolean().default(true),
  notify_on_schedule_change: z.boolean().default(true),
});

const uiSettingsSchema = z.object({
  company_name: z.string().min(1, 'Company name is required'),
  logo_url: z.string().url('Invalid URL').optional().or(z.literal('')),
  primary_color: z.string().regex(/^#[0-9a-f]{6}$/i, 'Invalid color format').default('#3b82f6'),
  theme: z.enum(['light', 'dark', 'auto']).default('auto'),
});

const securitySettingsSchema = z.object({
  password_min_length: z
    .number()
    .min(8)
    .max(20)
    .default(12),
  require_uppercase: z.boolean().default(true),
  require_numbers: z.boolean().default(true),
  require_special_characters: z.boolean().default(true),
  session_timeout_minutes: z
    .number()
    .min(5)
    .max(1440)
    .default(30),
  https_enforcement: z.boolean().default(true),
  require_2fa_for_admins: z.boolean().default(true),
});

type FeatureFlagsFormData = z.infer<typeof featureFlagsSchema>;
type RateLimitsFormData = z.infer<typeof rateLimitsSchema>;
type EmailSettingsFormData = z.infer<typeof emailSettingsSchema>;
type PaymentSettingsFormData = z.infer<typeof paymentSettingsSchema>;
type NotificationsFormData = z.infer<typeof notificationsSchema>;
type UISettingsFormData = z.infer<typeof uiSettingsSchema>;
type SecuritySettingsFormData = z.infer<typeof securitySettingsSchema>;

interface SettingMetadata {
  last_updated?: string;
  updated_by?: string;
}

export default function SystemSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [metadata, setMetadata] = useState<Record<string, SettingMetadata>>({});
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  const featureFlagsForm = useForm<FeatureFlagsFormData>({
    resolver: zodResolver(featureFlagsSchema),
    defaultValues: {
      assignments_enabled: true,
      payments_enabled: true,
      notifications_enabled: true,
      chat_enabled: true,
      knowledge_graph_enabled: true,
    },
  });

  const rateLimitsForm = useForm<RateLimitsFormData>({
    resolver: zodResolver(rateLimitsSchema),
    defaultValues: {
      api_requests_per_minute: 60,
      login_attempts_per_minute: 5,
      brute_force_lockout_duration: 30,
    },
  });

  const emailSettingsForm = useForm<EmailSettingsFormData>({
    resolver: zodResolver(emailSettingsSchema),
    defaultValues: {
      smtp_host: '',
      smtp_port: 587,
      from_address: '',
      use_tls: true,
      test_email: '',
    },
  });

  const paymentSettingsForm = useForm<PaymentSettingsFormData>({
    resolver: zodResolver(paymentSettingsSchema),
    defaultValues: {
      yookassa_shop_id: '',
      yookassa_enabled: true,
      payment_methods: ['card'],
      currency: 'RUB',
    },
  });

  const notificationsForm = useForm<NotificationsFormData>({
    resolver: zodResolver(notificationsSchema),
    defaultValues: {
      email_notifications_enabled: true,
      sms_notifications_enabled: false,
      push_notifications_enabled: true,
      notify_on_assignment_submission: true,
      notify_on_chat_message: true,
      notify_on_grade_posted: true,
      notify_on_schedule_change: true,
    },
  });

  const uiSettingsForm = useForm<UISettingsFormData>({
    resolver: zodResolver(uiSettingsSchema),
    defaultValues: {
      company_name: 'THE_BOT',
      logo_url: '',
      primary_color: '#3b82f6',
      theme: 'auto',
    },
  });

  const securitySettingsForm = useForm<SecuritySettingsFormData>({
    resolver: zodResolver(securitySettingsSchema),
    defaultValues: {
      password_min_length: 12,
      require_uppercase: true,
      require_numbers: true,
      require_special_characters: true,
      session_timeout_minutes: 30,
      https_enforcement: true,
      require_2fa_for_admins: true,
    },
  });

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await unifiedAPI.request<Record<string, any>>(
        '/admin/config/'
      );

      if (response.success && response.data) {
        const settings = response.data;
        logger.info('[SystemSettings] Settings loaded:', settings);

        // Update each form with loaded data
        if (settings.feature_flags) {
          featureFlagsForm.reset(settings.feature_flags);
        }
        if (settings.rate_limits) {
          rateLimitsForm.reset(settings.rate_limits);
        }
        if (settings.email_settings) {
          emailSettingsForm.reset(settings.email_settings);
        }
        if (settings.payment_settings) {
          paymentSettingsForm.reset(settings.payment_settings);
        }
        if (settings.notifications) {
          notificationsForm.reset(settings.notifications);
        }
        if (settings.ui_settings) {
          const uiData = settings.ui_settings;
          uiSettingsForm.reset(uiData);
          if (uiData.logo_url) {
            setLogoPreview(uiData.logo_url);
          }
        }
        if (settings.security_settings) {
          securitySettingsForm.reset(settings.security_settings);
        }

        // Store metadata
        if (settings.metadata) {
          setMetadata(settings.metadata);
        }
      }
    } catch (error) {
      logger.error('[SystemSettings] Failed to load settings:', error);
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (
    endpoint: string,
    data: Record<string, any>,
    tabName: string
  ) => {
    try {
      setSaving(true);
      const response = await unifiedAPI.request<any>(
        `/admin/config/${endpoint}/`,
        {
          method: 'PUT',
          body: JSON.stringify(data),
        }
      );

      if (response.success) {
        setHasChanges(false);
        toast.success(`${tabName} settings saved successfully`);
        logger.info(`[SystemSettings] ${tabName} saved:`, data);
      } else {
        toast.error(`Failed to save ${tabName} settings`);
      }
    } catch (error) {
      logger.error(`[SystemSettings] Failed to save ${tabName}:`, error);
      toast.error(`Error saving ${tabName} settings`);
    } finally {
      setSaving(false);
    }
  };

  const testEmailConnection = async () => {
    try {
      setSaving(true);
      const testEmail = emailSettingsForm.getValues('test_email');
      if (!testEmail) {
        toast.error('Please enter an email address');
        return;
      }

      const response = await unifiedAPI.request<any>(
        '/admin/config/test-email/',
        {
          method: 'POST',
          body: JSON.stringify({
            test_email: testEmail,
          }),
        }
      );

      if (response.success) {
        toast.success('Test email sent successfully');
      } else {
        toast.error('Failed to send test email');
      }
    } catch (error) {
      logger.error('[SystemSettings] Email test failed:', error);
      toast.error('Error testing email connection');
    } finally {
      setSaving(false);
    }
  };

  const resetToDefaults = async () => {
    if (
      !window.confirm(
        'Are you sure you want to reset all settings to defaults? This cannot be undone.'
      )
    ) {
      return;
    }

    try {
      setSaving(true);
      const response = await unifiedAPI.request<any>(
        '/admin/config/reset/',
        {
          method: 'POST',
        }
      );

      if (response.success) {
        toast.success('Settings reset to defaults');
        await loadSettings();
      } else {
        toast.error('Failed to reset settings');
      }
    } catch (error) {
      logger.error('[SystemSettings] Failed to reset settings:', error);
      toast.error('Error resetting settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg text-muted-foreground">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Settings className="h-8 w-8" />
          <h1 className="text-3xl font-bold">System Settings</h1>
        </div>
        <p className="text-muted-foreground">
          Configure platform-wide settings and features
        </p>
      </div>

      {/* Unsaved Changes Warning */}
      {hasChanges && (
        <Alert className="bg-yellow-50 border-yellow-200">
          <AlertCircle className="h-4 w-4 text-yellow-600" />
          <AlertDescription className="text-yellow-800">
            You have unsaved changes. Please save before leaving this page.
          </AlertDescription>
        </Alert>
      )}

      {/* Settings Tabs */}
      <Tabs defaultValue="feature-flags" className="w-full">
        <TabsList className="grid w-full grid-cols-4 lg:grid-cols-7">
          <TabsTrigger value="feature-flags" className="text-xs sm:text-sm">
            <Flag className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Features</span>
          </TabsTrigger>
          <TabsTrigger value="rate-limits" className="text-xs sm:text-sm">
            Rate Limits
          </TabsTrigger>
          <TabsTrigger value="email" className="text-xs sm:text-sm">
            <Mail className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Email</span>
          </TabsTrigger>
          <TabsTrigger value="payment" className="text-xs sm:text-sm">
            <CreditCard className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Payment</span>
          </TabsTrigger>
          <TabsTrigger value="notifications" className="text-xs sm:text-sm">
            <Bell className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Notify</span>
          </TabsTrigger>
          <TabsTrigger value="ui" className="text-xs sm:text-sm">
            <Palette className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">UI</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="text-xs sm:text-sm">
            <Shield className="h-4 w-4 mr-2" />
            <span className="hidden sm:inline">Security</span>
          </TabsTrigger>
        </TabsList>

        {/* Feature Flags Tab */}
        <TabsContent value="feature-flags">
          <Card>
            <CardHeader>
              <CardTitle>Feature Flags</CardTitle>
              <CardDescription>
                Enable or disable platform features
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...featureFlagsForm}>
                <form
                  onSubmit={featureFlagsForm.handleSubmit((data) => {
                    setHasChanges(true);
                    saveSettings(
                      'feature-flags',
                      data,
                      'Feature Flags'
                    );
                  })}
                  className="space-y-6"
                >
                  <FormField
                    control={featureFlagsForm.control}
                    name="assignments_enabled"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel>Assignments Enabled</FormLabel>
                          <FormDescription>
                            Allow students to submit assignments
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={featureFlagsForm.control}
                    name="payments_enabled"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel>Payments Enabled</FormLabel>
                          <FormDescription>
                            Enable payment processing for subscriptions
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={featureFlagsForm.control}
                    name="notifications_enabled"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel>Notifications Enabled</FormLabel>
                          <FormDescription>
                            Send email and push notifications
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={featureFlagsForm.control}
                    name="chat_enabled"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel>Chat Enabled</FormLabel>
                          <FormDescription>
                            Enable real-time messaging between users
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={featureFlagsForm.control}
                    name="knowledge_graph_enabled"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel>Knowledge Graph Enabled</FormLabel>
                          <FormDescription>
                            Use knowledge graph for lesson planning
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rate Limits Tab */}
        <TabsContent value="rate-limits">
          <Card>
            <CardHeader>
              <CardTitle>Rate Limits</CardTitle>
              <CardDescription>
                Configure API and authentication rate limits
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...rateLimitsForm}>
                <form
                  onSubmit={rateLimitsForm.handleSubmit((data) => {
                    setHasChanges(true);
                    saveSettings('rate-limits', data, 'Rate Limits');
                  })}
                  className="space-y-6"
                >
                  <FormField
                    control={rateLimitsForm.control}
                    name="api_requests_per_minute"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>API Requests Per Minute</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            max={1000}
                            {...field}
                            onChange={(e) =>
                              field.onChange(parseInt(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormDescription>
                          Maximum API requests allowed per minute (1-1000)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={rateLimitsForm.control}
                    name="login_attempts_per_minute"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Login Attempts Per Minute</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            max={60}
                            {...field}
                            onChange={(e) =>
                              field.onChange(parseInt(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormDescription>
                          Maximum login attempts allowed per minute (1-60)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={rateLimitsForm.control}
                    name="brute_force_lockout_duration"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Brute Force Lockout Duration (minutes)
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            max={1440}
                            {...field}
                            onChange={(e) =>
                              field.onChange(parseInt(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormDescription>
                          How long to lock account after failed attempts (1-1440
                          minutes)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Email Settings Tab */}
        <TabsContent value="email">
          <Card>
            <CardHeader>
              <CardTitle>Email Settings</CardTitle>
              <CardDescription>
                Configure SMTP for sending emails
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...emailSettingsForm}>
                <form
                  onSubmit={emailSettingsForm.handleSubmit((data) => {
                    setHasChanges(true);
                    saveSettings('email-settings', data, 'Email Settings');
                  })}
                  className="space-y-6"
                >
                  <FormField
                    control={emailSettingsForm.control}
                    name="smtp_host"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>SMTP Host</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="smtp.gmail.com"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          SMTP server hostname
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={emailSettingsForm.control}
                    name="smtp_port"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>SMTP Port</FormLabel>
                        <FormControl>
                          <Input
                            type="number"
                            min={1}
                            max={65535}
                            {...field}
                            onChange={(e) =>
                              field.onChange(parseInt(e.target.value))
                            }
                          />
                        </FormControl>
                        <FormDescription>
                          SMTP server port (usually 587 or 465)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={emailSettingsForm.control}
                    name="from_address"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>From Address</FormLabel>
                        <FormControl>
                          <Input
                            type="email"
                            placeholder="noreply@example.com"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Email address emails will be sent from
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={emailSettingsForm.control}
                    name="use_tls"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel>Use TLS</FormLabel>
                          <FormDescription>
                            Use TLS encryption for SMTP connection
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <div className="space-y-3 border-t pt-6">
                    <h3 className="font-medium">Test Email Connection</h3>
                    <FormField
                      control={emailSettingsForm.control}
                      name="test_email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Test Email Address</FormLabel>
                          <FormControl>
                            <Input
                              type="email"
                              placeholder="test@example.com"
                              {...field}
                            />
                          </FormControl>
                          <FormDescription>
                            Send a test email to verify SMTP settings
                          </FormDescription>
                        </FormItem>
                      )}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={testEmailConnection}
                      disabled={saving}
                    >
                      Send Test Email
                    </Button>
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Payment Settings Tab */}
        <TabsContent value="payment">
          <Card>
            <CardHeader>
              <CardTitle>Payment Settings</CardTitle>
              <CardDescription>
                Configure YooKassa payment processing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...paymentSettingsForm}>
                <form
                  onSubmit={paymentSettingsForm.handleSubmit((data) => {
                    setHasChanges(true);
                    saveSettings('payment-settings', data, 'Payment Settings');
                  })}
                  className="space-y-6"
                >
                  <FormField
                    control={paymentSettingsForm.control}
                    name="yookassa_shop_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>YooKassa Shop ID</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="••••••••"
                            autoComplete="new-password"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Your YooKassa merchant shop ID
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={paymentSettingsForm.control}
                    name="yookassa_enabled"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                        <div className="space-y-0.5">
                          <FormLabel>YooKassa Enabled</FormLabel>
                          <FormDescription>
                            Enable YooKassa payment processing
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  <FormItem>
                    <FormLabel>Supported Payment Methods</FormLabel>
                    <div className="space-y-3 mt-3">
                      {['card', 'wallet', 'bank_transfer'].map((method) => (
                        <div key={method} className="flex items-center">
                          <Checkbox
                            id={method}
                            checked={
                              paymentSettingsForm
                                .getValues('payment_methods')
                                .includes(method)
                            }
                            onCheckedChange={(checked) => {
                              const current = paymentSettingsForm.getValues(
                                'payment_methods'
                              );
                              if (checked) {
                                paymentSettingsForm.setValue(
                                  'payment_methods',
                                  [...current, method]
                                );
                              } else {
                                paymentSettingsForm.setValue(
                                  'payment_methods',
                                  current.filter((m) => m !== method)
                                );
                              }
                            }}
                          />
                          <Label
                            htmlFor={method}
                            className="ml-2 cursor-pointer"
                          >
                            {method === 'card'
                              ? 'Credit/Debit Card'
                              : method === 'wallet'
                                ? 'Digital Wallet'
                                : 'Bank Transfer'}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </FormItem>

                  <FormField
                    control={paymentSettingsForm.control}
                    name="currency"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Currency</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="RUB">
                              Russian Ruble (RUB)
                            </SelectItem>
                            <SelectItem value="USD">
                              US Dollar (USD)
                            </SelectItem>
                            <SelectItem value="EUR">Euro (EUR)</SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          Primary currency for payment processing
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>
                Configure notification channels and preferences
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...notificationsForm}>
                <form
                  onSubmit={notificationsForm.handleSubmit((data) => {
                    setHasChanges(true);
                    saveSettings('notifications', data, 'Notifications');
                  })}
                  className="space-y-6"
                >
                  <div className="border-b pb-6">
                    <h3 className="font-medium mb-4">
                      Notification Channels
                    </h3>

                    <FormField
                      control={notificationsForm.control}
                      name="email_notifications_enabled"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4 mb-3">
                          <div className="space-y-0.5">
                            <FormLabel>Email Notifications</FormLabel>
                            <FormDescription>
                              Send notifications via email
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={notificationsForm.control}
                      name="sms_notifications_enabled"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4 mb-3">
                          <div className="space-y-0.5">
                            <FormLabel>SMS Notifications</FormLabel>
                            <FormDescription>
                              Send notifications via SMS
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={notificationsForm.control}
                      name="push_notifications_enabled"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                          <div className="space-y-0.5">
                            <FormLabel>Push Notifications</FormLabel>
                            <FormDescription>
                              Send push notifications to apps
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>

                  <div>
                    <h3 className="font-medium mb-4">
                      Event Notifications
                    </h3>

                    <FormField
                      control={notificationsForm.control}
                      name="notify_on_assignment_submission"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center gap-3 mb-3">
                          <FormControl>
                            <Checkbox
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                          <Label className="cursor-pointer">
                            Assignment Submissions
                          </Label>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={notificationsForm.control}
                      name="notify_on_chat_message"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center gap-3 mb-3">
                          <FormControl>
                            <Checkbox
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                          <Label className="cursor-pointer">
                            New Chat Messages
                          </Label>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={notificationsForm.control}
                      name="notify_on_grade_posted"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center gap-3 mb-3">
                          <FormControl>
                            <Checkbox
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                          <Label className="cursor-pointer">
                            Grade Posted
                          </Label>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={notificationsForm.control}
                      name="notify_on_schedule_change"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center gap-3">
                          <FormControl>
                            <Checkbox
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                          <Label className="cursor-pointer">
                            Schedule Changes
                          </Label>
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* UI Settings Tab */}
        <TabsContent value="ui">
          <Card>
            <CardHeader>
              <CardTitle>UI Settings</CardTitle>
              <CardDescription>
                Customize the appearance of the platform
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...uiSettingsForm}>
                <form
                  onSubmit={uiSettingsForm.handleSubmit((data) => {
                    setHasChanges(true);
                    saveSettings('ui-settings', data, 'UI Settings');
                  })}
                  className="space-y-6"
                >
                  <FormField
                    control={uiSettingsForm.control}
                    name="company_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Company Name</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="THE_BOT"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Display name for your platform
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={uiSettingsForm.control}
                    name="logo_url"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Logo URL</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="https://example.com/logo.png"
                            {...field}
                            onChange={(e) => {
                              field.onChange(e);
                              if (e.target.value) {
                                setLogoPreview(e.target.value);
                              }
                            }}
                          />
                        </FormControl>
                        <FormDescription>
                          URL to your company logo
                        </FormDescription>
                        {logoPreview && (
                          <div className="mt-2 p-2 bg-muted rounded">
                            <img
                              src={logoPreview}
                              alt="Logo preview"
                              className="h-12 object-contain"
                            />
                          </div>
                        )}
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={uiSettingsForm.control}
                    name="primary_color"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Primary Color</FormLabel>
                        <div className="flex gap-3 items-center">
                          <FormControl>
                            <Input
                              type="color"
                              {...field}
                              className="h-10 w-20"
                            />
                          </FormControl>
                          <Input
                            type="text"
                            value={field.value}
                            onChange={field.onChange}
                            placeholder="#3b82f6"
                            className="flex-1"
                          />
                        </div>
                        <FormDescription>
                          Primary brand color (hex format)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={uiSettingsForm.control}
                    name="theme"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Theme</FormLabel>
                        <Select
                          onValueChange={field.onChange}
                          defaultValue={field.value}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="light">Light</SelectItem>
                            <SelectItem value="dark">Dark</SelectItem>
                            <SelectItem value="auto">
                              Auto (Follow System)
                            </SelectItem>
                          </SelectContent>
                        </Select>
                        <FormDescription>
                          Default theme for the platform
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Settings Tab */}
        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>
                Configure security policies and requirements
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...securitySettingsForm}>
                <form
                  onSubmit={securitySettingsForm.handleSubmit((data) => {
                    setHasChanges(true);
                    saveSettings('security-settings', data, 'Security Settings');
                  })}
                  className="space-y-6"
                >
                  <div className="border-b pb-6">
                    <h3 className="font-medium mb-4">Password Policy</h3>

                    <FormField
                      control={securitySettingsForm.control}
                      name="password_min_length"
                      render={({ field }) => (
                        <FormItem className="mb-4">
                          <FormLabel>Minimum Password Length</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={8}
                              max={20}
                              {...field}
                              onChange={(e) =>
                                field.onChange(parseInt(e.target.value))
                              }
                            />
                          </FormControl>
                          <FormDescription>
                            Minimum number of characters required (8-20)
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={securitySettingsForm.control}
                      name="require_uppercase"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4 mb-3">
                          <div className="space-y-0.5">
                            <FormLabel>Require Uppercase</FormLabel>
                            <FormDescription>
                              Require at least one uppercase letter
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={securitySettingsForm.control}
                      name="require_numbers"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4 mb-3">
                          <div className="space-y-0.5">
                            <FormLabel>Require Numbers</FormLabel>
                            <FormDescription>
                              Require at least one number
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={securitySettingsForm.control}
                      name="require_special_characters"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                          <div className="space-y-0.5">
                            <FormLabel>Require Special Characters</FormLabel>
                            <FormDescription>
                              Require at least one special character (!@#$%^&*)
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="border-b pb-6">
                    <h3 className="font-medium mb-4">Session Management</h3>

                    <FormField
                      control={securitySettingsForm.control}
                      name="session_timeout_minutes"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Session Timeout (minutes)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={5}
                              max={1440}
                              {...field}
                              onChange={(e) =>
                                field.onChange(parseInt(e.target.value))
                              }
                            />
                          </FormControl>
                          <FormDescription>
                            How long before inactive sessions expire (5-1440
                            minutes)
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <div>
                    <h3 className="font-medium mb-4">Additional Security</h3>

                    <FormField
                      control={securitySettingsForm.control}
                      name="https_enforcement"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4 mb-3">
                          <div className="space-y-0.5">
                            <FormLabel>HTTPS Enforcement</FormLabel>
                            <FormDescription>
                              Enforce HTTPS for all connections
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={securitySettingsForm.control}
                      name="require_2fa_for_admins"
                      render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                          <div className="space-y-0.5">
                            <FormLabel>Require 2FA for Admins</FormLabel>
                            <FormDescription>
                              Require two-factor authentication for admin users
                            </FormDescription>
                          </div>
                          <FormControl>
                            <Switch
                              checked={field.value}
                              onCheckedChange={field.onChange}
                            />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={saving}
                      className="gap-2"
                    >
                      <Save className="h-4 w-4" />
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Reset Button */}
      <div className="flex justify-center pt-6">
        <Button
          variant="outline"
          onClick={resetToDefaults}
          disabled={saving}
          className="gap-2"
        >
          <RotateCcw className="h-4 w-4" />
          Reset All Settings to Defaults
        </Button>
      </div>
    </div>
  );
}
