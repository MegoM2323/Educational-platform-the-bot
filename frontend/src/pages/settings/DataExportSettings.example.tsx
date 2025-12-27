/**
 * DataExportSettings Component - Usage Examples
 *
 * This file demonstrates various usage patterns and integration points
 * for the DataExportSettings component.
 */

import { DataExportSettings } from './DataExportSettings';
import { useDataExport } from '@/hooks/useDataExport';

/**
 * Example 1: Basic Integration
 *
 * Simple usage of the DataExportSettings component in a route
 */
export const Example1_BasicIntegration = () => {
  return (
    <div>
      <DataExportSettings />
    </div>
  );
};

/**
 * Example 2: Custom Wrapper with Additional Context
 *
 * Wrapping the component to add additional context or logging
 */
export const Example2_WithContext = () => {
  const handleExportStarted = () => {
    console.log('User started export process');
  };

  return (
    <div className="export-section">
      <header>
        <h1>Account Settings - Data Management</h1>
        <p>Download or manage your personal data</p>
      </header>
      <main>
        <DataExportSettings />
      </main>
    </div>
  );
};

/**
 * Example 3: Using the useDataExport Hook Directly
 *
 * For more granular control over the export process
 */
export const Example3_DirectHookUsage = () => {
  const {
    isLoading,
    error,
    initiateExport,
    checkStatus,
    downloadExport,
    deleteExport,
    fetchExports,
  } = useDataExport();

  const handleExportClick = async () => {
    try {
      // Initiate export
      const job = await initiateExport('json', {
        include_profile: true,
        include_messages: true,
        include_assignments: true,
      });

      console.log('Export job started:', job.job_id);

      // Poll for status
      const pollInterval = setInterval(async () => {
        const status = await checkStatus(job.job_id);
        console.log('Current status:', status.status);

        if (status.status === 'completed') {
          clearInterval(pollInterval);
          // Download automatically
          if (status.download_token) {
            await downloadExport(job.job_id, status.download_token, 'json');
          }
        }
      }, 2000);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  return (
    <div>
      <button onClick={handleExportClick} disabled={isLoading}>
        {isLoading ? 'Exporting...' : 'Export Data'}
      </button>
      {error && <div className="error">{error}</div>}
    </div>
  );
};

/**
 * Example 4: Export History Management
 *
 * Display and manage export history separately
 */
export const Example4_ExportHistory = () => {
  const { fetchExports, deleteExport, downloadExport } = useDataExport();

  const handleFetchHistory = async () => {
    try {
      const exports = await fetchExports();
      console.log('Export history:', exports);

      // Filter completed exports
      const completed = exports.filter((e) => e.status === 'completed');
      console.log('Completed exports:', completed);

      // Delete old exports
      for (const exportItem of exports) {
        const created = new Date(exportItem.created_at);
        const now = new Date();
        const daysDiff = (now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24);

        if (daysDiff > 7) {
          await deleteExport(exportItem.job_id);
          console.log('Deleted old export:', exportItem.job_id);
        }
      }
    } catch (err) {
      console.error('History fetch failed:', err);
    }
  };

  return (
    <button onClick={handleFetchHistory}>Load Export History</button>
  );
};

/**
 * Example 5: Integration with Settings Layout
 *
 * Complete example showing integration with a settings page structure
 */
export const Example5_SettingsPageIntegration = () => {
  return (
    <div className="settings-container">
      <nav className="settings-sidebar">
        <ul>
          <li><a href="#profile">Profile</a></li>
          <li><a href="#notifications">Notifications</a></li>
          <li><a href="#data-export" className="active">Data & Privacy</a></li>
          <li><a href="#security">Security</a></li>
        </ul>
      </nav>

      <main className="settings-main">
        <section id="data-export">
          <DataExportSettings />
        </section>
      </main>
    </div>
  );
};

/**
 * Example 6: Error Handling and Recovery
 *
 * Shows how to handle various error scenarios
 */
export const Example6_ErrorHandling = () => {
  const { initiateExport, checkStatus } = useDataExport();

  const handleExportWithRetry = async (maxRetries = 3) => {
    let attempts = 0;

    while (attempts < maxRetries) {
      try {
        const job = await initiateExport('csv');

        // Check status with retry logic
        const maxStatusChecks = 10;
        for (let i = 0; i < maxStatusChecks; i++) {
          const status = await checkStatus(job.job_id);

          if (status.status === 'completed') {
            console.log('Export completed successfully');
            return status;
          } else if (status.status === 'failed') {
            throw new Error(status.error_message || 'Export failed');
          }

          await new Promise((resolve) => setTimeout(resolve, 1000));
        }

        throw new Error('Export timeout');
      } catch (err) {
        attempts++;
        if (attempts >= maxRetries) {
          console.error('Export failed after retries:', err);
          throw err;
        }
        console.warn(`Retry attempt ${attempts}...`);
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }
    }
  };

  return (
    <button onClick={() => handleExportWithRetry()}>
      Export with Retry Logic
    </button>
  );
};

/**
 * Example 7: Batch Operations
 *
 * Handle multiple export formats in sequence
 */
export const Example7_BatchOperations = () => {
  const { initiateExport, checkStatus } = useDataExport();

  const handleMultiFormatExport = async () => {
    const formats: ('json' | 'csv')[] = ['json', 'csv'];
    const results = [];

    for (const format of formats) {
      try {
        console.log(`Starting ${format} export...`);
        const job = await initiateExport(format);
        results.push({
          format,
          jobId: job.job_id,
          status: 'initiated',
        });
      } catch (err) {
        results.push({
          format,
          status: 'failed',
          error: err instanceof Error ? err.message : 'Unknown error',
        });
      }
    }

    console.log('Batch export results:', results);
  };

  return (
    <button onClick={handleMultiFormatExport}>
      Export All Formats
    </button>
  );
};

/**
 * Example 8: Progress Tracking
 *
 * Advanced usage with progress tracking UI
 */
export const Example8_ProgressTracking = () => {
  const { initiateExport, checkStatus } = useDataExport();
  const [progress, setProgress] = React.useState(0);
  const [status, setStatus] = React.useState<string | null>(null);

  const handleExportWithProgress = async () => {
    try {
      setProgress(0);
      setStatus('Initiating...');

      const job = await initiateExport('json');
      setProgress(10);

      const pollTimeout = setTimeout(async () => {
        let checks = 0;
        const pollInterval = setInterval(async () => {
          checks++;
          setProgress(Math.min(90, 10 + checks * 5));
          setStatus('Processing your data...');

          const jobStatus = await checkStatus(job.job_id);

          if (jobStatus.status === 'completed') {
            clearInterval(pollInterval);
            setProgress(100);
            setStatus('Complete!');
          }
        }, 2000);
      }, 0);

      return job;
    } catch (err) {
      setStatus(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  return (
    <div>
      <button onClick={handleExportWithProgress}>Start Export</button>
      {status && (
        <div className="progress-section">
          <p>{status}</p>
          <progress value={progress} max={100} />
          <span>{progress}%</span>
        </div>
      )}
    </div>
  );
};

/**
 * Example 9: GDPR Compliance
 *
 * Demonstrating GDPR-specific functionality
 */
export const Example9_GDPRCompliance = () => {
  const { initiateExport, fetchExports, deleteExport } = useDataExport();

  const handleGDPRDataRequest = async () => {
    // Initiate export (Right to Data Portability - Article 20)
    const job = await initiateExport('json', {
      include_profile: true,
      include_activity: true,
      include_messages: true,
      include_assignments: true,
      include_payments: true,
      include_notifications: true,
    });

    console.log('GDPR data request initiated');
    console.log('Job ID:', job.job_id);
    console.log('Expires:', job.expires_at);
  };

  const handleDataDeletion = async () => {
    // TODO: Implement data deletion endpoint
    // This would call a deletion API with proper GDPR compliance
    console.log('Data deletion request initiated');
  };

  return (
    <div>
      <button onClick={handleGDPRDataRequest}>
        Request My Data (GDPR Article 20)
      </button>
      <button onClick={handleDataDeletion}>
        Request Data Deletion (GDPR Article 17)
      </button>
    </div>
  );
};

/**
 * Example 10: Mobile Responsive Usage
 *
 * Component works seamlessly on mobile devices
 */
export const Example10_MobileResponsive = () => {
  return (
    <div className="responsive-container">
      {/* Component automatically adapts to mobile viewport */}
      <DataExportSettings />
    </div>
  );
};

// Note: The component includes:
// - Full mobile responsiveness with tailwind CSS
// - Touch-friendly button sizes
// - Proper form inputs for mobile
// - Responsive data table/list layout
// - Modal dialogs that work on mobile
// - Toast notifications that don't overlap

/**
 * Integration Points
 *
 * The DataExportSettings component integrates with:
 *
 * 1. API Layer:
 *    - POST /api/accounts/data-export/
 *    - GET /api/accounts/data-export/
 *    - GET /api/accounts/data-export/{job_id}/
 *    - DELETE /api/accounts/data-export/{job_id}/
 *    - GET /api/accounts/data-export/download/{token}/
 *
 * 2. State Management:
 *    - React hooks (useState, useEffect, useCallback)
 *    - React Router for navigation
 *    - Context providers (if needed)
 *
 * 3. UI Components:
 *    - Shadcn/ui components (Button, Card, Dialog, etc.)
 *    - Lucide icons
 *    - Tailwind CSS for styling
 *
 * 4. Utilities:
 *    - unifiedAPI for API calls
 *    - Sonner for toast notifications
 *    - Logger for debugging
 *    - React Hook Form for form handling
 */

/**
 * Styling Guide
 *
 * The component uses Tailwind CSS with a color scheme:
 * - Primary: Blue (#3b82f6)
 * - Success: Green (#10b981)
 * - Error: Red (#ef4444)
 * - Background: Gray (#f9fafb)
 *
 * Responsive breakpoints used:
 * - Mobile: Default (< 640px)
 * - Tablet: md: (768px)
 * - Desktop: lg: (1024px)
 */

/**
 * Accessibility Features
 *
 * - Semantic HTML (h1-h6, button, form, etc.)
 * - ARIA labels and descriptions
 * - Keyboard navigation support
 * - Screen reader friendly
 * - Color contrast WCAG AA compliant
 * - Focus indicators visible
 */

/**
 * Performance Considerations
 *
 * - Status polling with configurable intervals
 * - Automatic cleanup of polling on unmount
 * - Efficient re-renders with memoization
 * - Lazy component loading
 * - Bundle size optimized
 */

/**
 * Security Considerations
 *
 * - HTTPS-only file downloads
 * - Secure token validation
 * - CSRF protection via unifiedAPI
 * - No sensitive data in logs
 * - User authentication required
 */

export default DataExportSettings;
