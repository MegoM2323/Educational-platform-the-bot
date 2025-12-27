import React, { useState, useCallback } from 'react';
import { Loader2, Download, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { logger } from '@/utils/logger';

/**
 * Export format type
 */
export type ExportFormat = 'csv' | 'excel' | 'pdf';

/**
 * Export scope - what data to include
 */
export type ExportScope = 'current' | 'selected' | 'all';

/**
 * ExportDialog Props
 */
export interface ExportDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  onExport: (params: ExportParams) => Promise<void>;
  isLoading?: boolean;
  supportedFormats?: ExportFormat[];
  supportedScopes?: ExportScope[];
  defaultFormat?: ExportFormat;
  defaultScope?: ExportScope;
  includeScheduling?: boolean;
  includeFormatOptions?: boolean;
  className?: string;
}

/**
 * Export parameters
 */
export interface ExportParams {
  format: ExportFormat;
  scope: ExportScope;
  fileName: string;
  includeFormatting: boolean;
  scheduleExport: boolean;
  scheduleEmail: string | null;
  scheduleFrequency: 'once' | 'daily' | 'weekly' | 'monthly' | null;
}

/**
 * ExportDialog Component
 *
 * Modal dialog for exporting data in various formats with options for:
 * - Format selection (CSV, Excel, PDF)
 * - Scope selection (current data, selected items, all data)
 * - File naming
 * - Formatting options
 * - Scheduling exports with email delivery
 *
 * Features:
 * - Loading state during export
 * - Error handling and display
 * - Success notification
 * - Responsive design
 * - Form validation
 * - Progress indication
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false);
 *
 * const handleExport = async (params) => {
 *   await api.exportData(params);
 * };
 *
 * return (
 *   <>
 *     <Button onClick={() => setIsOpen(true)}>Export</Button>
 *     <ExportDialog
 *       isOpen={isOpen}
 *       onOpenChange={setIsOpen}
 *       onExport={handleExport}
 *       title="Export Analytics"
 *       description="Choose format and scope for your analytics export"
 *       supportedFormats={['csv', 'excel', 'pdf']}
 *       supportedScopes={['current', 'selected', 'all']}
 *       includeScheduling={true}
 *     />
 *   </>
 * );
 * ```
 */
