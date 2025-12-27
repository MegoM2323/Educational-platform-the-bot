# ExportDialog Component

A comprehensive React modal dialog component for exporting data in multiple formats with advanced options including scheduling and email delivery.

## Features

- **Multiple Export Formats**: CSV, Excel (XLSX), PDF
- **Data Scope Selection**: Current view, selected items, or all data
- **Custom File Naming**: User-friendly file naming with automatic extension handling
- **Formatting Options**: Toggle cell formatting and styling for exports
- **Export Scheduling**: Schedule exports to run once, daily, weekly, or monthly
- **Email Delivery**: Send exports directly to email addresses
- **Loading States**: Visual feedback during export processing
- **Error Handling**: Comprehensive error messages and recovery
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Accessibility**: WCAG compliant with proper labels and descriptions

## Installation

The component is already integrated into the project. Import it where needed:

```tsx
import { ExportDialog, ExportParams } from '@/components/common/ExportDialog';
```

## Basic Usage

### Simple Example

```tsx
import { useState } from 'react';
import { ExportDialog } from '@/components/common/ExportDialog';
import { Button } from '@/components/ui/button';

export const MyComponent = () => {
  const [isOpen, setIsOpen] = useState(false);

  const handleExport = async (params) => {
    // Call your export API
    const response = await fetch('/api/export/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    // Handle response
  };

  return (
    <>
      <Button onClick={() => setIsOpen(true)}>Export Data</Button>
      <ExportDialog
        isOpen={isOpen}
        onOpenChange={setIsOpen}
        onExport={handleExport}
        title="Export Analytics"
        supportedFormats={['csv', 'excel', 'pdf']}
      />
    </>
  );
};
```

### With useExportDialog Hook

```tsx
import { useExportDialog } from '@/hooks/useExportDialog';
import { ExportDialog } from '@/components/common/ExportDialog';
import { Button } from '@/components/ui/button';

export const MyComponent = () => {
  const { isOpen, openDialog, closeDialog, exportData, isLoading } = useExportDialog(
    async (params) => {
      const response = await api.exportData(params);
      return response;
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
      />
    </>
  );
};
```

## Props

### ExportDialogProps

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `isOpen` | `boolean` | - | Controls dialog open/closed state |
| `onOpenChange` | `(open: boolean) => void` | - | Callback when dialog state changes |
| `onExport` | `(params: ExportParams) => Promise<void>` | - | Handler function called on export |
| `title` | `string` | `"Export Data"` | Dialog title |
| `description` | `string` | `"Choose export format..."` | Dialog description |
| `isLoading` | `boolean` | `false` | Show loading state |
| `supportedFormats` | `ExportFormat[]` | `['csv', 'excel', 'pdf']` | Available export formats |
| `supportedScopes` | `ExportScope[]` | `['current', 'all']` | Available data scopes |
| `defaultFormat` | `ExportFormat` | `'csv'` | Initially selected format |
| `defaultScope` | `ExportScope` | `'current'` | Initially selected scope |
| `includeScheduling` | `boolean` | `false` | Show scheduling options |
| `includeFormatOptions` | `boolean` | `true` | Show formatting toggles |
| `className` | `string` | `''` | Additional CSS classes |

### ExportParams

Parameters passed to the export handler:

```typescript
interface ExportParams {
  format: ExportFormat;           // 'csv' | 'excel' | 'pdf'
  scope: ExportScope;             // 'current' | 'selected' | 'all'
  fileName: string;               // File name without extension
  includeFormatting: boolean;      // Include cell formatting
  scheduleExport: boolean;         // Schedule for later execution
  scheduleEmail: string | null;    // Email for scheduled export
  scheduleFrequency: 'once' | 'daily' | 'weekly' | 'monthly' | null;
}
```

## Hooks

### useExportDialog

Custom hook for managing export dialog state and operations.

