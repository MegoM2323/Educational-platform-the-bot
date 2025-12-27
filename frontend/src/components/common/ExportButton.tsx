import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Download,
  FileJson,
  FileSpreadsheet,
  AlertCircle,
  CheckCircle2,
  Clock,
  Trash2,
  RefreshCw,
} from 'lucide-react';
import { useDataExport, ExportFormat } from '@/hooks/useDataExport';
import { toast } from 'sonner';
import { logger } from '@/utils/logger';

/**
 * Export format configuration
 */
interface ExportFormatConfig {
  id: ExportFormat;
  label: string;
  icon: React.ReactNode;
  description: string;
}

/**
 * Export history item display model
 */
interface ExportHistoryDisplay {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  format: ExportFormat;
  file_size?: number;
  created_at: string;
  download_token?: string;
  error_message?: string;
  expires_at: string;
}

const EXPORT_FORMATS: ExportFormatConfig[] = [
  {
    id: 'json',
    label: 'JSON',
    icon: <FileJson className="w-4 h-4" />,
    description: 'Single file with all data',
  },
  {
    id: 'csv',
    label: 'CSV',
    icon: <FileSpreadsheet className="w-4 h-4" />,
    description: 'Multiple CSV files in ZIP archive',
  },
];

/**
 * Props for ExportButton component
 */
export interface ExportButtonProps {
  onExportComplete?: (jobId: string) => void;
  variant?: 'default' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  showHistory?: boolean;
}

/**
 * ExportButton Component
 *
 * Provides a user-friendly interface for data export with:
 * - Format selection dropdown
 * - Download progress tracking
 * - Export history management
 * - Error handling and recovery
 * - Large file download support
 *
 * @example
 * ```tsx
 * <ExportButton
 *   onExportComplete={() => console.log('Export done')}
 *   variant="default"
 *   size="md"
 * />
 * ```
 */
