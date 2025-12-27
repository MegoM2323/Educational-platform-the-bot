/**
 * NotificationSettings Component - Usage Example
 *
 * This file demonstrates how to use the NotificationSettings component
 * and how it integrates with the rest of the application.
 */

import { NotificationSettings } from './NotificationSettings';

/**
 * Example 1: Basic usage in a route
 *
 * Add to your router configuration:
 */
export const notificationSettingsRoute = {
  path: '/settings/notifications',
  element: <NotificationSettings />,
  requiredRole: 'authenticated', // Any authenticated user can access
};

/**
 * Example 2: Full routing example using React Router
 */
export const createNotificationSettingsRouter = () => {
  return {
    path: '/settings',
    element: <div>Settings</div>,
    children: [
      {
        path: 'notifications',
        element: <NotificationSettings />,
      },
    ],
  };
};

/**
 * Example 3: Integration with sidebar/navigation
 *
 * Add to your navigation component:
 */
export const navigationExample = [
  {
    label: 'Settings',
    icon: 'Settings',
    href: '/settings',
    subItems: [
      {
        label: 'Profile',
        href: '/settings/profile',
      },
      {
        label: 'Notifications',
        href: '/settings/notifications', // Links to NotificationSettings
      },
      {
        label: 'Privacy',
        href: '/settings/privacy',
      },
    ],
  },
];

/**
 * Example 4: Using with the custom hook
 *
 * If you want to use notification settings elsewhere:
 */
import { useNotificationSettings, useUpdateNotificationSettings } from '@/hooks/useNotificationSettings';

export const CustomNotificationComponent = () => {
  const { data: settings, isLoading } = useNotificationSettings();
  const { mutate: updateSettings, isPending } = useUpdateNotificationSettings();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <p>Email notifications: {settings?.email_enabled ? 'On' : 'Off'}</p>
      <button
        onClick={() => updateSettings({ email_enabled: !settings?.email_enabled })}
        disabled={isPending}
      >
        {isPending ? 'Updating...' : 'Toggle Email Notifications'}
      </button>
    </div>
  );
};

/**
 * API Integration Details
 *
 * The component makes the following API calls:
 *
 * 1. GET /api/accounts/notification-settings/
 *    - Fetches current user's notification preferences
 *    - Called on component mount
 *    - Required authentication
 *
 * 2. PATCH /api/accounts/notification-settings/
 *    - Updates user's notification preferences
 *    - Sent when user saves changes
 *    - Accepts partial updates
 *    - Returns updated settings object
 *
 * Example API Response:
 * {
 *   "assignments_enabled": true,
 *   "materials_enabled": true,
 *   "messages_enabled": true,
 *   "payments_enabled": true,
 *   "invoices_enabled": true,
 *   "system_enabled": true,
 *   "email_enabled": true,
 *   "push_enabled": true,
 *   "sms_enabled": false,
 *   "quiet_hours_enabled": false,
 *   "quiet_hours_start": "22:00",
 *   "quiet_hours_end": "08:00",
 *   "timezone": "UTC"
 * }
 */

/**
 * Features
 *
 * 1. Notification Types
 *    - Assignments: Toggle notifications for assignment-related events
 *    - Materials: Toggle notifications for new materials
 *    - Messages: Toggle notifications for direct messages and replies
 *    - Payments: Toggle notifications for payment-related events
 *    - Invoices: Toggle notifications for invoice updates
 *    - System: Toggle notifications for system announcements
 *
 * 2. Notification Channels
 *    - Email: Receive notifications via email
 *    - Push: Receive browser and mobile push notifications
 *    - SMS: Receive notifications via SMS (optional, may incur costs)
 *    - In-App: Always enabled (cannot be disabled)
 *
 * 3. Quiet Hours
 *    - Optional feature to prevent notifications during specified times
 *    - Supports timezone selection for accurate scheduling
 *    - Start and end times in 24-hour format (HH:MM)
 *    - Example: Quiet hours from 22:00 to 08:00 (10 PM to 8 AM)
 *
 * 4. User Experience
 *    - Loading state with spinner during initial fetch
 *    - Save button disabled when form is unchanged
 *    - Success message after successful save (3-second auto-dismiss)
 *    - Error messages with clear explanations
 *    - Reset button to discard changes
 *    - Responsive design for mobile/tablet/desktop
 *    - Accessible toggle switches with labels
 *    - Helpful descriptions for each setting
 */

/**
 * Responsive Design
 *
 * - Mobile (< 640px): Full width, stacked sections, optimized touch targets
 * - Tablet (640px - 1024px): 2-column layout for better use of space
 * - Desktop (> 1024px): 3-column layout with max-width container
 *
 * The component uses Tailwind CSS responsive classes:
 * - Form sections stack vertically on mobile
 * - Toggle switches have adequate spacing for touch
 * - Input fields are full-width on mobile, constrained on desktop
 */

/**
 * Error Handling
 *
 * The component handles the following error scenarios:
 *
 * 1. 401 Unauthorized
 *    - User is not authenticated
 *    - Navigates to /auth page
 *    - Shows appropriate error message
 *
 * 2. Network Error
 *    - Connection timeout or failed request
 *    - Shows "Failed to load notification settings" error
 *    - Allows user to refresh the page
 *
 * 3. Validation Error
 *    - Invalid input format (e.g., bad time format)
 *    - Shows specific validation error message
 *    - Prevents form submission
 *
 * 4. Server Error
 *    - 400 Bad Request, 500 Internal Server Error
 *    - Shows error message from API or generic error
 *    - Allows user to retry
 */

/**
 * Testing Strategy
 *
 * The component includes comprehensive tests for:
 *
 * 1. Rendering
 *    - All sections render correctly
 *    - All toggles and inputs are present
 *    - Loading state is displayed
 *
 * 2. Interactions
 *    - Toggle switches change state
 *    - Quiet hours time inputs show/hide appropriately
 *    - Timezone selector is available when quiet hours enabled
 *    - Form buttons are enabled/disabled correctly
 *
 * 3. API Integration
 *    - GET request fetches settings on mount
 *    - PATCH request sends changes to API
 *    - Error responses are handled gracefully
 *    - Success responses update the UI
 *
 * 4. Form Management
 *    - Changes are tracked (dirty state)
 *    - Reset button restores original values
 *    - Save button is disabled when unchanged
 *    - Validation prevents invalid submissions
 */