```typescript
const {
  isOpen,              // Dialog open state
  openDialog,          // Function to open dialog
  closeDialog,         // Function to close dialog
  toggleDialog,        // Function to toggle dialog
  isLoading,           // Loading state
  error,              // Error message if any
  success,            // Success state
  exportData,         // Function to trigger export
  reset,              // Function to reset all state
} = useExportDialog(onExport, options);
```

#### Options

```typescript
interface UseExportDialogOptions {
  defaultFormat?: ExportFormat;
  defaultScope?: ExportScope;
  supportedFormats?: ExportFormat[];
  supportedScopes?: ExportScope[];
  includeScheduling?: boolean;
  includeFormatOptions?: boolean;
}
```

## Examples

### Analytics Export with All Features

```tsx
import { useState } from 'react';
import { useExportDialog } from '@/hooks/useExportDialog';
import { ExportDialog } from '@/components/common/ExportDialog';
import { Button } from '@/components/ui/button';

export const AnalyticsExport = () => {
  const { isOpen, openDialog, closeDialog, exportData, isLoading, error } = useExportDialog(
    async (params) => {
      const response = await fetch('/api/analytics/export/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      // Option 1: Download immediately
      if (!params.scheduleExport) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${params.fileName}.${getExtension(params.format)}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
      // Option 2: Scheduled export - server handles it
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
    <>
      <div className="p-6">
        <h1>Analytics Dashboard</h1>

        {error && <Alert variant="destructive">{error}</Alert>}

        <Button onClick={openDialog} disabled={isLoading}>
          Export Analytics
        </Button>
      </div>

      <ExportDialog
        isOpen={isOpen}
        onOpenChange={closeDialog}
        onExport={exportData}
        isLoading={isLoading}
        title="Export Analytics"
        description="Export your analytics data in your preferred format"
        supportedFormats={['csv', 'excel', 'pdf']}
        supportedScopes={['current', 'selected', 'all']}
        includeScheduling={true}
        includeFormatOptions={true}
      />
    </>
  );
};
```

### CSV-Only Export for Reports

```tsx
import { useExportDialog } from '@/hooks/useExportDialog';
import { ExportDialog } from '@/components/common/ExportDialog';

export const ReportExport = () => {
  const { isOpen, openDialog, closeDialog, exportData } = useExportDialog(
    async (params) => {
      const response = await api.exportReport(params);
      return response;
    }
  );

  return (
    <>
      <Button onClick={openDialog}>Export Report</Button>
      <ExportDialog
        isOpen={isOpen}
        onOpenChange={closeDialog}
        onExport={exportData}
        supportedFormats={['csv']}
        supportedScopes={['all']}
        includeScheduling={false}
        includeFormatOptions={false}
      />
    </>
  );
};
```

### With File Download Utility

```tsx
import { useExportDialog } from '@/hooks/useExportDialog';
import { downloadProtectedFile } from '@/utils/fileDownload';
import { ExportDialog } from '@/components/common/ExportDialog';

export const SecureExport = () => {
  const { isOpen, openDialog, closeDialog, exportData } = useExportDialog(
    async (params) => {
      // Server generates file and returns download URL
      const response = await api.createExport(params);

      if (!params.scheduleExport) {
        // Download the file securely
        await downloadProtectedFile(
          response.download_url,
          `${params.fileName}.${getExtension(params.format)}`
        );
      }
    }
  );

  return (
    <>
      <Button onClick={openDialog}>Download Report</Button>
      <ExportDialog
        isOpen={isOpen}
        onOpenChange={closeDialog}
        onExport={exportData}
        supportedFormats={['csv', 'excel', 'pdf']}
      />
    </>
  );
};
```

## Backend Integration

### Expected API Endpoint

```typescript
POST /api/export/

Request Body:
{
  format: "csv" | "excel" | "pdf",
  scope: "current" | "selected" | "all",
  fileName: string,
  includeFormatting: boolean,
  scheduleExport: boolean,
  scheduleEmail: string | null,
  scheduleFrequency: "once" | "daily" | "weekly" | "monthly" | null
}

Response (for immediate export):
{
  success: boolean,
  download_url: string,  // URL to download file
  file_size: number,
  created_at: string
}

Response (for scheduled export):
{
  success: boolean,
  scheduled_export_id: number,
  scheduled_at: string,
  email: string,
  frequency: string
}
```

