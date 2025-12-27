import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { LoadingSpinner } from '@/components/LoadingSpinner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, AlertCircle, ChevronLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';
import { toast } from 'sonner';

/**
 * Notification settings form validation schema
 * Defines validation rules for all notification preferences
 */
const notificationSettingsSchema = z.object({
  // Notification types
  assignments_enabled: z.boolean().default(true),
  materials_enabled: z.boolean().default(true),
  messages_enabled: z.boolean().default(true),
  payments_enabled: z.boolean().default(true),
  invoices_enabled: z.boolean().default(true),
  system_enabled: z.boolean().default(true),

  // Notification channels
  email_enabled: z.boolean().default(true),
  push_enabled: z.boolean().default(true),
  sms_enabled: z.boolean().default(false),

  // Quiet hours
  quiet_hours_enabled: z.boolean().default(false),
  quiet_hours_start: z.string().regex(/^\d{2}:\d{2}$/, 'Invalid time format (HH:MM)').default('22:00'),
  quiet_hours_end: z.string().regex(/^\d{2}:\d{2}$/, 'Invalid time format (HH:MM)').default('08:00'),
  timezone: z.string().default('UTC'),
});

type NotificationSettingsFormData = z.infer<typeof notificationSettingsSchema>;

/**
 * Common timezones for user selection
 */
const TIMEZONES = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)' },
  { value: 'Europe/Moscow', label: 'Europe/Moscow (MSK)' },
  { value: 'Europe/London', label: 'Europe/London (GMT/BST)' },
  { value: 'Europe/Paris', label: 'Europe/Paris (CET/CEST)' },
  { value: 'Europe/Berlin', label: 'Europe/Berlin (CET/CEST)' },
  { value: 'America/New_York', label: 'America/New_York (EST/EDT)' },
  { value: 'America/Los_Angeles', label: 'America/Los_Angeles (PST/PDT)' },
  { value: 'America/Chicago', label: 'America/Chicago (CST/CDT)' },
  { value: 'Asia/Tokyo', label: 'Asia/Tokyo (JST)' },
  { value: 'Asia/Shanghai', label: 'Asia/Shanghai (CST)' },
  { value: 'Asia/Hong_Kong', label: 'Asia/Hong_Kong (HKT)' },
  { value: 'Australia/Sydney', label: 'Australia/Sydney (AEDT/AEST)' },
  { value: 'Asia/Singapore', label: 'Asia/Singapore (SGT)' },
  { value: 'Asia/Dubai', label: 'Asia/Dubai (GST)' },
];

/**
 * NotificationSettings Component
 *
 * Provides UI for managing notification preferences including:
 * - Notification type toggles (assignments, materials, messages, etc.)
 * - Channel preferences (email, push, SMS)
 * - Quiet hours configuration with timezone support
 * - API integration for fetching and saving preferences
 *
 * @example
 * ```tsx
 * <NotificationSettings />
 * ```
 */
