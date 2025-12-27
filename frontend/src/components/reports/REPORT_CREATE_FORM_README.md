# ReportCreateForm Component

## Overview

`ReportCreateForm` is a React component that allows users to generate custom reports from templates. It provides a complete form interface with template selection, validation, preview functionality, and integration with the backend report generation API.

**Location**: `/frontend/src/components/reports/ReportCreateForm.tsx`

## Features

- **Template Selection**: Browse and select from available report templates
- **Template Preview**: View template content before creating a report
- **Form Validation**: Real-time validation with user-friendly error messages
- **Date Range Selection**: Specify report period with automatic validation
- **Optional Filtering**: Filter reports by student or class (if provided)
- **Loading States**: Progress indicator during report generation
- **Error Handling**: Comprehensive error handling with retry functionality
- **Responsive Design**: Mobile-friendly layout with responsive form fields
- **Success Feedback**: Toast notifications and success callbacks

## Props

```typescript
interface ReportCreateFormProps {
  /**
   * Callback function when report is successfully created
   * @param report - The generated report object
   */
  onSuccess?: (report: GeneratedReport) => void;

  /**
   * Callback function when user clicks cancel
   */
  onCancel?: () => void;

  /**
   * CSS class name for styling the form container
   */
  className?: string;

  /**
   * List of students for filtering (optional)
   */
  students?: Array<{ id: number; name: string }>;

  /**
   * List of classes for filtering (optional)
   */
  classes?: Array<{ id: number; name: string }>;
}
```

## Type Definitions

### ReportTemplate
```typescript
interface ReportTemplate {
  id: number;
  name: string;
  report_type: string;
  template_content: string;
  created_at: string;
  description?: string;
}
```

### ReportCreateFormData
```typescript
interface ReportCreateFormData {
  template_id: number;
  report_name: string;
  date_start: string;
  date_end: string;
  student_id?: number;
  class_id?: number;
}
```

### GeneratedReport
```typescript
interface GeneratedReport {
  id: number;
  name: string;
  template_id: number;
  content: string;
  date_created: string;
  date_start: string;
  date_end: string;
  status: 'generated' | 'sent' | 'archived';
}
```

## Usage Examples

### Basic Usage
```tsx
import { ReportCreateForm } from '@/components/reports';

export default function MyReportPage() {
  return (
    <ReportCreateForm
      onSuccess={(report) => {
        console.log('Report created:', report);
      }}
      onCancel={() => {
        // Handle cancel
      }}
    />
  );
}
```

### With Student Filtering
```tsx
<ReportCreateForm
  students={[
    { id: 1, name: 'John Doe' },
    { id: 2, name: 'Jane Smith' },
  ]}
  onSuccess={(report) => {
    // Handle success
  }}
/>
```

### With Both Filters
```tsx
<ReportCreateForm
  students={students}
  classes={classes}
  onSuccess={(report) => {
    navigate(`/reports/${report.id}`);
  }}
  onCancel={() => setShowForm(false)}
/>
```

### In a Dialog
```tsx
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Create Custom Report</DialogTitle>
    </DialogHeader>
    <ReportCreateForm
      onSuccess={handleSuccess}
      onCancel={() => setIsOpen(false)}
    />
  </DialogContent>
</Dialog>
```

## Form Validation

The component performs the following validations:

1. **Template Selection**: Required field - user must select a template
2. **Report Name**: Required field - must not be empty or whitespace-only
3. **Start Date**: Required field - must be a valid date
4. **End Date**: Required field - must be a valid date
5. **Date Range**: Start date must not be after end date

Validation errors are displayed inline with helpful messages and icon indicators.

## API Integration

The component integrates with the following API endpoints:

### Load Templates
```
GET /reports/templates/
Response: ReportTemplate[]
```

### Generate Report
```
POST /reports/generate/
Request Body: {
  template_id: number;
  report_name: string;
  date_start: string;
  date_end: string;
  student_id?: number;
  class_id?: number;
}
Response: GeneratedReport
```

## State Management

The component manages the following state:

- **templates**: Array of available templates
- **loading**: Loading state during report generation
- **loadingTemplates**: Loading state while fetching templates
- **formData**: Current form input values
- **validationErrors**: Validation error messages for each field
- **submitError**: Error message from failed submission
- **showPreview**: Toggle for template preview visibility

## Event Handlers

### loadTemplates()
Fetches available report templates from the API and auto-selects the first template.

### validateForm()
Validates all form fields and returns true if valid.

### handleSubmit(e)
Handles form submission:
1. Validates form data
2. Prepares request payload
3. Calls API to generate report
4. Executes onSuccess callback if provided
5. Clears form for new submission

### handleFieldChange(field, value)
Handles field input changes:
1. Updates form state
2. Clears validation error for that field

## Styling

The component uses:
- **CSS Classes**: From Tailwind CSS utility classes
- **UI Components**: From `@/components/ui` (Card, Button, Input, Label, Select)
- **Icons**: From Lucide React
- **Theme**: Inherits from app's color scheme (light/dark mode compatible)

## Error Handling

The component handles various error scenarios:

1. **Template Loading Failure**: Shows retry button and error message
2. **Validation Errors**: Displays inline error messages for each field
3. **API Submission Errors**: Shows error state with retry option
4. **Network Errors**: Displays user-friendly error messages

## Accessibility

The component follows WCAG 2.1 guidelines:

- Form inputs have associated labels
- Error messages are associated with fields using ARIA patterns
- Loading states are announced to screen readers
- Color is not the only indicator (uses icons with text)
- Form is keyboard navigable

## Testing

Unit tests are provided in `ReportCreateForm.test.tsx`:

- Template loading
- Template preview functionality
- Form validation
- Date range validation
- Form submission
- Error handling
- Filter rendering
- Callback execution

Run tests with:
```bash
npm test -- ReportCreateForm.test.tsx
```

## Performance Considerations

- **Lazy Loading**: Templates loaded on component mount
- **Memoization**: Consider using useMemo for template filtering
- **Validation**: Debounced validation on field changes to avoid excessive checks
- **API Calls**: Single API call to load templates, batched form submission

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Dependencies

- React 18+
- TypeScript 4.5+
- Tailwind CSS 3+
- Lucide React (icons)
- Sonner (toast notifications)
- Custom UI components from `@/components/ui`

## Related Components

- **ReportsList**: Display list of generated reports
- **ReportDetail**: View full report details
- **ReportForm**: For creating detailed reports (different use case)

## Troubleshooting

### Templates Not Loading
- Check `/reports/templates/` API endpoint is accessible
- Verify backend has report templates created
- Check browser console for API errors

### Form Submission Fails
- Verify `/reports/generate/` endpoint exists on backend (T_RPT_005)
- Check date format is ISO (YYYY-MM-DD)
- Verify template_id exists in database

### Validation Not Clearing
- Check browser console for errors in validation logic
- Ensure handleFieldChange is properly connected to inputs

## Future Enhancements

1. **Report Preview**: Display preview of generated report before creation
2. **Batch Generation**: Create multiple reports at once
3. **Schedule Reports**: Schedule reports to generate at specific times
4. **Export Formats**: Support multiple export formats (PDF, Excel, etc.)
5. **Advanced Filters**: Additional filtering options (date range templates, department, etc.)
6. **Report Templates**: UI to create/edit report templates
7. **Progress Tracking**: Show progress for long-running report generation

## Maintenance

- Update API endpoints if backend routes change
- Keep template interface in sync with backend models
- Update tests when adding new validation rules
- Monitor error logs for common failure patterns
