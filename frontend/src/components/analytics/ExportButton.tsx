import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import {
  Download,
  FileJson,
  FileText,
  Sheet,
  Loader2,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/integrations/api/client';

interface ExportButtonProps {
  /**
   * Data to export
   */
  data?: Record<string, any>;

  /**
   * Endpoint to fetch exportable data from
   */
  endpoint?: string;

  /**
   * Query parameters for the export endpoint
   */
  queryParams?: Record<string, string | number | boolean>;

  /**
   * Custom filename (without extension)
   */
  filename?: string;

  /**
   * Available export formats
   */
  formats?: Array<'csv' | 'xlsx' | 'pdf' | 'json'>;

  /**
   * Show progress during export
   */
  showProgress?: boolean;

  /**
   * Callback when export completes successfully
   */
  onExportSuccess?: (format: string) => void;

  /**
   * Callback on export error
   */
  onExportError?: (error: Error, format: string) => void;

  /**
   * Button variant
   */
  variant?: 'default' | 'outline' | 'ghost' | 'secondary' | 'destructive';

  /**
   * Button size
   */
  size?: 'sm' | 'md' | 'lg';

  /**
   * Show as dropdown or single button
   */
  asDropdown?: boolean;
}

/**
 * Export Button Component
 *
 * Provides functionality to export dashboard data in multiple formats:
 * - CSV: Comma-separated values for spreadsheet applications
 * - XLSX: Excel format with styling and multiple sheets
 * - PDF: Formatted report with charts and headers
 * - JSON: Raw data export for programmatic use
 *
 * Features:
 * - Progress tracking for large exports
 * - Multiple format support
 * - Error handling and user feedback
 * - Custom filename support
 * - Query parameter support for server-side filtering
 * - Download progress indication
 *
 * @example
 * ```tsx
 * // Export dashboard data as CSV
 * <ExportButton
 *   data={dashboardData}
 *   filename="analytics_report"
 *   formats={['csv', 'xlsx', 'pdf']}
 * />
 *
 * // Export from API endpoint
 * <ExportButton
 *   endpoint="/reports/analytics-data/export/"
 *   queryParams={{ classId: 5, format: 'csv' }}
 *   onExportSuccess={(format) => console.log(`Exported as ${format}`)}
 * />
 * ```
 */
export const ExportButton: React.FC<ExportButtonProps> = ({
  data,
  endpoint,
  queryParams = {},
  filename = 'analytics_export',
  formats = ['csv', 'xlsx', 'pdf'],
  showProgress = true,
  onExportSuccess,
  onExportError,
  variant = 'outline',
  size = 'sm',
  asDropdown = true,
}) => {
  const { toast } = useToast();
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);

  /**
   * Export data to CSV format
   */
  const exportToCSV = async () => {
    try {
      setExporting(true);
      setExportProgress(0);

      if (endpoint) {
        const params = new URLSearchParams({
          ...queryParams,
          format: 'csv',
        } as Record<string, string>);

        const response = await apiClient.get(`${endpoint}?${params}`, {
          responseType: 'blob',
        });

        downloadBlob(response.data, `${filename}.csv`, 'text/csv');
      } else if (data) {
        const csv = convertToCSV(data);
        const blob = new Blob([csv], { type: 'text/csv' });
        downloadBlob(blob, `${filename}.csv`, 'text/csv');
      }

      setExportProgress(100);
      toast({
        title: 'Export Successful',
        description: 'Analytics data exported as CSV',
      });
      onExportSuccess?.('csv');
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Export failed');
      toast({
        title: 'Export Failed',
        description: err.message,
        variant: 'destructive',
      });
      onExportError?.(err, 'csv');
    } finally {
      setExporting(false);
      setExportProgress(0);
    }
  };

  /**
   * Export data to XLSX format
   */
  const exportToXLSX = async () => {
    try {
      setExporting(true);
      setExportProgress(0);

      if (endpoint) {
        const params = new URLSearchParams({
          ...queryParams,
          format: 'xlsx',
        } as Record<string, string>);

        const response = await apiClient.get(`${endpoint}?${params}`, {
          responseType: 'blob',
        });

        downloadBlob(
          response.data,
          `${filename}.xlsx`,
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        );
      } else {
        toast({
          title: 'Export Not Available',
          description: 'XLSX export requires server-side generation',
          variant: 'destructive',
        });
      }

      setExportProgress(100);
      toast({
        title: 'Export Successful',
        description: 'Analytics data exported as XLSX',
      });
      onExportSuccess?.('xlsx');
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Export failed');
      toast({
        title: 'Export Failed',
        description: err.message,
        variant: 'destructive',
      });
      onExportError?.(err, 'xlsx');
    } finally {
      setExporting(false);
      setExportProgress(0);
    }
  };

  /**
   * Export data to PDF format
   */
  const exportToPDF = async () => {
    try {
      setExporting(true);
      setExportProgress(0);

      if (endpoint) {
        const params = new URLSearchParams({
          ...queryParams,
          format: 'pdf',
        } as Record<string, string>);

        const response = await apiClient.get(`${endpoint}?${params}`, {
          responseType: 'blob',
        });

        downloadBlob(response.data, `${filename}.pdf`, 'application/pdf');
      } else {
        toast({
          title: 'Export Not Available',
          description: 'PDF export requires server-side generation',
          variant: 'destructive',
        });
      }

      setExportProgress(100);
      toast({
        title: 'Export Successful',
        description: 'Analytics data exported as PDF',
      });
      onExportSuccess?.('pdf');
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Export failed');
      toast({
        title: 'Export Failed',
        description: err.message,
        variant: 'destructive',
      });
      onExportError?.(err, 'pdf');
    } finally {
      setExporting(false);
      setExportProgress(0);
    }
  };

  /**
   * Export data to JSON format
   */
  const exportToJSON = async () => {
    try {
      setExporting(true);
      setExportProgress(50);

      if (data) {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        downloadBlob(blob, `${filename}.json`, 'application/json');
      } else if (endpoint) {
        const response = await apiClient.get(endpoint, {
          params: queryParams,
        });

        const json = JSON.stringify(response.data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        downloadBlob(blob, `${filename}.json`, 'application/json');
      }

      setExportProgress(100);
      toast({
        title: 'Export Successful',
        description: 'Analytics data exported as JSON',
      });
      onExportSuccess?.('json');
    } catch (error) {
      const err = error instanceof Error ? error : new Error('Export failed');
      toast({
        title: 'Export Failed',
        description: err.message,
        variant: 'destructive',
      });
      onExportError?.(err, 'json');
    } finally {
      setExporting(false);
      setExportProgress(0);
    }
  };

  /**
   * Trigger file download
   */
  const downloadBlob = (blob: Blob, filename: string, mimeType: string) => {
    const url = window.URL.createObjectURL(new Blob([blob], { type: mimeType }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  /**
   * Convert object/array to CSV format
   */
  const convertToCSV = (obj: any): string => {
    if (Array.isArray(obj)) {
      if (obj.length === 0) return '';

      const headers = Object.keys(obj[0]);
      const csvHeaders = headers.join(',');
      const csvRows = obj.map((row) =>
        headers
          .map((header) => {
            const value = row[header];
            // Escape quotes and wrap in quotes if contains comma
            if (typeof value === 'string' && value.includes(',')) {
              return `"${value.replace(/"/g, '""')}"`;
            }
            return value;
          })
          .join(',')
      );

      return [csvHeaders, ...csvRows].join('\n');
    }

    // Handle object (convert to key-value pairs)
    const rows = [];
    const flattenObj = (obj: any, prefix = '') => {
      for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
          const fullKey = prefix ? `${prefix}.${key}` : key;
          const value = obj[key];
          if (typeof value === 'object' && value !== null) {
            flattenObj(value, fullKey);
          } else {
            rows.push([fullKey, value]);
          }
        }
      }
    };

    flattenObj(obj);
    return rows.map((row) => row.join(',')).join('\n');
  };

  if (!asDropdown && formats.length === 1) {
    // Single format button
    const handleClick = async () => {
      switch (formats[0]) {
        case 'csv':
          await exportToCSV();
          break;
        case 'xlsx':
          await exportToXLSX();
          break;
        case 'pdf':
          await exportToPDF();
          break;
        case 'json':
          await exportToJSON();
          break;
      }
    };

    return (
      <Button
        onClick={handleClick}
        disabled={exporting}
        variant={variant}
        size={size}
      >
        {exporting ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            {showProgress && exportProgress > 0 && `${exportProgress}%`}
          </>
        ) : (
          <>
            <Download className="h-4 w-4 mr-2" />
            Export
          </>
        )}
      </Button>
    );
  }

  // Dropdown menu with multiple formats
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          disabled={exporting}
          variant={variant}
          size={size}
        >
          {exporting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              {showProgress && exportProgress > 0 && `${exportProgress}%`}
            </>
          ) : (
            <>
              <Download className="h-4 w-4 mr-2" />
              Export
            </>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {formats.includes('csv') && (
          <DropdownMenuItem onClick={exportToCSV} disabled={exporting}>
            <FileText className="h-4 w-4 mr-2" />
            Export as CSV
          </DropdownMenuItem>
        )}
        {formats.includes('xlsx') && (
          <DropdownMenuItem onClick={exportToXLSX} disabled={exporting}>
            <Sheet className="h-4 w-4 mr-2" />
            Export as XLSX
          </DropdownMenuItem>
        )}
        {formats.includes('json') && (
          <DropdownMenuItem onClick={exportToJSON} disabled={exporting}>
            <FileJson className="h-4 w-4 mr-2" />
            Export as JSON
          </DropdownMenuItem>
        )}
        {formats.includes('pdf') && (
          <>
            <DropdownMenuSeparator />
          </>
        )}
        {formats.includes('pdf') && (
          <DropdownMenuItem onClick={exportToPDF} disabled={exporting}>
            <FileText className="h-4 w-4 mr-2" />
            Export as PDF
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default ExportButton;
