import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  ChevronLeft,
  AlertCircle,
  CheckCircle2,
  Download,
  Trash2,
  Clock,
  FileJson,
  FileSpreadsheet,
  Shield,
  Info,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { unifiedAPI } from '@/integrations/api/unifiedClient';
import { logger } from '@/utils/logger';
import { toast } from 'sonner';

/**
 * Data export form validation schema
 */
const dataExportSchema = z.object({
  format: z.enum(['json', 'csv']).default('json'),
  include_profile: z.boolean().default(true),
  include_activity: z.boolean().default(true),
  include_messages: z.boolean().default(true),
  include_assignments: z.boolean().default(true),
  include_payments: z.boolean().default(true),
  include_notifications: z.boolean().default(true),
});

type DataExportFormData = z.infer<typeof dataExportSchema>;

/**
 * Export history item from API
 */
interface ExportHistoryItem {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  format: 'json' | 'csv';
  file_path?: string;
  file_size?: number;
  created_at: string;
  expires_at: string;
  download_token?: string;
  error_message?: string;
}

/**
 * DataExportSettings Component
 *
 * Allows users to:
 * - Initiate GDPR-compliant data export in JSON or CSV format
 * - Select what data to include (profile, activity, messages, etc.)
 * - View export history with download links
 * - Delete export requests
 * - Understand their GDPR rights
 *
 * @example
 * ```tsx
 * <DataExportSettings />
 * ```
 */