export const ExportDialog: React.FC<ExportDialogProps> = ({
  isOpen,
  onOpenChange,
  title = 'Export Data',
  description = 'Choose export format, scope, and options',
  onExport,
  isLoading = false,
  supportedFormats = ['csv', 'excel', 'pdf'],
  supportedScopes = ['current', 'all'],
  defaultFormat = 'csv',
  defaultScope = 'current',
  includeScheduling = false,
  includeFormatOptions = true,
  className = '',
}) => {
  // State management
  const [format, setFormat] = useState<ExportFormat>(defaultFormat);
  const [scope, setScope] = useState<ExportScope>(defaultScope);
  const [fileName, setFileName] = useState<string>(
    `export_${new Date().toISOString().split('T')[0]}`
  );
  const [includeFormatting, setIncludeFormatting] = useState(true);
  const [scheduleExport, setScheduleExport] = useState(false);
  const [scheduleEmail, setScheduleEmail] = useState<string | null>(null);
  const [scheduleFrequency, setScheduleFrequency] = useState<
    'once' | 'daily' | 'weekly' | 'monthly' | null
  >('once');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Validate email format
  const isValidEmail = (email: string | null): boolean => {
    if (!email) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  // Handle export
  const handleExport = useCallback(async () => {
    try {
      setError(null);
      setSuccess(false);
      setExporting(true);

      // Validate inputs
      if (!fileName.trim()) {
        setError('File name is required');
        return;
      }

      if (scheduleExport && !isValidEmail(scheduleEmail)) {
        setError('Valid email address is required for scheduled exports');
        return;
      }

      logger.debug('[ExportDialog] Exporting with params:', {
        format,
        scope,
        fileName: fileName.trim(),
        includeFormatting,
        scheduleExport,
        scheduleEmail,
        scheduleFrequency,
      });

      // Call export handler
      await onExport({
        format,
        scope,
        fileName: fileName.trim(),
        includeFormatting,
        scheduleExport,
        scheduleEmail,
        scheduleFrequency,
      });

      setSuccess(true);
      toast.success(`Export started for ${format.toUpperCase()}`);

      // Close dialog after short delay
      setTimeout(() => {
        onOpenChange(false);
        // Reset form
        setFormat(defaultFormat);
        setScope(defaultScope);
        setFileName(`export_${new Date().toISOString().split('T')[0]}`);
        setIncludeFormatting(true);
        setScheduleExport(false);
        setScheduleEmail(null);
        setScheduleFrequency('once');
        setSuccess(false);
        setError(null);
      }, 1500);
    } catch (err) {
      logger.error('[ExportDialog] Export error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Export failed';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setExporting(false);
    }
  }, [
    format,
    scope,
    fileName,
    includeFormatting,
    scheduleExport,
    scheduleEmail,
    scheduleFrequency,
    onExport,
    defaultFormat,
    defaultScope,
    onOpenChange,
  ]);

  // Handle close
  const handleClose = (open: boolean) => {
    if (!exporting && !isLoading) {
      onOpenChange(open);
    }
  };

  // Get file extension based on format
  const getFileExtension = (): string => {
    switch (format) {
      case 'csv':
        return '.csv';
      case 'excel':
        return '.xlsx';
      case 'pdf':
        return '.pdf';
      default:
        return '';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className={`sm:max-w-lg ${className}`}>
        {/* Header */}
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            {title}
          </DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        {/* Content */}
        <div className="space-y-6">
          {/* Format Selection */}
          <div className="space-y-2">
            <Label htmlFor="export-format" className="font-medium">
              Export Format
            </Label>
            <Select value={format} onValueChange={(v) => setFormat(v as ExportFormat)}>
              <SelectTrigger id="export-format" disabled={exporting || isLoading}>
                <SelectValue placeholder="Choose format" />
              </SelectTrigger>
              <SelectContent>
                {supportedFormats.includes('csv') && (
                  <SelectItem value="csv">
                    CSV (Comma-separated values)
                  </SelectItem>
                )}
                {supportedFormats.includes('excel') && (
                  <SelectItem value="excel">
                    Excel (XLSX spreadsheet)
                  </SelectItem>
                )}
                {supportedFormats.includes('pdf') && (
                  <SelectItem value="pdf">PDF (Portable document)</SelectItem>
                )}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              File will be saved as:{' '}
              <code className="bg-muted px-1 rounded">
                {fileName}
                {getFileExtension()}
              </code>
            </p>
          </div>

          {/* Scope Selection */}
          <div className="space-y-2">
            <Label htmlFor="export-scope" className="font-medium">
              Data Scope
            </Label>
            <Select value={scope} onValueChange={(v) => setScope(v as ExportScope)}>
              <SelectTrigger id="export-scope" disabled={exporting || isLoading}>
                <SelectValue placeholder="Choose scope" />
              </SelectTrigger>
              <SelectContent>
                {supportedScopes.includes('current') && (
                  <SelectItem value="current">
                    Current View (current page/section)
                  </SelectItem>
                )}
                {supportedScopes.includes('selected') && (
                  <SelectItem value="selected">
                    Selected Items (only selected rows/items)
                  </SelectItem>
                )}
                {supportedScopes.includes('all') && (
                  <SelectItem value="all">
                    All Data (entire dataset)
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          {/* File Name Input */}
          <div className="space-y-2">
            <Label htmlFor="file-name" className="font-medium">
              File Name
            </Label>
            <Input
              id="file-name"
              type="text"
              placeholder="export_2024-01-01"
              value={fileName}
              onChange={(e) => setFileName(e.target.value)}
              disabled={exporting || isLoading}
              className="text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Enter name without extension. File extension will be added automatically.
            </p>
          </div>

          {/* Format Options */}
          {includeFormatOptions && (
            <div className="space-y-3 border-t pt-4">
              <Label className="font-medium">Formatting Options</Label>
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
                <div>
                  <p className="text-sm font-medium">Include Formatting</p>
                  <p className="text-xs text-muted-foreground">
                    {format === 'pdf'
                      ? 'Apply colors, fonts, and styling'
                      : 'Apply colors and basic formatting'}
                  </p>
                </div>
                <Switch
                  checked={includeFormatting}
                  onCheckedChange={setIncludeFormatting}
                  disabled={exporting || isLoading}
                />
              </div>
            </div>
          )}

          {/* Scheduling Options */}
          {includeScheduling && (
            <div className="space-y-3 border-t pt-4">
              <div className="flex items-center justify-between">
                <Label className="font-medium">Schedule Export</Label>
                <Switch
                  checked={scheduleExport}
                  onCheckedChange={setScheduleExport}
                  disabled={exporting || isLoading}
                />
              </div>

              {scheduleExport && (
                <Card className="border bg-muted/50">
                  <CardContent className="space-y-3 pt-4">
                    {/* Email Input */}
                    <div className="space-y-2">
                      <Label htmlFor="schedule-email" className="text-sm">
                        Email Address
                      </Label>
                      <Input
                        id="schedule-email"
                        type="email"
                        placeholder="example@email.com"
                        value={scheduleEmail || ''}
                        onChange={(e) => setScheduleEmail(e.target.value || null)}
                        disabled={exporting || isLoading}
                        className="text-sm"
                      />
                      <p className="text-xs text-muted-foreground">
                        Export will be sent to this email address
                      </p>
                    </div>

                    {/* Frequency Selection */}
                    <div className="space-y-2">
                      <Label htmlFor="schedule-frequency" className="text-sm">
                        Frequency
                      </Label>
                      <Select
                        value={scheduleFrequency || 'once'}
                        onValueChange={(v) =>
                          setScheduleFrequency(
                            v as 'once' | 'daily' | 'weekly' | 'monthly' | null
                          )
                        }
                      >
                        <SelectTrigger
                          id="schedule-frequency"
                          disabled={exporting || isLoading}
                          className="text-sm"
                        >
                          <SelectValue placeholder="Select frequency" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="once">Once</SelectItem>
                          <SelectItem value="daily">Daily</SelectItem>
                          <SelectItem value="weekly">Weekly</SelectItem>
                          <SelectItem value="monthly">Monthly</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Error Display */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Success Display */}
          {success && (
            <Alert className="border-green-200 bg-green-50 text-green-900">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                Export started successfully. You will receive a notification when it's ready.
              </AlertDescription>
            </Alert>
          )}

          {/* Loading Indicator */}
          {(exporting || isLoading) && (
            <div className="flex items-center gap-2 p-3 bg-muted rounded-md">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <div className="flex flex-col flex-1 gap-1">
                <p className="text-sm font-medium">Processing export...</p>
                <p className="text-xs text-muted-foreground">
                  {scheduleExport ? 'Scheduling export...' : 'Generating file...'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="flex gap-2 flex-col-reverse sm:flex-row sm:justify-end">
          <Button
            variant="outline"
            onClick={() => handleClose(false)}
            disabled={exporting || isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleExport}
            disabled={exporting || isLoading || !fileName.trim()}
            className="gap-2"
          >
            {exporting || isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Export {format.toUpperCase()}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ExportDialog;
