import { useState, useCallback } from 'react';
import { ExportParams, ExportFormat, ExportScope } from '@/components/common/ExportDialog';
import { logger } from '@/utils/logger';

/**
 * Export options for hook initialization
 */
export interface UseExportDialogOptions {
  defaultFormat?: ExportFormat;
  defaultScope?: ExportScope;
  supportedFormats?: ExportFormat[];
  supportedScopes?: ExportScope[];
  includeScheduling?: boolean;
  includeFormatOptions?: boolean;
}

/**
 * Return type for useExportDialog hook
 */
export interface UseExportDialogReturn {
  isOpen: boolean;
  openDialog: () => void;
  closeDialog: () => void;
  toggleDialog: () => void;
  isLoading: boolean;
  error: string | null;
  success: boolean;
  exportData: (params: ExportParams) => Promise<void>;
  reset: () => void;
}

/**
 * useExportDialog Hook
 *
 * Custom hook for managing export dialog state and operations
 *
 * Features:
 * - Dialog open/close state management
 * - Loading and error handling
 * - Export function wrapper
 * - State reset capability
 *
 * @param onExport - Function to execute when export is triggered
 * @param options - Configuration options for the hook
 * @returns Export dialog state and control functions
 *
 * @example
 * ```tsx
 * const { isOpen, openDialog, closeDialog, exportData, isLoading, error } = useExportDialog(
 *   async (params) => {
 *     const response = await api.exportAnalytics(params);
 *     // Handle response
 *   },
 *   { supportedFormats: ['csv', 'pdf'] }
 * );
 *
 * return (
 *   <>
 *     <Button onClick={openDialog}>Export</Button>
 *     <ExportDialog
 *       isOpen={isOpen}
 *       onOpenChange={closeDialog}
 *       onExport={exportData}
 *       isLoading={isLoading}
 *     />
 *   </>
 * );
 * ```
 */
export const useExportDialog = (
  onExport: (params: ExportParams) => Promise<void>,
  options: UseExportDialogOptions = {}
): UseExportDialogReturn => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const openDialog = useCallback(() => {
    logger.debug('[useExportDialog] Opening dialog');
    setIsOpen(true);
    setError(null);
    setSuccess(false);
  }, []);

  const closeDialog = useCallback(() => {
    logger.debug('[useExportDialog] Closing dialog');
    setIsOpen(false);
  }, []);

  const toggleDialog = useCallback(() => {
    logger.debug('[useExportDialog] Toggling dialog');
    setIsOpen((prev) => !prev);
  }, []);

  const exportData = useCallback(
    async (params: ExportParams) => {
      try {
        logger.debug('[useExportDialog] Starting export with params:', params);
        setIsLoading(true);
        setError(null);
        setSuccess(false);

        await onExport(params);

        logger.debug('[useExportDialog] Export completed successfully');
        setSuccess(true);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Export failed';
        logger.error('[useExportDialog] Export failed:', errorMessage);
        setError(errorMessage);
        setSuccess(false);
      } finally {
        setIsLoading(false);
      }
    },
    [onExport]
  );

  const reset = useCallback(() => {
    logger.debug('[useExportDialog] Resetting state');
    setIsOpen(false);
    setIsLoading(false);
    setError(null);
    setSuccess(false);
  }, []);

  return {
    isOpen,
    openDialog,
    closeDialog,
    toggleDialog,
    isLoading,
    error,
    success,
    exportData,
    reset,
  };
};

export default useExportDialog;