export const DataExportSettings = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [exportHistory, setExportHistory] = useState<ExportHistoryItem[]>([]);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteJobId, setDeleteJobId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [exportSuccessJobId, setExportSuccessJobId] = useState<string | null>(null);
  const [statusCheckInterval, setStatusCheckInterval] = useState<NodeJS.Timeout | null>(null);

  const form = useForm<DataExportFormData>({
    resolver: zodResolver(dataExportSchema),
    mode: 'onBlur',
    defaultValues: {
      format: 'json',
      include_profile: true,
      include_activity: true,
      include_messages: true,
      include_assignments: true,
      include_payments: true,
      include_notifications: true,
    },
  });

  /**
   * Fetch export history on component mount
   */
  useEffect(() => {
    const fetchExportHistory = async () => {
      try {
        setIsLoading(true);
        setLoadError(null);

        logger.debug('[DataExportSettings] Fetching export history...');

        const response = await unifiedAPI.fetch(
          '/accounts/data-export/',
          'GET'
        );

        if (!response.ok) {
          if (response.status === 401) {
            navigate('/auth');
            return;
          }

          throw new Error(`Failed to fetch export history (${response.status})`);
        }

        const data = await response.json();
        logger.debug('[DataExportSettings] Fetched export history:', data);

        // Handle both array and paginated responses
        const exports = Array.isArray(data) ? data : data.results || data.data || [];
        setExportHistory(exports);
      } catch (error) {
        logger.error('[DataExportSettings] Error fetching export history:', error);
        const errorMessage =
          error instanceof Error ? error.message : 'Failed to load export history';
        setLoadError(errorMessage);
        toast.error('Failed to load export history');
      } finally {
        setIsLoading(false);
      }
    };

    fetchExportHistory();
  }, [navigate]);

  /**
   * Check status of ongoing export
   */
  const checkExportStatus = async (jobId: string) => {
    try {
      logger.debug(`[DataExportSettings] Checking status for job ${jobId}...`);

      const response = await unifiedAPI.fetch(
        `/accounts/data-export/${jobId}/`,
        'GET'
      );

      if (!response.ok) {
        throw new Error(`Failed to check export status (${response.status})`);
      }

      const data = await response.json();
      const updatedExport = data.data || data;

      // Update export history with new status
      setExportHistory((prev) =>
        prev.map((item) =>
          item.job_id === jobId ? { ...item, ...updatedExport } : item
        )
      );

      // If completed or failed, stop polling
      if (
        updatedExport.status === 'completed' ||
        updatedExport.status === 'failed'
      ) {
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval);
          setStatusCheckInterval(null);
        }

        if (updatedExport.status === 'completed') {
          setExportSuccessJobId(jobId);
          toast.success('Your data export is ready for download!');
        }
      }

      return updatedExport;
    } catch (error) {
      logger.error(
        `[DataExportSettings] Error checking status for ${jobId}:`,
        error
      );
      throw error;
    }
  };

  /**
   * Handle data export form submission
   */
  const handleExport = async (values: DataExportFormData) => {
    try {
      setIsExporting(true);
      setExportError(null);
      setExportSuccessJobId(null);

      logger.debug('[DataExportSettings] Initiating data export...', values);

      // Build query params
      const params = new URLSearchParams();
      params.set('format', values.format);

      // Add scope parameters if API supports selective export
      // (This is for future enhancement if backend supports it)
      const scopeParams = {
        include_profile: values.include_profile,
        include_activity: values.include_activity,
        include_messages: values.include_messages,
        include_assignments: values.include_assignments,
        include_payments: values.include_payments,
        include_notifications: values.include_notifications,
      };

      const response = await unifiedAPI.fetch(
        `/accounts/data-export/?${params.toString()}`,
        'POST',
        { scope: scopeParams }
      );

      if (!response.ok) {
        if (response.status === 401) {
          navigate('/auth');
          return;
        }

        const errorData = await response.json().catch(() => ({}));
        const errorMessage =
          errorData.error ||
          errorData.detail ||
          `Failed to initiate export (${response.status})`;

        throw new Error(errorMessage);
      }

      const data = await response.json();
      const exportJob = data.data || data;

      logger.debug('[DataExportSettings] Export job created:', exportJob);

      // Add to history
      const newExport: ExportHistoryItem = {
        job_id: exportJob.job_id,
        status: 'queued',
        format: values.format,
        created_at: new Date().toISOString(),
        expires_at: exportJob.expires_at,
      };

      setExportHistory((prev) => [newExport, ...prev]);
      setExportSuccessJobId(exportJob.job_id);

      toast.success('Data export initiated! It will be ready shortly.');

      // Start polling for status updates
      const interval = setInterval(() => {
        checkExportStatus(exportJob.job_id);
      }, 2000); // Check every 2 seconds
      setStatusCheckInterval(interval);

      // Stop polling after 5 minutes
      setTimeout(() => {
        if (interval) {
          clearInterval(interval);
          setStatusCheckInterval(null);
        }
      }, 5 * 60 * 1000);
    } catch (error) {
      logger.error('[DataExportSettings] Error initiating export:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to initiate data export';
      setExportError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsExporting(false);
    }
  };

  /**
   * Download export file
   */
  const handleDownload = async (exportItem: ExportHistoryItem) => {
    try {
      if (!exportItem.download_token) {
        toast.error('Download link is no longer available');
        return;
      }

      logger.debug('[DataExportSettings] Downloading export...', exportItem.job_id);

      // Build download URL with token
      const params = new URLSearchParams();
      params.set('token', exportItem.download_token);
      params.set('format', exportItem.format);

      const fileExtension = exportItem.format === 'json' ? 'json' : 'zip';
      const filename = `data-export-${new Date(exportItem.created_at).toISOString().split('T')[0]}.${fileExtension}`;

      // Use direct fetch for file download
      const response = await fetch(
        `/api/accounts/data-export/download/${exportItem.download_token}/?${params.toString()}`,
        {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Download failed (${response.status})`);
      }

      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast.success('Download started!');
    } catch (error) {
      logger.error('[DataExportSettings] Error downloading export:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to download export';
      toast.error(errorMessage);
    }
  };

  /**
   * Delete export request
   */
  const handleDelete = async () => {
    if (!deleteJobId) return;

    try {
      setIsDeleting(true);

      logger.debug('[DataExportSettings] Deleting export:', deleteJobId);

      const response = await unifiedAPI.fetch(
        `/accounts/data-export/${deleteJobId}/`,
        'DELETE'
      );

      if (!response.ok) {
        throw new Error(`Failed to delete export (${response.status})`);
      }

      // Remove from history
      setExportHistory((prev) =>
        prev.filter((item) => item.job_id !== deleteJobId)
      );

      toast.success('Export request deleted');
      setShowDeleteDialog(false);
      setDeleteJobId(null);
    } catch (error) {
      logger.error('[DataExportSettings] Error deleting export:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to delete export';
      toast.error(errorMessage);
    } finally {
      setIsDeleting(false);
    }
  };

  /**
   * Format file size for display
   */
  const formatFileSize = (bytes: number | undefined) => {
    if (!bytes) return 'Unknown size';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  /**
   * Format date for display
   */
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  /**
   * Get status badge color
   */
  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'queued':
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  /**
   * Get status icon
   */
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
      case 'processing':
        return <Clock className="w-4 h-4" />;
      case 'completed':
        return <CheckCircle2 className="w-4 h-4" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4 flex items-center justify-center">
        <LoadingSpinner size="lg" text="Loading data export settings..." />
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Data Export</h1>
          <p className="text-gray-600">
            Download your personal data in accordance with GDPR Article 20 (Right to Data Portability)
          </p>
        </div>

        {/* GDPR Information Alert */}
        <Alert className="mb-6 bg-blue-50 text-blue-800 border-blue-200">
          <Shield className="h-4 w-4" />
          <AlertDescription>
            <strong>Your GDPR Right:</strong> You have the right to request and download all your
            personal data in a structured, commonly used, and machine-readable format. Your data
            will be available for 7 days from the export request date.
          </AlertDescription>
        </Alert>

        {/* Load Error Alert */}
        {loadError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}

        {/* Export Error Alert */}
        {exportError && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{exportError}</AlertDescription>
          </Alert>
        )}

        {/* Export Success Alert */}
        {exportSuccessJobId && (
          <Alert className="mb-6 bg-green-50 text-green-800 border-green-200">
            <CheckCircle2 className="h-4 w-4" />
            <AlertDescription>
              Your data export has been initiated and will be ready shortly. You'll see it in the
              history below.
            </AlertDescription>
          </Alert>
        )}

        {/* Export Form Card */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileJson className="w-5 h-5" />
              Create New Export
            </CardTitle>
            <CardDescription>
              Choose the format and data types you want to export
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(handleExport)} className="space-y-6">
                {/* Format Selection */}
                <FormField
                  control={form.control}
                  name="format"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-base font-semibold">Export Format</FormLabel>
                      <FormDescription className="mb-3">
                        Choose the file format for your data export
                      </FormDescription>
                      <FormControl>
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger className="w-full md:w-64">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="json">
                              <div className="flex items-center gap-2">
                                <FileJson className="w-4 h-4" />
                                JSON (Single File)
                              </div>
                            </SelectItem>
                            <SelectItem value="csv">
                              <div className="flex items-center gap-2">
                                <FileSpreadsheet className="w-4 h-4" />
                                CSV (Multiple Files in ZIP)
                              </div>
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {/* Data Scope Selection */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900">Data to Include</h3>
                  <p className="text-sm text-gray-600 mb-3">
                    Select which data types you want to include in your export
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="include_profile"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value}
                              onChange={field.onChange}
                              className="w-4 h-4 rounded"
                            />
                          </FormControl>
                          <FormLabel className="cursor-pointer flex-1 m-0">
                            <div>
                              <p className="font-medium text-sm">Profile Data</p>
                              <p className="text-xs text-gray-500">
                                Name, email, role, contact info
                              </p>
                            </div>
                          </FormLabel>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="include_activity"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value}
                              onChange={field.onChange}
                              className="w-4 h-4 rounded"
                            />
                          </FormControl>
                          <FormLabel className="cursor-pointer flex-1 m-0">
                            <div>
                              <p className="font-medium text-sm">Activity Logs</p>
                              <p className="text-xs text-gray-500">Login history, actions</p>
                            </div>
                          </FormLabel>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="include_messages"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value}
                              onChange={field.onChange}
                              className="w-4 h-4 rounded"
                            />
                          </FormControl>
                          <FormLabel className="cursor-pointer flex-1 m-0">
                            <div>
                              <p className="font-medium text-sm">Messages</p>
                              <p className="text-xs text-gray-500">Chat messages, discussions</p>
                            </div>
                          </FormLabel>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="include_assignments"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value}
                              onChange={field.onChange}
                              className="w-4 h-4 rounded"
                            />
                          </FormControl>
                          <FormLabel className="cursor-pointer flex-1 m-0">
                            <div>
                              <p className="font-medium text-sm">Assignments</p>
                              <p className="text-xs text-gray-500">
                                Submissions, grades, feedback
                              </p>
                            </div>
                          </FormLabel>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="include_payments"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value}
                              onChange={field.onChange}
                              className="w-4 h-4 rounded"
                            />
                          </FormControl>
                          <FormLabel className="cursor-pointer flex-1 m-0">
                            <div>
                              <p className="font-medium text-sm">Payments</p>
                              <p className="text-xs text-gray-500">Invoices, transactions</p>
                            </div>
                          </FormLabel>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="include_notifications"
                      render={({ field }) => (
                        <FormItem className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                          <FormControl>
                            <input
                              type="checkbox"
                              checked={field.value}
                              onChange={field.onChange}
                              className="w-4 h-4 rounded"
                            />
                          </FormControl>
                          <FormLabel className="cursor-pointer flex-1 m-0">
                            <div>
                              <p className="font-medium text-sm">Notifications</p>
                              <p className="text-xs text-gray-500">Alerts, messages</p>
                            </div>
                          </FormLabel>
                        </FormItem>
                      )}
                    />
                  </div>
                </div>

                {/* Submit Button */}
                <div className="flex gap-3 pt-4">
                  <Button
                    type="submit"
                    disabled={isExporting}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {isExporting ? (
                      <>
                        <LoadingSpinner size="sm" className="mr-2" />
                        Initiating Export...
                      </>
                    ) : (
                      <>
                        <Download className="w-4 h-4 mr-2" />
                        Create Export
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>

        {/* Export History Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Export History
            </CardTitle>
            <CardDescription>
              View and download your previous data exports (available for 7 days)
            </CardDescription>
          </CardHeader>
          <CardContent>
            {exportHistory.length === 0 ? (
              <div className="text-center py-8">
                <Info className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500">No exports yet. Create your first export above!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {exportHistory.map((exportItem) => (
                  <div
                    key={exportItem.job_id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      {/* Format Icon */}
                      {exportItem.format === 'json' ? (
                        <FileJson className="w-5 h-5 text-blue-600" />
                      ) : (
                        <FileSpreadsheet className="w-5 h-5 text-green-600" />
                      )}

                      {/* Export Details */}
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="font-semibold text-gray-900">
                            {exportItem.format.toUpperCase()} Export
                          </span>
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium flex items-center gap-1 ${getStatusBadgeColor(exportItem.status)}`}
                          >
                            {getStatusIcon(exportItem.status)}
                            <span className="capitalize">{exportItem.status}</span>
                          </span>
                        </div>
                        <div className="text-sm text-gray-500 space-y-1">
                          <p>Created: {formatDate(exportItem.created_at)}</p>
                          {exportItem.file_size && (
                            <p>Size: {formatFileSize(exportItem.file_size)}</p>
                          )}
                          {exportItem.status === 'failed' && exportItem.error_message && (
                            <p className="text-red-600">Error: {exportItem.error_message}</p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center gap-2">
                      {exportItem.status === 'completed' && exportItem.download_token && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDownload(exportItem)}
                          className="gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Download
                        </Button>
                      )}

                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setDeleteJobId(exportItem.job_id);
                          setShowDeleteDialog(true);
                        }}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Additional Information */}
        <Card className="mt-8 bg-blue-50 border-blue-200">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Info className="w-5 h-5" />
              About Your Data Export
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-gray-700">
            <div>
              <p className="font-semibold mb-1">What data is included?</p>
              <p>
                Your export includes all personal data associated with your account: profile
                information, activity logs, messages, assignments, payments, and notifications.
              </p>
            </div>
            <div>
              <p className="font-semibold mb-1">How long is it available?</p>
              <p>
                Export files are available for download for 7 days from the date of creation. After
                that, they are automatically deleted.
              </p>
            </div>
            <div>
              <p className="font-semibold mb-1">Is my data secure?</p>
              <p>
                Yes. Your export is protected with secure tokens and can only be downloaded by you.
                Files are encrypted during transmission and stored securely.
              </p>
            </div>
            <div>
              <p className="font-semibold mb-1">Need help?</p>
              <p>
                For questions about your data or to exercise your GDPR rights, please contact our
                support team at support@thebot.platform or submit a request through our privacy
                portal.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Export?</DialogTitle>
            <DialogDescription>
              This will permanently delete the export request and any associated files. This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete Export'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DataExportSettings;
