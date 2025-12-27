import React from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ExportDialog, ExportParams } from './ExportDialog';
import { useExportDialog } from '@/hooks/useExportDialog';
import { logger } from '@/utils/logger';

/**
 * Integration Example: Analytics Export with Real API
 *
 * This example demonstrates how to integrate the ExportDialog with
 * a real backend API for exporting analytics data.
 *
 * Features:
 * - Real API integration
 * - File download handling
 * - Error handling and recovery
 * - Success notifications
 * - Support for scheduled exports
 */
export const AnalyticsExportIntegration: React.FC = () => {
  const { isOpen, openDialog, closeDialog, exportData, isLoading, error, success } =
    useExportDialog(
      async (params: ExportParams) => {
        logger.info('[AnalyticsExport] Exporting with params:', params);

        // Build API endpoint
        const endpoint = `/api/analytics/export/`;

        try {
          const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Token ${localStorage.getItem('authToken') || ''}`,
            },
            body: JSON.stringify({
              format: params.format,
              scope: params.scope,
              file_name: params.fileName,
              include_formatting: params.includeFormatting,
              schedule_export: params.scheduleExport,
              schedule_email: params.scheduleEmail,
              schedule_frequency: params.scheduleFrequency,
            }),
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Export failed');
          }

          const data = await response.json();

          // For immediate exports, download the file
          if (!params.scheduleExport && data.download_url) {
            const link = document.createElement('a');
            link.href = data.download_url;
            link.download = `${params.fileName}.${getFileExtension(params.format)}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }

          logger.info('[AnalyticsExport] Export completed:', data);
        } catch (error) {
          logger.error('[AnalyticsExport] Export failed:', error);
          throw error;
        }
      },
      {
        defaultFormat: 'csv',
        defaultScope: 'all',
        supportedFormats: ['csv', 'excel', 'pdf'],
        supportedScopes: ['current', 'selected', 'all'],
        includeScheduling: true,
        includeFormatOptions: true,
      }
    );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Analytics Export Integration</h1>
        <p className="text-muted-foreground mt-2">
          Example of integrating ExportDialog with a real analytics API
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Dialog Status</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{isOpen ? 'Open' : 'Closed'}</p>
            <p className="text-xs text-muted-foreground mt-1">Current dialog state</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Loading State</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{isLoading ? 'Loading' : 'Ready'}</p>
            <p className="text-xs text-muted-foreground mt-1">API request status</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Last Result</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{success ? 'Success' : error ? 'Error' : 'Pending'}</p>
            <p className="text-xs text-muted-foreground mt-1">Last operation outcome</p>
          </CardContent>
        </Card>
      </div>

      {/* Error Display */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="text-red-900 text-sm">Error</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-red-800">{error}</CardContent>
        </Card>
      )}

      {/* Success Display */}
      {success && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader>
            <CardTitle className="text-green-900 text-sm">Success</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-green-800">
            Export has been initiated successfully. Check your downloads or email for the file.
          </CardContent>
        </Card>
      )}

      {/* Controls */}
      <div className="flex gap-4">
        <Button onClick={openDialog} disabled={isLoading} size="lg">
          Open Export Dialog
        </Button>
      </div>

      {/* ExportDialog Component */}
      <ExportDialog
        isOpen={isOpen}
        onOpenChange={closeDialog}
        title="Export Analytics Data"
        description="Select your preferred format and export options"
        onExport={exportData}
        isLoading={isLoading}
        supportedFormats={['csv', 'excel', 'pdf']}
        supportedScopes={['current', 'selected', 'all']}
        includeScheduling={true}
        includeFormatOptions={true}
      />

      {/* Documentation */}
      <Card>
        <CardHeader>
          <CardTitle>Implementation Details</CardTitle>
          <CardDescription>How this integration works</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-semibold mb-2">API Endpoint</h4>
            <code className="block bg-muted p-3 rounded text-sm overflow-auto">
              POST /api/analytics/export/
            </code>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Request Body</h4>
            <pre className="bg-muted p-3 rounded text-xs overflow-auto">
{`{
  format: "csv" | "excel" | "pdf",
  scope: "current" | "selected" | "all",
  file_name: string,
  include_formatting: boolean,
  schedule_export: boolean,
  schedule_email: string | null,
  schedule_frequency: "once" | "daily" | "weekly" | "monthly" | null
}`}
            </pre>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Response (Immediate Export)</h4>
            <pre className="bg-muted p-3 rounded text-xs overflow-auto">
{`{
  success: true,
  download_url: "https://api.example.com/files/export_123.csv",
  file_size: 1024000,
  created_at: "2024-01-15T10:30:00Z"
}`}
            </pre>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Response (Scheduled Export)</h4>
            <pre className="bg-muted p-3 rounded text-xs overflow-auto">
{`{
  success: true,
  scheduled_export_id: 42,
  scheduled_at: "2024-01-15T10:30:00Z",
  email: "user@example.com",
  frequency: "weekly"
}`}
            </pre>
          </div>

          <div>
            <h4 className="font-semibold mb-2">File Extension Mapping</h4>
            <pre className="bg-muted p-3 rounded text-xs overflow-auto">
{`csv   → .csv
excel → .xlsx
pdf   → .pdf`}
            </pre>
          </div>

          <div>
            <h4 className="font-semibold mb-2">Flow</h4>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              <li>User clicks "Open Export Dialog"</li>
              <li>Dialog opens with format/scope options</li>
              <li>User configures export parameters</li>
              <li>User clicks "Export {FORMAT}"</li>
              <li>ExportDialog calls onExport with params</li>
              <li>API request is sent to /api/analytics/export/</li>
              <li>For immediate exports: file is downloaded automatically</li>
              <li>For scheduled exports: confirmation is shown to user</li>
              <li>Toast notification indicates success or error</li>
            </ol>
          </div>
        </CardContent>
      </Card>

      {/* Code Example */}
      <Card>
        <CardHeader>
          <CardTitle>Code Example</CardTitle>
          <CardDescription>How to implement this in your components</CardDescription>
        </CardHeader>
        <CardContent>
          <pre className="bg-muted p-4 rounded text-xs overflow-auto">
{`import { useExportDialog } from '@/hooks/useExportDialog';
import { ExportDialog } from '@/components/common/ExportDialog';

export const MyAnalytics = () => {
  const { isOpen, openDialog, closeDialog, exportData } =
    useExportDialog(
      async (params) => {
        const response = await fetch('/api/analytics/export/', {
          method: 'POST',
          body: JSON.stringify(params),
        });

        const data = await response.json();

        // Download file for immediate exports
        if (!params.scheduleExport && data.download_url) {
          window.location.href = data.download_url;
        }
      }
    );

  return (
    <>
      <Button onClick={openDialog}>Export Data</Button>
      <ExportDialog
        isOpen={isOpen}
        onOpenChange={closeDialog}
        onExport={exportData}
        supportedFormats={['csv', 'excel', 'pdf']}
        includeScheduling={true}
      />
    </>
  );
};`}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
};

/**
 * Get file extension for format
 */
function getFileExtension(format: string): string {
  switch (format) {
    case 'csv':
      return 'csv';
    case 'excel':
      return 'xlsx';
    case 'pdf':
      return 'pdf';
    default:
      return 'txt';
  }
}

export default AnalyticsExportIntegration;
