import React from 'react';
import { Button } from '@/components/ui/button';
import { ExportDialog, ExportParams } from './ExportDialog';
import { useExportDialog } from '@/hooks/useExportDialog';
import { logger } from '@/utils/logger';

/**
 * Example: Analytics Export Dialog
 *
 * Demonstrates how to use the ExportDialog component with:
 * - Custom export handler
 * - Format and scope selection
 * - Scheduling options
 * - Error handling
 */
export const ExportDialogExample: React.FC = () => {
  // Hook for managing export dialog state
  const {
    isOpen,
    openDialog,
    closeDialog,
    exportData,
    isLoading,
    error,
    success,
  } = useExportDialog(
    async (params: ExportParams) => {
      logger.info('[ExportDialogExample] Export params:', params);

      // Simulate API call
      return new Promise((resolve, reject) => {
        setTimeout(() => {
          if (Math.random() > 0.1) {
            logger.info('[ExportDialogExample] Export successful');
            resolve();
          } else {
            reject(new Error('Export service temporarily unavailable'));
          }
        }, 1500);
      });
    },
    {
      defaultFormat: 'csv',
      defaultScope: 'all',
      supportedFormats: ['csv', 'excel', 'pdf'],
      supportedScopes: ['current', 'all'],
      includeScheduling: true,
      includeFormatOptions: true,
    }
  );

  return (
    <div className="space-y-4 p-6">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold">Export Dialog Example</h2>
        <p className="text-muted-foreground">
          Click the button below to open the export dialog
        </p>
      </div>

      {/* Status Information */}
      {success && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-md">
          <p className="text-sm text-green-900">
            Export initiated! Check your email for the file.
          </p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-900">Error: {error}</p>
        </div>
      )}

      {/* Export Button */}
      <Button
        onClick={openDialog}
        size="lg"
        disabled={isLoading}
      >
        Open Export Dialog
      </Button>

      {/* Export Dialog */}
      <ExportDialog
        isOpen={isOpen}
        onOpenChange={closeDialog}
        title="Export Analytics Data"
        description="Choose your preferred format and export options to download analytics data"
        onExport={exportData}
        isLoading={isLoading}
        defaultFormat="csv"
        defaultScope="all"
        supportedFormats={['csv', 'excel', 'pdf']}
        supportedScopes={['current', 'selected', 'all']}
        includeScheduling={true}
        includeFormatOptions={true}
      />

      {/* Instructions */}
      <div className="border rounded-lg p-4 space-y-2">
        <h3 className="font-semibold">Features:</h3>
        <ul className="list-disc list-inside text-sm space-y-1 text-muted-foreground">
          <li>Select from multiple export formats (CSV, Excel, PDF)</li>
          <li>Choose data scope (current, selected, or all)</li>
          <li>Customize file naming</li>
          <li>Apply formatting options</li>
          <li>Schedule exports with email delivery</li>
          <li>Set recurring exports (daily, weekly, monthly)</li>
          <li>Progress indication during export</li>
          <li>Error handling and notifications</li>
        </ul>
      </div>

      {/* Usage Code */}
      <div className="border rounded-lg p-4 bg-muted">
        <h3 className="font-semibold mb-2">Usage:</h3>
        <pre className="text-xs overflow-auto">
{`import { useExportDialog } from '@/hooks/useExportDialog';
import { ExportDialog } from '@/components/common/ExportDialog';

const MyComponent = () => {
  const {
    isOpen,
    openDialog,
    closeDialog,
    exportData,
    isLoading,
  } = useExportDialog(
    async (params) => {
      // Call your export API
      await api.exportAnalytics(params);
    }
  );

  return (
    <>
      <Button onClick={openDialog}>Export</Button>
      <ExportDialog
        isOpen={isOpen}
        onOpenChange={closeDialog}
        onExport={exportData}
        isLoading={isLoading}
        supportedFormats={['csv', 'excel', 'pdf']}
      />
    </>
  );
};`}
        </pre>
      </div>
    </div>
  );
};

export default ExportDialogExample;
