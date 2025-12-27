# ExportButton Component

## Overview

The `ExportButton` component provides a user-friendly interface for exporting personal data in multiple formats (JSON, CSV) with comprehensive features for managing exports.

**Location**: `frontend/src/components/common/ExportButton.tsx`

**Status**: Production Ready

## Features

### Export Formats
- **JSON**: Single file with all data
- **CSV**: Multiple CSV files packaged in ZIP archive

### Format Selection
- Dropdown menu for format selection
- User-friendly format cards with descriptions and icons
- Real-time format preview before export

### Download Management
- **Progress Tracking**: Visual progress bar during downloads
- **Large File Support**: Stream-based downloads for large files
- **Automatic Filename Generation**: Timestamped filenames
- **Safe Download**: Uses secure token-based authentication

### Export History
- View all previous exports with status indicators
- Real-time status polling (updates every 2 seconds)
- Download links for completed exports (7-day availability)
- Delete exports to free up storage
- File size information and creation timestamps

### Status Tracking
- **Queued**: Initial state when export request is submitted
- **Processing**: Export is being generated
- **Completed**: Ready for download
- **Failed**: Export failed with error message

### Error Handling
- Network error recovery
- User-friendly error messages
- Graceful failure states
- Error details in history view

## Component Props

```typescript
interface ExportButtonProps {
  // Callback when export is successfully initiated
  onExportComplete?: (jobId: string) => void;

  // Button style variant
  variant?: 'default' | 'secondary' | 'outline' | 'ghost';

  // Button size
  size?: 'sm' | 'md' | 'lg';

  // Show/hide export history section
  showHistory?: boolean;
}
```

## Usage Examples

### Basic Usage
```tsx
import { ExportButton } from '@/components/common';

export function MyComponent() {
  return <ExportButton />;
}
```

### With Callback
```tsx
import { ExportButton } from '@/components/common';

export function MyComponent() {
  const handleExportStart = (jobId: string) => {
    console.log('Export started:', jobId);
    // Track export, update UI, etc.
  };

  return (
    <ExportButton onExportComplete={handleExportStart} />
  );
}
```

### Compact Variant (for toolbars)
```tsx
<ExportButton
  size="sm"
  variant="outline"
  showHistory={false}
/>
```

### Large Variant (for dashboards)
```tsx
<ExportButton
  size="lg"
  variant="default"
/>
```

## Dialog Flows

### Export Initiation Flow
1. User clicks "Export Data" button
2. Format Selection dialog opens
3. User selects format (JSON or CSV)
4. User clicks "Export" button
5. API request sent to initiate export
6. Export added to history with "queued" status
7. Real-time status polling begins

### Download Flow
1. Export status changes to "completed"
2. Download button becomes available in history
3. User clicks "Download"
4. Progress bar shows download progress
5. Browser downloads the file automatically
6. Success toast notification shown

### Delete Flow
1. User clicks trash icon on an export
2. Confirmation dialog appears
3. User confirms deletion
4. Export removed from history
5. Success notification shown

## API Integration

The component uses the `useDataExport` hook which integrates with:

### Endpoints
- `POST /accounts/data-export/` - Initiate new export
- `GET /accounts/data-export/` - List all exports
- `GET /accounts/data-export/{jobId}/` - Check export status
- `GET /accounts/data-export/download/{token}/` - Download export file
- `DELETE /accounts/data-export/{jobId}/` - Delete export

### Authentication
- Token-based authentication via Authorization header
- Secure download tokens with expiration (7 days)
- CSRF protection for all mutations

## State Management

### Local State
- `showFormatDialog`: Format selection dialog visibility
- `showHistoryDialog`: Export history dialog visibility
- `selectedFormat`: Currently selected export format
- `exportHistory`: List of exports with metadata
- `downloadProgress`: Progress tracking per export
- `deletingJobId`: Currently deleting export ID
- `activeStatusCheck`: Job ID of active status check