export const ExportButton: React.FC<ExportButtonProps> = ({ onExportComplete, variant = 'default', size = 'md', showHistory = true }) => {
  const {
    isLoading,
    error,
    initiateExport,
    checkStatus,
    fetchExports,
    downloadExport,
    deleteExport,
  } = useDataExport();

  const [showFormatDialog, setShowFormatDialog] = useState(false);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('json');
  const [exportHistory, setExportHistory] = useState<ExportHistoryDisplay[]>([]);
  const [downloadProgress, setDownloadProgress] = useState<Record<string, number>>({});
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);
  const [activeStatusCheck, setActiveStatusCheck] = useState<string | null>(null);
  const statusCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Load export history on component mount
   */
  useEffect(() => {
    loadExportHistory();
  }, []);

  /**
   * Cleanup interval on unmount
   */
  useEffect(() => {
    return () => {
      if (statusCheckIntervalRef.current) {
        clearInterval(statusCheckIntervalRef.current);
      }
    };
  }, []);

  /**
   * Load export history from API
   */
  const loadExportHistory = async () => {
    try {
      logger.debug('[ExportButton] Loading export history...');
      const exports = await fetchExports();
      setExportHistory(exports as ExportHistoryDisplay[]);
    } catch (err) {
      logger.error('[ExportButton] Error loading history:', err);
      // Don't show error toast for history load - it's secondary
    }
  };

  /**
   * Start status checking for a job
   */
  const startStatusCheck = (jobId: string) => {
    logger.debug('[ExportButton] Starting status check for:', jobId);
    setActiveStatusCheck(jobId);

    const checkInterval = setInterval(async () => {
      try {
        const status = await checkStatus(jobId);
        setExportHistory((prev) =>
          prev.map((item) =>
            item.job_id === jobId ? { ...item, ...status } : item
          )
        );

        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(checkInterval);
          setActiveStatusCheck(null);

          if (status.status === 'completed') {
            toast.success('Export is ready for download!');
          }
        }
      } catch (err) {
        logger.error('[ExportButton] Error checking status:', err);
      }
    }, 2000);

    statusCheckIntervalRef.current = checkInterval;

    // Auto-stop after 5 minutes
    setTimeout(() => {
      clearInterval(checkInterval);
      setActiveStatusCheck(null);
    }, 5 * 60 * 1000);
  };

  /**
   * Handle export format selection and initiation
   */
  const handleExport = async () => {
    try {
      setShowFormatDialog(false);
      logger.debug('[ExportButton] Initiating export with format:', selectedFormat);

      const job = await initiateExport(selectedFormat);

      // Add to history
      const newExport: ExportHistoryDisplay = {
        job_id: job.job_id,
        status: 'queued',
        format: selectedFormat,
        created_at: new Date().toISOString(),
        expires_at: job.expires_at,
      };

      setExportHistory((prev) => [newExport, ...prev]);
      toast.success('Export initiated! Processing in background...');

      // Start status checking
      startStatusCheck(job.job_id);

      // Notify parent component
      onExportComplete?.(job.job_id);
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : 'Failed to initiate export';
      logger.error('[ExportButton] Export error:', err);
      toast.error(errorMsg);
    }
  };

  /**
   * Handle file download with progress tracking
   */
  const handleDownload = async (exportItem: ExportHistoryDisplay) => {
    try {
      if (!exportItem.download_token) {
        toast.error('Download link is no longer available');
        return;
      }

      logger.debug('[ExportButton] Starting download for:', exportItem.job_id);
      setDownloadProgress((prev) => ({ ...prev, [exportItem.job_id]: 0 }));

      // Use simulated progress since we can't track actual download progress easily
      const progressInterval = setInterval(() => {
        setDownloadProgress((prev) => {
          const current = prev[exportItem.job_id] || 0;
          if (current < 90) {
            return { ...prev, [exportItem.job_id]: current + Math.random() * 20 };
          }
          return prev;
        });
      }, 500);

      await downloadExport(
        exportItem.job_id,
        exportItem.download_token,
        exportItem.format
      );

      clearInterval(progressInterval);
      setDownloadProgress((prev) => ({ ...prev, [exportItem.job_id]: 100 }));
      toast.success('Download started!');

      // Clear progress after 2 seconds
      setTimeout(() => {
        setDownloadProgress((prev) => {
          const updated = { ...prev };
          delete updated[exportItem.job_id];
          return updated;
        });
      }, 2000);
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : 'Failed to download export';
      logger.error('[ExportButton] Download error:', err);
      toast.error(errorMsg);
      setDownloadProgress((prev) => {
        const updated = { ...prev };
        delete updated[exportItem.job_id];
        return updated;
      });
    }
  };

  /**
   * Handle export deletion
   */
  const handleDeleteExport = async (jobId: string) => {
    try {
      setDeletingJobId(jobId);
      logger.debug('[ExportButton] Deleting export:', jobId);

      await deleteExport(jobId);
      setExportHistory((prev) => prev.filter((item) => item.job_id !== jobId));
      toast.success('Export deleted');
    } catch (err) {
      const errorMsg =
        err instanceof Error ? err.message : 'Failed to delete export';
      logger.error('[ExportButton] Delete error:', err);
      toast.error(errorMsg);
    } finally {
      setDeletingJobId(null);
    }
  };

  /**
   * Format file size for display
   */
  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  /**
   * Format date for display
   */
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  /**
   * Get status badge styling
   */
  const getStatusStyles = (
    status: string
  ): { bg: string; text: string; icon: React.ReactNode } => {
    switch (status) {
      case 'queued':
      case 'processing':
        return {
          bg: 'bg-blue-100',
          text: 'text-blue-800',
          icon: <Clock className="w-4 h-4" />,
        };
      case 'completed':
        return {
          bg: 'bg-green-100',
          text: 'text-green-800',
          icon: <CheckCircle2 className="w-4 h-4" />,
        };
      case 'failed':
        return {
          bg: 'bg-red-100',
          text: 'text-red-800',
          icon: <AlertCircle className="w-4 h-4" />,
        };
      default:
        return {
          bg: 'bg-gray-100',
          text: 'text-gray-800',
          icon: null,
        };
    }
  };

  return (
    <>
      {/* Main Export Button */}
      <div className="flex gap-2">
        <Button
          onClick={() => setShowFormatDialog(true)}
          disabled={isLoading}
          variant={variant}
          size={size}
          className="gap-2"
        >
          <Download className="w-4 h-4" />
          Export Data
        </Button>

        {/* History Button */}
        {showHistory && (
          <Button
            onClick={() => setShowHistoryDialog(true)}
            variant="outline"
            size={size}
            className="gap-2"
          >
            <Clock className="w-4 h-4" />
            History
          </Button>
        )}
      </div>

      {/* Format Selection Dialog */}
      <Dialog open={showFormatDialog} onOpenChange={setShowFormatDialog}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Select Export Format</DialogTitle>
            <DialogDescription>
              Choose the format for your data export. The file will be available for 7 days.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-3">
            {EXPORT_FORMATS.map((format) => (
              <div
                key={format.id}
                onClick={() => setSelectedFormat(format.id)}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedFormat === format.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center gap-3 mb-1">
                  {format.icon}
                  <h4 className="font-semibold">{format.label}</h4>
                </div>
                <p className="text-sm text-gray-600 ml-7">{format.description}</p>
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowFormatDialog(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleExport}
              disabled={isLoading}
              className="gap-2"
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Export
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Export History Dialog */}
      <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Export History</DialogTitle>
            <DialogDescription>
              View and manage your previous data exports (available for 7 days)
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            {exportHistory.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <FileJson className="w-12 h-12 mx-auto mb-2 opacity-30" />
                <p>No exports yet. Create your first export above!</p>
              </div>
            ) : (
              exportHistory.map((item) => {
                const statusStyles = getStatusStyles(item.status);
                const progress = downloadProgress[item.job_id];

                return (
                  <div
                    key={item.job_id}
                    className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        {item.format === 'json' ? (
                          <FileJson className="w-5 h-5 text-blue-600" />
                        ) : (
                          <FileSpreadsheet className="w-5 h-5 text-green-600" />
                        )}
                        <div>
                          <p className="font-semibold text-gray-900">
                            {item.format.toUpperCase()} Export
                          </p>
                          <p className="text-sm text-gray-500">
                            {formatDate(item.created_at)}
                          </p>
                        </div>
                      </div>

                      <span
                        className={`px-3 py-1 rounded text-xs font-medium flex items-center gap-1 ${statusStyles.bg} ${statusStyles.text}`}
                      >
                        {statusStyles.icon}
                        {item.status.charAt(0).toUpperCase() +
                          item.status.slice(1)}
                      </span>
                    </div>

                    {/* Details */}
                    {item.file_size && (
                      <p className="text-sm text-gray-600 mb-2">
                        Size: {formatFileSize(item.file_size)}
                      </p>
                    )}

                    {item.status === 'failed' && item.error_message && (
                      <Alert variant="destructive" className="mb-3">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{item.error_message}</AlertDescription>
                      </Alert>
                    )}

                    {/* Progress Bar */}
                    {progress !== undefined && (
                      <div className="mb-3">
                        <div className="flex justify-between mb-1">
                          <span className="text-sm text-gray-600">
                            Downloading...
                          </span>
                          <span className="text-sm font-medium">
                            {Math.round(progress)}%
                          </span>
                        </div>
                        <Progress value={progress} className="h-2" />
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex gap-2">
                      {item.status === 'completed' &&
                        item.download_token && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDownload(item)}
                            disabled={progress !== undefined}
                            className="gap-2"
                          >
                            <Download className="w-4 h-4" />
                            Download
                          </Button>
                        )}

                      {activeStatusCheck === item.job_id && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled
                          className="gap-2"
                        >
                          <RefreshCw className="w-4 h-4 animate-spin" />
                          Checking...
                        </Button>
                      )}

                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteExport(item.job_id)}
                        disabled={deletingJobId === item.job_id}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowHistoryDialog(false)}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ExportButton;
