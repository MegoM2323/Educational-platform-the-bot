import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';

/**
 * Notification settings types
 */
export interface NotificationSettingsData {
  // Notification types
  assignments_enabled: boolean;
  materials_enabled: boolean;
  messages_enabled: boolean;
  payments_enabled: boolean;
  invoices_enabled: boolean;
  system_enabled: boolean;

  // Channels
  email_enabled: boolean;
  push_enabled: boolean;
  sms_enabled: boolean;

  // Quiet hours
  quiet_hours_enabled: boolean;
  quiet_hours_start: string; // Format: HH:MM
  quiet_hours_end: string; // Format: HH:MM
  timezone: string;
}

/**
 * Query configuration for notification settings
 */
const NOTIFICATION_SETTINGS_QUERY_CONFIG = {
  staleTime: 5 * 60 * 1000, // 5 minutes
  gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
  retry: 2,
  refetchOnWindowFocus: false,
  refetchOnMount: false,
  refetchOnReconnect: true,
};

/**
 * Hook for fetching notification settings
 *
 * @returns Query result with notification settings
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useNotificationSettings();
 *
 * if (isLoading) return <div>Loading...</div>;
 * if (error) return <div>Error: {error.message}</div>;
 *
 * return <div>Email enabled: {data?.email_enabled}</div>;
 * ```
 */
export const useNotificationSettings = (): UseQueryResult<NotificationSettingsData, Error> => {
  return useQuery({
    queryKey: ['notificationSettings'],
    queryFn: async (): Promise<NotificationSettingsData> => {
      logger.debug('[useNotificationSettings] Fetching notification settings...');

      try {
        const response = await unifiedAPI.fetch(
          '/accounts/notification-settings/',
          'GET'
        );

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Unauthorized');
          }

          throw new Error(`Failed to fetch notification settings (${response.status})`);
        }

        const data = await response.json();
        logger.debug('[useNotificationSettings] Settings fetched:', data);

        return data.data || data;
      } catch (error) {
        logger.error('[useNotificationSettings] Error fetching settings:', error);
        throw error instanceof Error ? error : new Error('Failed to fetch notification settings');
      }
    },
    ...NOTIFICATION_SETTINGS_QUERY_CONFIG,
  });
};

/**
 * Hook for updating notification settings
 *
 * @returns Mutation result for updating settings
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useUpdateNotificationSettings();
 *
 * const handleSave = (settings: NotificationSettingsData) => {
 *   mutate(settings);
 * };
 *
 * return (
 *   <button onClick={() => handleSave(newSettings)} disabled={isPending}>
 *     {isPending ? 'Saving...' : 'Save'}
 *   </button>
 * );
 * ```
 */
export const useUpdateNotificationSettings = (): UseMutationResult<
  NotificationSettingsData,
  Error,
  Partial<NotificationSettingsData>
> => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (settings: Partial<NotificationSettingsData>) => {
      logger.debug('[useUpdateNotificationSettings] Saving settings:', settings);

      try {
        const response = await unifiedAPI.fetch(
          '/accounts/notification-settings/',
          'PATCH',
          settings
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage =
            errorData.error ||
            errorData.detail ||
            `Failed to update settings (${response.status})`;

          throw new Error(errorMessage);
        }

        const data = await response.json();
        logger.debug('[useUpdateNotificationSettings] Settings updated:', data);

        return data.data || data;
      } catch (error) {
        logger.error('[useUpdateNotificationSettings] Error updating settings:', error);
        throw error instanceof Error ? error : new Error('Failed to update notification settings');
      }
    },
    onSuccess: (data) => {
      logger.debug('[useUpdateNotificationSettings] Invalidating cache');
      // Invalidate the notification settings query to refresh data
      queryClient.invalidateQueries({ queryKey: ['notificationSettings'] });
    },
  });
};

/**
 * Hook combining fetch and update operations
 *
 * @returns Object with data, loading state, and update function
 *
 * @example
 * ```tsx
 * const { settings, isLoading, updateSettings } = useNotificationSettingsComplete();
 *
 * const handleToggle = async (field: string, value: boolean) => {
 *   await updateSettings({
 *     ...settings,
 *     [field]: value,
 *   });
 * };
 * ```
 */
export const useNotificationSettingsComplete = () => {
  const { data: settings, isLoading: isLoadingSettings, error: fetchError } = useNotificationSettings();
  const { mutate: updateSettings, isPending: isUpdating, error: updateError } = useUpdateNotificationSettings();

  return {
    settings,
    isLoading: isLoadingSettings,
    isUpdating,
    error: fetchError || updateError,
    updateSettings,
  };
};
