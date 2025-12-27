# Material Form Frontend Validation (T_MAT_011)

## Overview

This document describes the implementation of the `MaterialForm` component, a comprehensive React form for creating and editing educational materials with real-time validation using React Hook Form and Zod.

## Features

### 1. Real-time Validation
- **React Hook Form** for form state management
- **Zod** for schema validation
- Field-level error messages with icons
- Visual error indicators (red borders, error text)

### 2. Field Validation

#### Title Field
- **Required**: Yes
- **Max Length**: 200 characters
- **Features**:
  - Character counter (e.g., "13/200")
  - Real-time feedback
  - Trimmed input

#### Description Field
- **Required**: No (optional)
- **Max Length**: 5000 characters
- **Features**:
  - Character counter (e.g., "0/5000")
  - Textarea with 3 rows default
  - Help text explaining optional nature

#### Content Field
- **Required**: Yes
- **Max Length**: 50000 characters
- **Features**:
  - Character counter (e.g., "0/50000")
  - Collapsible view (Show/Hide button)
  - Textarea with 8 rows when expanded, 4 when collapsed
  - Real-time character count display
  - Visual toggle button

#### Subject Field
- **Required**: Yes
- **Validation**: Selected value must be from available subjects
- **Features**:
  - Dropdown select component
  - Loads subjects from `/materials/subjects/` API
  - Error message if not selected

#### Type Field
- **Required**: Yes
- **Options**: lesson, homework, test, document
- **Validation**: Must be one of the predefined types
- **Features**: Dropdown select with clear options

#### Status Field
- **Optional**: Yes
- **Options**: draft, active
- **Default**: draft
- **Features**: Dropdown select, defaults to draft

#### Difficulty Level
- **Optional**: Yes
- **Range**: 1-5
- **Default**: 1
- **Features**: Dropdown select with 5 levels

#### Tags Field
- **Optional**: Yes
- **Max Length**: 500 characters
- **Features**:
  - Comma-separated tags
  - Help text suggesting format
  - Field-level validation

#### Video URL Field
- **Optional**: Yes
- **Validation**: Must be valid URL (if provided)
- **Features**:
  - URL validation using Zod
  - Placeholder with example
  - Error message for invalid URLs

#### Public Checkbox
- **Optional**: Yes
- **Default**: false
- **Features**:
  - Styled checkbox with label
  - Description explaining meaning
  - Toggle to make material public

### 3. File Upload Validation

#### File Constraints
- **Max Size**: 10MB
- **Allowed Types**: pdf, doc, docx, ppt, pptx, txt, jpg, jpeg, png

#### Features
- **File Validation**:
  - Automatic type checking
  - Size validation with clear error messages
  - File extension verification

- **File Preview**:
  - Shows filename and size (in KB)
  - Green success indicator
  - File remove button

- **Error Handling**:
  - Clear error messages for oversized files
  - Type mismatch errors with supported formats list
  - Visual error state with red background

- **Help Text**:
  - Maximum file size displayed
  - List of supported formats
  - Clear guidance for optional nature

### 4. UI/UX Enhancements

#### Visual Feedback
- Alert icons for errors
- Check icons for successful file upload
- Disabled state during submission
- Loading spinner in submit button

#### Responsive Design
- Grid layout for paired fields (2 columns on desktop, 1 on mobile)
- Mobile-friendly file input
- Proper spacing and padding
- Accessible form labels

#### Accessibility
- Proper label associations (htmlFor)
- ARIA attributes where applicable
- Keyboard navigation support
- Screen reader friendly error messages

#### Form State Management
- Disabled inputs during submission
- Loading states
- Real-time character counters
- Show/Hide toggle for large content field

## File Structure

```
frontend/src/components/forms/
├── MaterialForm.tsx                    # Main form component
├── __tests__/
│   └── MaterialForm.test.tsx           # Unit tests
└── MATERIAL_FORM_IMPLEMENTATION.md     # This file
```

## Usage

### Basic Usage

```tsx
import { MaterialForm } from "@/components/forms/MaterialForm";

function CreateMaterialPage() {
  const handleSubmit = async (formData, file) => {
    // Handle form submission
    // Send to backend API
  };

  return (
    <MaterialForm
      onSubmit={handleSubmit}
      onCancel={() => navigate("/materials")}
    />
  );
}
```

