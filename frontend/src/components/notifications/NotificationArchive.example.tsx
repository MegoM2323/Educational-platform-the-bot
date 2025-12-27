/**
 * NotificationArchive Component - Usage Examples
 *
 * This file demonstrates various ways to use the NotificationArchive component
 * for managing archived notifications in your application.
 */

import React, { useState } from 'react';
import { NotificationArchive } from './NotificationArchive';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/**
 * Example 1: Basic Usage
 * Simple implementation in a page or modal
 */
export const BasicArchiveExample = () => {
  return (
    <div className="p-6">
      <NotificationArchive />
    </div>
  );
};

/**
 * Example 2: Archive with Close Callback
 * Useful when displaying the archive in a modal or sidebar
 */
export const ArchiveWithCloseExample = () => {
  const [showArchive, setShowArchive] = useState(false);

  if (!showArchive) {
    return (
      <Button onClick={() => setShowArchive(true)}>
        View Archived Notifications
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <Card className="w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <NotificationArchive
            onClose={() => setShowArchive(false)}
          />
        </div>
      </Card>
    </div>
  );
};

/**
 * Example 3: Archive in a Tabbed Interface
 * Showing archive alongside active notifications
 */
export const TabbedNotificationsExample = () => {
  const [activeTab, setActiveTab] = useState<'active' | 'archive'>('active');

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button
          variant={activeTab === 'active' ? 'default' : 'outline'}
          onClick={() => setActiveTab('active')}
        >
          Active Notifications
        </Button>
        <Button
          variant={activeTab === 'archive' ? 'default' : 'outline'}
          onClick={() => setActiveTab('archive')}
        >
          Archived
        </Button>
      </div>

      <div>
        {activeTab === 'active' ? (
          <div className="p-6 border rounded-lg">
            {/* Your active notifications component here */}
            <p>Active notifications would be displayed here</p>
          </div>
        ) : (
          <NotificationArchive />
        )}
      </div>
    </div>
  );
};

/**
 * Example 4: Archive with Custom Styling
 * Using Tailwind CSS classes to customize appearance
 */
export const CustomStyledArchiveExample = () => {
  return (
    <div className="bg-gradient-to-br from-slate-50 to-slate-100 p-8 rounded-lg">
      <div className="max-w-6xl mx-auto">
        <NotificationArchive />
      </div>
    </div>
  );
};

/**
 * Example 5: Integration in Settings Page
 * Showing archive as part of notification management
 */
export const NotificationSettingsExample = () => {
  const [showArchive, setShowArchive] = useState(false);

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Notification Settings</h2>

        <div className="space-y-4">
          <div>
            <h3 className="font-semibold mb-2">Notification Management</h3>
            <p className="text-sm text-muted-foreground mb-4">
              View and manage your archived notifications
            </p>
            <Button
              onClick={() => setShowArchive(!showArchive)}
              variant="outline"
            >
              {showArchive ? 'Hide' : 'View'} Archived Notifications
            </Button>
          </div>

          {showArchive && (
            <div className="mt-6 border-t pt-6">
              <NotificationArchive
                onClose={() => setShowArchive(false)}
              />
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

/**
 * Example 6: Notification Dashboard
 * Shows archive alongside notification statistics
 */
export const NotificationDashboardExample = () => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">
            Unread
          </h3>
          <p className="text-3xl font-bold mt-2">5</p>
        </Card>
        <Card className="p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">
            Archived
          </h3>
          <p className="text-3xl font-bold mt-2">23</p>
        </Card>
        <Card className="p-6">
          <h3 className="font-semibold text-sm text-muted-foreground">
            Total
          </h3>
          <p className="text-3xl font-bold mt-2">28</p>
        </Card>
      </div>

      <NotificationArchive />
    </div>
  );
};

/**
 * Example 7: Responsive Archive View
 * Optimized for mobile, tablet, and desktop
 */
export const ResponsiveArchiveExample = () => {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-4 md:p-6">
        <NotificationArchive />
      </div>
    </div>
  );
};

/**
 * Example 8: Archive with Refresh Button
 * Allows users to manually refresh the list
 */
export const ArchiveWithRefreshExample = () => {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    // Increment key to force component re-render
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Archived Notifications</h2>
        <Button onClick={handleRefresh} variant="outline">
          Refresh
        </Button>
      </div>

      <NotificationArchive key={refreshKey} />
    </div>
  );
};