### Status Polling
- Interval-based polling every 2 seconds
- Auto-stop after 5 minutes or when export completes
- Automatic cleanup on component unmount

## Styling

Uses Tailwind CSS and Shadcn UI components:
- `Button`: Primary action buttons
- `Dialog`: Format selection and history modals
- `Progress`: Download progress visualization
- `Alert`: Error and status messages
- Icons: `lucide-react` for visual feedback

## Accessibility

- Semantic HTML structure
- ARIA labels for interactive elements
- Keyboard navigation support
- Loading states with accessible indicators
- Clear error messages and feedback

## Performance Optimizations

- Memoized callbacks with `useCallback`
- Ref-based interval management for cleanup
- No unnecessary re-renders
- Efficient state updates with batching
- Icons lazy-loaded from lucide-react

## Testing

### Test Coverage
- 29 unit tests covering all functionality
- Test file: `ExportButton.test.tsx`

### Test Suites
1. **Rendering Tests**: Button display, variants, sizes
2. **Format Selection Tests**: Dialog interaction, format selection
3. **Export Initiation Tests**: API calls, success/error handling
4. **History Management Tests**: Loading, displaying, updating
5. **Download Tests**: Download flow, progress, error handling
6. **Delete Tests**: Deletion flow, confirmations
7. **Error Handling Tests**: Network errors, validation
8. **UI Tests**: File size formatting, status badges

### Running Tests
```bash
npm test -- ExportButton.test.tsx --run
```

## Examples

Full example showcase available in `ExportButton.example.tsx`:

- Basic usage
- Compact size
- With callback
- Secondary style
- Ghost style (minimal)
- Without history
- Large button
- In toolbar context
- In settings page
- Responsive layout
- Loading states
- Admin dashboard usage

To view examples:
```bash
npm run storybook
# or view directly in your dev environment
```

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Dependencies

- React 18+
- @/components/ui (Shadcn UI)
- lucide-react (icons)
- sonner (toast notifications)
- @/hooks/useDataExport (custom hook)

## Integration Points

### With DataExportSettings Page
The ExportButton can be used within the full DataExportSettings page:
```tsx
import { DataExportSettings } from '@/pages/settings/DataExportSettings';

// DataExportSettings internally uses similar functionality
```

### With Other Components
ExportButton integrates seamlessly with:
- Admin dashboards for system exports
- User settings pages for personal data exports
- Report generators for batch exports
- Analytics dashboards for data downloads

## Future Enhancements

Potential improvements for future versions:

1. **Batch Operations**: Export multiple data types simultaneously
2. **Custom Scope Selection**: Let users choose exactly what to export
3. **Schedule Exports**: Automatic recurring exports
4. **Email Delivery**: Send exports directly to email
5. **Format Options**: CSV encoding, JSON compression
6. **Export Templates**: Save and reuse export configurations
7. **Encryption**: Optional export encryption
8. **Data Filtering**: Pre-export filtering options
9. **Webhook Notifications**: Notify on completion
10. **S3 Integration**: Direct upload to cloud storage

## Troubleshooting

### Export not starting
- Check network connectivity
- Verify authentication token is valid
- Check browser console for errors

### Download link unavailable
- Export may have expired (7-day limit)
- Try initiating a new export
- Check that your browser allows downloads

### Large files timing out
- Consider breaking into smaller exports
- Check network connection stability
- Increase browser timeout settings

### Status not updating
- Refresh the page
- Check that JavaScript is enabled
- Verify no browser extensions are blocking requests

## Contributing

When modifying this component:

1. Update tests to maintain coverage
2. Document new props/types
3. Update examples for new features
4. Run all tests before committing
5. Follow existing code style

## License

Part of THE_BOT Platform. See main LICENSE file.

## Support

For issues or feature requests:
- Check existing GitHub issues
- Review API documentation
- Contact development team
- Check component examples for usage patterns
