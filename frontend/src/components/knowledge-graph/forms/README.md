# Knowledge Graph Form Components

This directory contains form components for creating and managing elements and lessons in the Knowledge Graph system.

## Components

### CreateElementForm

A comprehensive form for creating educational elements with type-specific fields.

**Features:**
- Element type selection (text_problem, quick_question, theory, video)
- Dynamic fields based on selected type
- Full validation with Zod schema
- Toast notifications for success/error
- Form reset after successful submission
- Unsaved changes warning
- Loading states
- Responsive design

**Usage:**
```tsx
import { CreateElementForm } from '@/components/knowledge-graph/forms';

const handleSubmit = async (data: ElementFormData) => {
  const response = await elementAPI.create(data);
  return response;
};

<CreateElementForm
  onSubmit={handleSubmit}
  onCancel={() => setShowForm(false)}
  isLoading={isCreating}
/>
```

**Props:**
- `onSubmit: (data: ElementFormData) => Promise<void>` - Callback when form is submitted
- `onCancel?: () => void` - Optional callback for cancel button
- `initialData?: Partial<ElementFormData>` - Optional initial form values
- `isLoading?: boolean` - External loading state

**Field Types:**

**Text Problem:**
- Title (required, 3-200 chars)
- Description (optional, max 1000 chars)
- Content (required, max 10000 chars) - textarea for problem text

**Quick Question:**
- Title (required)
- Description (optional)
- Content (required) - question text
- Options (min 2, max 10) - dynamic list with add/remove
- Correct answer selection (radio buttons)

**Theory:**
- Title (required)
- Description (optional)
- Content (required, max 10000 chars) - rich text for theory material

**Video:**
- Title (required)
- Description (optional)
- Video URL (required, valid URL)
- Video Type (youtube, vimeo, other)
- Content (optional) - video description

### CreateLessonForm

Form for creating lessons by selecting and ordering elements from the content bank.

**Features:**
- Element search and filtering
- Multi-select elements with checkboxes
- Drag-drop reordering (manual with up/down buttons)
- Element preview with order numbers
- Difficulty selection
- Full validation
- Toast notifications
- Responsive design

**Usage:**
```tsx
import { CreateLessonForm } from '@/components/knowledge-graph/forms';

const { data: elements } = useQuery(['elements'], elementAPI.getAll);

const handleSubmit = async (data: LessonFormData) => {
  const response = await lessonAPI.create(data);
  return response;
};

<CreateLessonForm
  onSubmit={handleSubmit}
  availableElements={elements || []}
  onCancel={() => setShowForm(false)}
  isLoading={isCreating}
/>
```

**Props:**
- `onSubmit: (data: LessonFormData) => Promise<void>` - Callback when form is submitted
- `onCancel?: () => void` - Optional callback for cancel button
- `availableElements: Element[]` - List of elements available for selection
- `isLoading?: boolean` - External loading state

**Fields:**
- Title (required, 3-200 chars)
- Description (optional, max 1000 chars)
- Difficulty (easy, medium, hard)
- Elements (min 1, max 50) - selected from bank

### ElementTypeFields

Internal component that renders type-specific fields for CreateElementForm.

**Usage:**
```tsx
import { ElementTypeFields } from './ElementTypeFields';

<ElementTypeFields form={form} elementType={selectedType} />
```

**Props:**
- `form: UseFormReturn<ElementFormData>` - React Hook Form instance
- `elementType: 'text_problem' | 'quick_question' | 'theory' | 'video'` - Current element type

## Validation

All forms use Zod schemas defined in `/src/schemas/knowledge-graph.ts`.

### Element Schema Validation

```typescript
{
  type: enum (required),
  title: string (3-200 chars, required),
  description: string (max 1000 chars, optional),
  content: string (1-10000 chars, required),
  options: array (for quick_question only, min 2, max 10),
  video_url: url (for video type, required if video),
  video_type: enum (optional)
}
```

**Custom Validation:**
- Quick questions must have at least 2 options
- Quick questions must have at least 1 correct answer
- Video elements must have a valid video_url
- Options limited to 10 maximum

### Lesson Schema Validation

```typescript
{
  title: string (3-200 chars, required),
  description: string (max 1000 chars, optional),
  difficulty: enum (easy, medium, hard, required),
  element_ids: array (min 1, max 50, required)
}
```

## Error Handling

Both forms implement comprehensive error handling:

1. **Field-level validation** - Errors shown below each field
2. **Form-level validation** - Schema validation with Zod
3. **API errors** - Caught and displayed via toast notifications
4. **Loading states** - Disabled submit button during submission
5. **Success feedback** - Toast notification and success banner

## Styling

All components use:
- ShadcN UI components (Button, Input, Textarea, Select, Card, etc.)
- Tailwind CSS for styling
- Lucide React icons
- Responsive design (mobile-first)
- Proper spacing and layout

## Accessibility

- Proper ARIA labels via FormLabel
- Keyboard navigation support
- Focus management
- Error announcements
- Semantic HTML structure

## TypeScript

All components are fully typed with:
- React.FC<Props> for components
- Zod schema inference for form data types
- Explicit prop interfaces
- No `any` types

## Testing Recommendations

### Unit Tests

Test with @testing-library/react:
- Form submission with valid data
- Validation errors for invalid data
- Type-specific field rendering
- Element selection/deselection
- Element reordering
- Form reset functionality

### Integration Tests

- Full form workflow (fill → submit → success)
- API error handling
- Multiple elements/lessons creation
- Search/filter functionality

### E2E Tests

With Playwright:
- Create element of each type
- Create lesson with multiple elements
- Reorder elements in lesson
- Validation error flows
- Cancel/reset flows

## Files

```
forms/
├── CreateElementForm.tsx       # Main element creation form
├── CreateLessonForm.tsx        # Main lesson creation form
├── ElementTypeFields.tsx       # Type-specific field renderer
├── index.ts                    # Export barrel
└── README.md                   # This file
```

## Dependencies

- `react-hook-form` - Form state management
- `@hookform/resolvers/zod` - Zod schema resolver
- `zod` - Schema validation
- `@/components/ui/*` - ShadcN UI components
- `lucide-react` - Icons
- `@/hooks/use-toast` - Toast notifications

## Future Enhancements

Potential improvements:
- Rich text editor for theory content
- Drag-drop reordering with react-beautiful-dnd
- Auto-save drafts to localStorage
- Image upload for elements
- Preview mode before submission
- Bulk import elements
- Element templates
- Lesson duplication