/**
 * Example 9: Controlled Archive View
 * Parent component manages the archive state
 */
export const ControlledArchiveExample = () => {
  const [selectedArchiveId, setSelectedArchiveId] = useState<number | null>(
    null
  );
  const [archiveStats, setArchiveStats] = useState({
    totalArchived: 0,
    pendingRestore: 0,
  });

  return (
    <div className="space-y-6">
      <Card className="p-6 bg-blue-50">
        <h3 className="font-semibold mb-4">Archive Statistics</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Total Archived</p>
            <p className="text-2xl font-bold">{archiveStats.totalArchived}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Pending Restore</p>
            <p className="text-2xl font-bold">
              {archiveStats.pendingRestore}
            </p>
          </div>
        </div>
      </Card>

      <NotificationArchive />
    </div>
  );
};

/**
 * Example 10: Full Application Example
 * Complete notification management system
 */
export const FullNotificationManagementExample = () => {
  const [view, setView] = useState<'inbox' | 'archive' | 'settings'>(
    'inbox'
  );

  return (
    <div className="min-h-screen bg-background">
      <div className="border-b">
        <div className="container mx-auto p-4">
          <nav className="flex gap-4">
            <button
              onClick={() => setView('inbox')}
              className={`px-4 py-2 ${
                view === 'inbox' ? 'border-b-2 border-primary' : ''
              }`}
            >
              Inbox
            </button>
            <button
              onClick={() => setView('archive')}
              className={`px-4 py-2 ${
                view === 'archive' ? 'border-b-2 border-primary' : ''
              }`}
            >
              Archive
            </button>
            <button
              onClick={() => setView('settings')}
              className={`px-4 py-2 ${
                view === 'settings' ? 'border-b-2 border-primary' : ''
              }`}
            >
              Settings
            </button>
          </nav>
        </div>
      </div>

      <div className="container mx-auto p-4 md:p-6">
        {view === 'inbox' && (
          <div className="p-6 border rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Your Notifications</h2>
            <p className="text-muted-foreground">
              Inbox notifications would be displayed here
            </p>
          </div>
        )}

        {view === 'archive' && <NotificationArchive />}

        {view === 'settings' && (
          <div className="p-6 border rounded-lg">
            <h2 className="text-2xl font-bold mb-4">Settings</h2>
            <p className="text-muted-foreground">
              Notification settings would be displayed here
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Integration Checklist
 *
 * When implementing NotificationArchive in your application:
 *
 * 1. API Integration
 *    - Ensure backend has /api/notifications/archive/ endpoint
 *    - Verify PATCH /api/notifications/{id}/restore/ endpoint exists
 *    - Check DELETE /api/notifications/{id}/ endpoint works
 *    - Test bulk endpoints if used
 *
 * 2. UI Components
 *    - Import required UI components (Button, Badge, Table, etc.)
 *    - Verify dark mode compatibility
 *    - Test responsive design on mobile devices
 *    - Check accessibility (keyboard navigation, ARIA labels)
 *
 * 3. Error Handling
 *    - Test network error scenarios
 *    - Verify error messages are user-friendly
 *    - Check toast notifications display correctly
 *    - Test loading states
 *
 * 4. Features
 *    - Test search functionality
 *    - Verify filtering works correctly
 *    - Test sorting options
 *    - Check pagination navigation
 *    - Test bulk selection and actions
 *    - Verify restore/delete dialogs appear
 *
 * 5. Performance
 *    - Monitor for N+1 queries
 *    - Check pagination efficiency
 *    - Verify table rendering with large datasets
 *    - Test search/filter performance
 *
 * 6. Testing
 *    - Run unit tests for component
 *    - Run unit tests for hook
 *    - Perform manual testing with real data
 *    - Test on multiple browsers
 *    - Test on different screen sizes
 */

// Export all examples
export const examples = {
  BasicArchiveExample,
  ArchiveWithCloseExample,
  TabbedNotificationsExample,
  CustomStyledArchiveExample,
  NotificationSettingsExample,
  NotificationDashboardExample,
  ResponsiveArchiveExample,
  ArchiveWithRefreshExample,
  ControlledArchiveExample,
  FullNotificationManagementExample,
};