### Example Django View

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class ExportView(APIView):
    def post(self, request):
        format_type = request.data.get('format')
        scope = request.data.get('scope')
        file_name = request.data.get('fileName')
        include_formatting = request.data.get('includeFormatting')
        schedule_export = request.data.get('scheduleExport')
        schedule_email = request.data.get('scheduleEmail')
        schedule_frequency = request.data.get('scheduleFrequency')

        if schedule_export:
            # Create scheduled export
            scheduled_export = ScheduledExport.objects.create(
                user=request.user,
                format=format_type,
                scope=scope,
                file_name=file_name,
                include_formatting=include_formatting,
                email=schedule_email,
                frequency=schedule_frequency
            )
            return Response({
                'success': True,
                'scheduled_export_id': scheduled_export.id,
                'scheduled_at': scheduled_export.created_at,
                'email': schedule_email,
                'frequency': schedule_frequency
            })
        else:
            # Generate and return file
            export_service = ExportService(
                format=format_type,
                scope=scope,
                file_name=file_name,
                include_formatting=include_formatting
            )
            file_path = export_service.generate(request.user)

            return Response({
                'success': True,
                'download_url': f'/api/files/download/{file_path}/',
                'file_size': os.path.getsize(file_path),
                'created_at': datetime.now()
            })
```

## Styling

The component uses Tailwind CSS and integrates with the project's UI system. Customize appearance using:

- CSS classes via the `className` prop
- Dialog component theming (colors, spacing, animations)
- Form input styling for consistency

## Accessibility

The component follows WCAG 2.1 AA standards:

- Proper `<label>` elements for all form fields
- ARIA attributes for dialog
- Keyboard navigation support
- Focus management
- Error announcements
- Loading state indication
- Descriptive button labels

## Error Handling

The component handles various error scenarios:

```tsx
// Validation errors
- Empty file name
- Invalid email format for scheduled exports

// Export errors
- API failures
- Network timeouts
- Permission denied
- File generation failures

// User feedback
- Toast notifications for success/error
- In-dialog error messages
- Loading indicators
```

## Testing

See `ExportDialog.test.tsx` for comprehensive test coverage:

```bash
npm test ExportDialog.test.tsx
```

Test categories:
- Rendering and visibility
- Format and scope selection
- File naming
- Export functionality
- Scheduling and email
- Dialog controls
- Loading states
- Accessibility

## Performance Considerations

- **Lazy Loading**: Dialog content only renders when open
- **Memoization**: Form handlers are memoized to prevent unnecessary re-renders
- **Debouncing**: File name input uses onChange without debouncing (immediate validation)
- **Memory Management**: Blob URLs are properly revoked after use

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Related Components

- `Button` - UI button component
- `Input` - Text input component
- `Select` - Dropdown select component
- `Dialog` - Base dialog component
- `Alert` - Alert display component

## Related Hooks

- `useExportDialog` - State management for export dialogs

## Related Utilities

- `fileDownload.ts` - File download utilities with authentication

## Troubleshooting

### Dialog not appearing
- Check `isOpen` prop is set to `true`
- Verify `onOpenChange` callback is properly updating state

### Export not executing
- Verify `onExport` function is properly defined
- Check browser console for error messages
- Ensure API endpoint is accessible

### File download not working
- Verify API returns correct `Content-Disposition` headers
- Check for CORS issues in browser console
- Ensure file exists at the download URL

### Email not received (scheduled exports)
- Verify email address is valid
- Check email service configuration on backend
- Review server logs for delivery errors

## Version History

- **1.0.0** (Dec 2024): Initial release
  - Basic export dialog with format selection
  - Scope and file naming options
  - Formatting toggles
  - Scheduling and email delivery
  - Full test coverage
  - Accessibility compliance
