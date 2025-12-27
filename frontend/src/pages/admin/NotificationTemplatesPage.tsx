/**
 * Notification Templates Admin Page
 *
 * Page for managing notification templates in the admin panel
 * Provides a user-friendly interface for CRUD operations on templates
 */

import { NotificationTemplatesAdmin } from '@/components/admin/NotificationTemplatesAdmin';

/**
 * NotificationTemplatesPage Component
 * Wraps the NotificationTemplatesAdmin component for use in routing
 */
export default function NotificationTemplatesPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <NotificationTemplatesAdmin />
    </div>
  );
}