### With Initial Data (Editing)

```tsx
<MaterialForm
  onSubmit={handleSubmit}
  onCancel={handleCancel}
  initialData={{
    title: "Existing Material",
    description: "Description",
    content: "Content",
    subject: "1",
    type: "lesson",
    status: "active"
  }}
  isEditing={true}
/>
```

### With Loading State

```tsx
<MaterialForm
  onSubmit={handleSubmit}
  isLoading={isSubmitting}
/>
```

## Validation Schema (Zod)

```typescript
const materialFormSchema = z.object({
  title: z.string()
    .min(1, "Название материала обязательно")
    .max(200, "Название не может быть длиннее 200 символов")
    .trim(),
  description: z.string()
    .max(5000, "Описание не может быть длиннее 5000 символов")
    .optional()
    .default(""),
  content: z.string()
    .min(1, "Содержание материала обязательно")
    .max(50000, "Содержание не может быть длиннее 50000 символов"),
  subject: z.string()
    .min(1, "Выберите предмет"),
  type: z.enum(["lesson", "homework", "test", "document"]),
  status: z.enum(["draft", "active"]).optional().default("draft"),
  difficulty_level: z.number().min(1).max(5).optional().default(1),
  is_public: z.boolean().optional().default(false),
  tags: z.string().max(500).optional().default(""),
  video_url: z.string().url().optional().or(z.literal(""))
});
```

## API Integration

### Form Submission Flow

1. **Validate** with Zod schema
2. **Prepare FormData** with file if present
3. **POST/PATCH** to `/api/materials/`
4. **Handle Response**:
   - Success: Navigate to materials list
   - Error: Display field-specific or general error messages

### Subject Loading

```typescript
// Automatically loads from:
GET /api/materials/subjects/

// Displays in dropdown with format:
{
  id: number;
  name: string;
  description: string;
  color: string;
}
```

## Error Handling

### Field-Level Errors
- Displayed below each field
- Red border on invalid fields
- Clear error message text
- Alert icon for visual indication

### File Errors
- Size validation messages
- Type validation messages
- Displayed in red box below file input
- Prevents form submission until fixed

### Server Errors
- Caught in onSubmit callback
- Mapped to field-specific errors when possible
- General toast notifications for non-field errors

### Example Error Messages

| Error | Message |
|-------|---------|
| Title empty | "Название материала обязательно" |
| Title too long | "Название не может быть длиннее 200 символов" |
| File too large | "Размер файла не должен превышать 10MB. Ваш файл: 15.50MB" |
| Invalid file type | "Неподдерживаемый тип файла "exe". Разрешенные форматы: pdf, doc, docx..." |
| Invalid URL | "Некорректный URL видео" |

## Testing

### Test Coverage

The component includes comprehensive unit tests covering:

- **Rendering**: All form fields and labels render correctly
- **Validation**:
  - Required fields validation
  - Character limit validation
  - File size validation
  - File type validation
  - URL format validation
- **User Interactions**:
  - Form submission
  - File upload and removal
  - Character counter updates
  - Show/hide toggle
- **Props**:
  - Initial data pre-filling
  - Edit mode display
  - Loading state

### Running Tests

```bash
cd frontend
npm test -- src/components/forms/__tests__/MaterialForm.test.tsx
```

### Test Examples

```typescript
// Validate title max length
it("validates title max length (200 chars)", async () => {
  const user = userEvent.setup();
  render(<MaterialForm onSubmit={mockOnSubmit} />);

  const titleInput = screen.getByLabelText(/название материала/i);
  await user.type(titleInput, "a".repeat(201));

  const submitButton = screen.getByRole("button", { name: /создать материал/i });
  await user.click(submitButton);

  await waitFor(() => {
    expect(screen.getByText(/название не может быть длиннее 200 символов/i))
      .toBeInTheDocument();
  });
});

// Validate file size
it("validates file size", async () => {
  const user = userEvent.setup();
  render(<MaterialForm onSubmit={mockOnSubmit} />);

  const fileInput = screen.getByLabelText(/прикрепить файл материала/i);
  const largeFile = new File(["x".repeat(11 * 1024 * 1024)], "large.pdf");

  await user.upload(fileInput, largeFile);

  await waitFor(() => {
    expect(screen.getByText(/размер файла не должен превышать/i))
      .toBeInTheDocument();
  });
});
```