export const NotificationSettings = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const form = useForm<NotificationSettingsFormData>({
    resolver: zodResolver(notificationSettingsSchema),
    mode: 'onBlur',
    defaultValues: {
      assignments_enabled: true,
      materials_enabled: true,
      messages_enabled: true,
      payments_enabled: true,
      invoices_enabled: true,
      system_enabled: true,
      email_enabled: true,
      push_enabled: true,
      sms_enabled: false,
      quiet_hours_enabled: false,
      quiet_hours_start: '22:00',
      quiet_hours_end: '08:00',
      timezone: 'UTC',
    },
  });

  // Fetch current notification settings on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);

        logger.debug('[NotificationSettings] Fetching notification preferences...');

        const response = await unifiedAPI.fetch(
          '/accounts/notification-settings/',
          'GET'
        );

        if (!response.ok) {
          if (response.status === 401) {
            navigate('/auth');
            return;
          }

          throw new Error(`Failed to fetch notification settings (${response.status})`);
        }

        const data = await response.json();
        logger.debug('[NotificationSettings] Fetched settings:', data);

        // Map API response to form values
        const settings = data.data || data;

        form.reset({
          assignments_enabled: settings.assignments_enabled ?? true,
          materials_enabled: settings.materials_enabled ?? true,
          messages_enabled: settings.messages_enabled ?? true,
          payments_enabled: settings.payments_enabled ?? true,
          invoices_enabled: settings.invoices_enabled ?? true,
          system_enabled: settings.system_enabled ?? true,
          email_enabled: settings.email_enabled ?? true,
          push_enabled: settings.push_enabled ?? true,
          sms_enabled: settings.sms_enabled ?? false,
          quiet_hours_enabled: settings.quiet_hours_enabled ?? false,
          quiet_hours_start: settings.quiet_hours_start ?? '22:00',
          quiet_hours_end: settings.quiet_hours_end ?? '08:00',
          timezone: settings.timezone ?? 'UTC',
        });
      } catch (error) {
        logger.error('[NotificationSettings] Error fetching settings:', error);
        const errorMessage = error instanceof Error ? error.message : 'Failed to load notification settings';
        setLoadError(errorMessage);
        toast.error('Failed to load notification settings');
      } finally {
        setIsLoading(false);
      }
    };

    fetchSettings();
  }, [form, navigate]);

  /**
   * Handle form submission to save notification preferences
   */
  const handleSubmit = async (values: NotificationSettingsFormData) => {
    try {
      setIsSaving(true);
      setSaveError(null);
      setSaveSuccess(false);

      logger.debug('[NotificationSettings] Saving notification settings:', values);

      const response = await unifiedAPI.fetch(
        '/accounts/notification-settings/',
        'PATCH',
        values
      );

      if (!response.ok) {
        if (response.status === 401) {
          navigate('/auth');
          return;
        }

        const errorData = await response.json().catch(() => ({}));
        const errorMessage =
          errorData.error || errorData.detail || `Failed to save settings (${response.status})`;

        throw new Error(errorMessage);
      }

      logger.debug('[NotificationSettings] Settings saved successfully');
      setSaveSuccess(true);
      toast.success('Notification settings saved successfully');

      // Clear success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      logger.error('[NotificationSettings] Error saving settings:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to save notification settings';
      setSaveError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  /**
   * Handle reset to default values
   */
  const handleReset = () => {
    form.reset();
    toast.info('Settings reset to last saved values');
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading notification settings..." />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate(-1)}
            className="mb-4"
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Notification Settings</h1>
          <p className="text-gray-600">
            Manage how and when you receive notifications about your activities
          </p>
        </div>

        {/* Load Error Alert */}
        {loadError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}

        {/* Save Success Alert */}
        {saveSuccess && (
          <Alert className="mb-6 bg-green-50 text-green-800 border-green-200">
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>Your notification settings have been saved successfully!</AlertDescription>
          </Alert>
        )}

        {/* Save Error Alert */}
        {saveError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{saveError}</AlertDescription>
          </Alert>
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            {/* Notification Types Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="text-2xl">📬</span>
                  Notification Types
                </CardTitle>
                <CardDescription>
                  Choose which types of notifications you want to receive
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Assignments Toggle */}
                <FormField
                  control={form.control}
                  name="assignments_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Assignments</FormLabel>
                        <FormDescription>
                          Get notified about new assignments and submission deadlines
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Materials Toggle */}
                <FormField
                  control={form.control}
                  name="materials_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Materials</FormLabel>
                        <FormDescription>
                          Get notified when new learning materials are shared
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Messages Toggle */}
                <FormField
                  control={form.control}
                  name="messages_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Messages</FormLabel>
                        <FormDescription>
                          Get notified about new direct messages and chat replies
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Payments Toggle */}
                <FormField
                  control={form.control}
                  name="payments_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Payments</FormLabel>
                        <FormDescription>
                          Get notified about payment requests and confirmations
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Invoices Toggle */}
                <FormField
                  control={form.control}
                  name="invoices_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Invoices</FormLabel>
                        <FormDescription>
                          Get notified about new invoices and billing updates
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* System Toggle */}
                <FormField
                  control={form.control}
                  name="system_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">System Notifications</FormLabel>
                        <FormDescription>
                          Get notified about important system updates and announcements
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />
              </CardContent>
            </Card>

            {/* Notification Channels Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="text-2xl">📱</span>
                  Notification Channels
                </CardTitle>
                <CardDescription>
                  Choose how you want to receive notifications
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Email Channel */}
                <FormField
                  control={form.control}
                  name="email_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Email Notifications</FormLabel>
                        <FormDescription>
                          Receive notifications via email
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Push Channel */}
                <FormField
                  control={form.control}
                  name="push_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Push Notifications</FormLabel>
                        <FormDescription>
                          Receive browser and mobile push notifications
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* SMS Channel */}
                <FormField
                  control={form.control}
                  name="sms_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">SMS Notifications</FormLabel>
                        <FormDescription>
                          Receive important notifications via SMS (may incur costs)
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* In-App Notification Notice */}
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                  <div className="flex gap-3">
                    <span className="text-xl">📢</span>
                    <div>
                      <p className="font-semibold text-blue-900">In-App Notifications</p>
                      <p className="text-sm text-blue-800">
                        In-app notifications are always enabled so you never miss important updates
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quiet Hours Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className="text-2xl">🌙</span>
                  Quiet Hours
                </CardTitle>
                <CardDescription>
                  Configure times when you don't want to receive notifications (except urgent ones)
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Enable Quiet Hours */}
                <FormField
                  control={form.control}
                  name="quiet_hours_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between space-y-0">
                      <div className="space-y-0.5">
                        <FormLabel className="text-base font-semibold">Enable Quiet Hours</FormLabel>
                        <FormDescription>
                          Don't receive notifications during specified times
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {/* Quiet Hours Settings (shown only if enabled) */}
                {form.watch('quiet_hours_enabled') && (
                  <div className="space-y-4 pt-4 border-t">
                    {/* Timezone Selection */}
                    <FormField
                      control={form.control}
                      name="timezone"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-base font-semibold">Timezone</FormLabel>
                          <Select value={field.value} onValueChange={field.onChange}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue placeholder="Select timezone" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent className="max-h-64">
                              {TIMEZONES.map((tz) => (
                                <SelectItem key={tz.value} value={tz.value}>
                                  {tz.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormDescription>
                            Select your timezone for accurate quiet hours scheduling
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Quiet Hours Start Time */}
                    <FormField
                      control={form.control}
                      name="quiet_hours_start"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-base font-semibold">Start Time</FormLabel>
                          <FormControl>
                            <Input
                              type="time"
                              {...field}
                              className="max-w-xs"
                            />
                          </FormControl>
                          <FormDescription>
                            When to start quiet hours (24-hour format)
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Quiet Hours End Time */}
                    <FormField
                      control={form.control}
                      name="quiet_hours_end"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-base font-semibold">End Time</FormLabel>
                          <FormControl>
                            <Input
                              type="time"
                              {...field}
                              className="max-w-xs"
                            />
                          </FormControl>
                          <FormDescription>
                            When to end quiet hours (24-hour format)
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Example quiet hours */}
                    <div className="rounded-lg bg-gray-100 p-3 text-sm text-gray-700">
                      <p className="font-medium mb-2">Example:</p>
                      <p>
                        If you set quiet hours from 22:00 to 08:00, you won't receive notifications between 10 PM and 8 AM in your timezone
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Form Actions */}
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
              <Button
                type="button"
                variant="outline"
                onClick={handleReset}
                disabled={isSaving}
              >
                Reset
              </Button>
              <Button
                type="submit"
                disabled={isSaving || !form.formState.isDirty}
                className="min-w-32"
              >
                {isSaving ? (
                  <div className="flex items-center gap-2">
                    <LoadingSpinner size="sm" text="" />
                    Saving...
                  </div>
                ) : (
                  'Save Settings'
                )}
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
};

export default NotificationSettings;