## Integration with CreateMaterial Page

The `CreateMaterial.tsx` page has been refactored to use the new `MaterialForm` component:

### Before
- Inline form validation
- Manual state management
- Mixed concerns (form + student assignment)

### After
- Reusable `MaterialForm` component
- Centralized validation with Zod
- Separated concerns
- Student assignment in separate card

### Component Hierarchy

```
CreateMaterial (Page)
├── MaterialForm (Component)
│   ├── Title Input
│   ├── Description Textarea
│   ├── Content Textarea
│   ├── Subject Select
│   ├── Type Select
│   ├── Status Select
│   ├── Difficulty Select
│   ├── Tags Input
│   ├── Video URL Input
│   ├── File Upload
│   └── Public Checkbox
└── Student Assignment Card
    ├── Select All Button
    ├── Clear All Button
    └── Student Badges
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android)

## Performance Considerations

1. **Character Counter**: Updates only on field change
2. **File Validation**: Synchronous (no network calls)
3. **Subject Loading**: Cached in component state
4. **Form Submission**: Disabled during submission to prevent duplicates
5. **Re-renders**: Optimized with React Hook Form's internal state

## Accessibility Features

- Semantic HTML structure
- Label associations (htmlFor)
- ARIA attributes for error messages
- Keyboard navigation support
- Screen reader friendly field names
- Color not the only indicator of errors (also uses icons and text)

## Styling

The component uses:
- **Tailwind CSS** for styling
- **shadcn/ui** components for consistency
- **Lucide React** icons for visual indicators
- **CSS Grid** for responsive layouts

## Localization

All text is in Russian with proper formatting:
- Error messages
- Label text
- Placeholder text
- Help text

To support multiple languages in the future:
1. Extract all text to i18n keys
2. Use translation framework
3. Update error messages

## Migration Guide

### From Old Form to MaterialForm

```typescript
// Old way - inline form
const [formData, setFormData] = useState({...});
const [errors, setErrors] = useState({});

// New way - use MaterialForm
<MaterialForm
  onSubmit={handleFormSubmit}
  initialData={materialData}
  isEditing={isEdit}
/>
```

## Future Enhancements

1. **Rich Text Editor** for content field (instead of textarea)
2. **Drag-and-drop** file upload
3. **Image preview** for uploaded images
4. **Material tags autocomplete** from existing tags
5. **Video URL preview** (YouTube thumbnail)
6. **Bulk student assignment** from CSV
7. **Scheduled publishing** date/time picker
8. **Material templates** for quick creation

## Related Components

- `CreateMaterial.tsx` - Page using MaterialForm
- `MaterialSubmissionForm.tsx` - Student submission form (different component)
- `ValidationMessage.tsx` - Reusable validation display component

## API Reference

### Props

```typescript
interface MaterialFormProps {
  /** Callback when form is submitted successfully */
  onSubmit: (data: MaterialFormData, file: File | null) => Promise<void>;

  /** Optional callback when form is cancelled */
  onCancel?: () => void;

  /** Pre-fill form with existing data (for editing) */
  initialData?: Partial<MaterialFormData>;

  /** Whether this is an edit operation (affects title and button text) */
  isEditing?: boolean;

  /** Whether form is currently submitting (disables fields) */
  isLoading?: boolean;
}
```

### Form Data Type

```typescript
type MaterialFormData = {
  title: string;
  description: string;
  content: string;
  subject: string;
  type: "lesson" | "homework" | "test" | "document";
  status?: "draft" | "active";
  is_public?: boolean;
  tags: string;
  difficulty_level?: number;
  video_url: string;
};
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Form not submitting | Check if all required fields are filled |
| Character counter not updating | Verify onChange event is firing |
| File upload not working | Check file size and type validation |
| Validation errors not showing | Ensure form is submitted (not just field blur) |
| Subjects not loading | Verify `/materials/subjects/` API endpoint |

## Version History

- **v1.0.0** (2025-12-27): Initial implementation
  - React Hook Form integration
  - Zod validation schema
  - File upload with validation
  - Character counters
  - Responsive design
  - Comprehensive test suite
