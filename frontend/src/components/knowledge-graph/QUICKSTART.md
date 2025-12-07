# ElementCard Quick Start Guide

## Installation

Dependencies already installed:
- dompurify (^3.2.2)
- @types/dompurify (^3.2.0)

## Basic Usage

```tsx
import { ElementCard } from '@/components/knowledge-graph';
import type { Element, ElementAnswer } from '@/types/knowledgeGraph';

// Your component
const MyLessonPage = () => {
  // Example element data
  const element: Element = {
    id: '1',
    title: 'Квадратное уравнение',
    description: 'Решите уравнение x² - 5x + 6 = 0',
    element_type: 'text_problem',
    element_type_display: 'Текстовая задача',
    content: {
      problem_text: 'Решите уравнение: x² - 5x + 6 = 0',
      hints: ['Используйте дискриминант', 'D = b² - 4ac'],
    },
    difficulty: 5,
    estimated_time_minutes: 15,
    max_score: 100,
    tags: ['математика', 'алгебра'],
    is_public: true,
    created_by: {
      id: 1,
      name: 'Учитель',
      email: 'teacher@example.com',
      role: 'teacher',
    },
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
  };

  // Submit handler
  const handleSubmit = async (answer: ElementAnswer) => {
    // Call your API here
    console.log('Submitting answer:', answer);
    // await api.submitElementAnswer(element.id, answer);
  };

  return (
    <ElementCard
      element={element}
      onSubmit={handleSubmit}
    />
  );
};
```

## With Progress Tracking

```tsx
import { ElementCard } from '@/components/knowledge-graph';
import type { ElementProgress } from '@/types/knowledgeGraph';

const MyLessonPage = () => {
  const element = { /* ... */ };

  // Progress from API
  const progress: ElementProgress = {
    id: 'p1',
    student: 'student-uuid',
    student_name: 'Иван Иванов',
    element: element,
    graph_lesson: 'lesson-uuid',
    answer: { text: 'x = 2, x = 3' },
    score: 80,
    max_score: 100,
    score_percent: 80,
    status: 'completed',
    started_at: '2024-01-01T10:00:00Z',
    completed_at: '2024-01-01T10:15:00Z',
    time_spent_seconds: 900,
    attempts: 1,
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:15:00Z',
  };

  return (
    <ElementCard
      element={element}
      progress={progress}
      onSubmit={handleSubmit}
    />
  );
};
```

## Element Types Examples

### 1. Text Problem

```tsx
const textProblem: Element = {
  // ...base fields
  element_type: 'text_problem',
  content: {
    problem_text: 'Решите задачу...',
    hints: ['Подсказка 1', 'Подсказка 2'],
  },
};

// Answer format:
// { text: "user's answer" }
```

### 2. Quick Question

```tsx
const quickQuestion: Element = {
  // ...base fields
  element_type: 'quick_question',
  content: {
    question: 'Какой город столица России?',
    choices: ['Москва', 'СПб', 'Казань'],
    correct_answer: 0, // Index
  },
};

// Answer format:
// { choice: 0 }
```

### 3. Theory

```tsx
const theory: Element = {
  // ...base fields
  element_type: 'theory',
  content: {
    text: '<h2>Заголовок</h2><p>Текст...</p>',
    sections: [
      {
        title: 'Дополнительный раздел',
        content: '<p>Контент...</p>',
      },
    ],
  },
};

// Answer format:
// { viewed: true }
```

### 4. Video

```tsx
const video: Element = {
  // ...base fields
  element_type: 'video',
  content: {
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    title: 'Урок физики',
    description: 'Описание урока',
    duration_seconds: 600,
  },
};

// Answer format:
// { watched_until: 480 }
```

## Error Handling

```tsx
const handleSubmit = async (answer: ElementAnswer) => {
  try {
    await api.submitAnswer(element.id, answer);
  } catch (error) {
    throw error; // Will be caught by ElementCard
  }
};

const handleError = (error: Error) => {
  toast.error(`Ошибка: ${error.message}`);
};

<ElementCard
  element={element}
  onSubmit={handleSubmit}
  onError={handleError}
/>
```

## Loading State

```tsx
const [isSubmitting, setIsSubmitting] = useState(false);

const handleSubmit = async (answer: ElementAnswer) => {
  setIsSubmitting(true);
  try {
    await api.submitAnswer(element.id, answer);
  } finally {
    setIsSubmitting(false);
  }
};

<ElementCard
  element={element}
  onSubmit={handleSubmit}
  isLoading={isSubmitting}
/>
```

## Read-Only Mode

```tsx
// For teachers/admins viewing student work
<ElementCard
  element={element}
  progress={studentProgress}
  onSubmit={() => Promise.resolve()}
  readOnly={true}
/>
```

## TypeScript Types

All types are in `@/types/knowledgeGraph.ts`:

```tsx
import type {
  Element,
  ElementType,
  ElementContent,
  ElementProgress,
  ElementAnswer,
  ElementCardProps,
  TextProblemContent,
  QuickQuestionContent,
  TheoryContent,
  VideoContent,
  TextProblemAnswer,
  QuickQuestionAnswer,
  TheoryAnswer,
  VideoAnswer,
} from '@/types/knowledgeGraph';
```

## Common Patterns

### Loading Skeleton

```tsx
import { ElementCardSkeleton } from '@/components/knowledge-graph';

{isLoading ? <ElementCardSkeleton /> : <ElementCard {...props} />}
```

### Multiple Elements

```tsx
const LessonView = ({ elements, progress }) => {
  return (
    <div className="space-y-6">
      {elements.map((element) => (
        <ElementCard
          key={element.id}
          element={element}
          progress={progress[element.id]}
          onSubmit={(answer) => handleSubmit(element.id, answer)}
        />
      ))}
    </div>
  );
};
```

### With React Query

```tsx
import { useMutation } from '@tanstack/react-query';

const { mutateAsync: submitAnswer, isPending } = useMutation({
  mutationFn: (data: { elementId: string; answer: ElementAnswer }) =>
    api.submitElementAnswer(data.elementId, data.answer),
});

<ElementCard
  element={element}
  onSubmit={(answer) => submitAnswer({ elementId: element.id, answer })}
  isLoading={isPending}
/>
```

## Testing

```tsx
import { render, screen } from '@testing-library/react';
import { ElementCard } from '@/components/knowledge-graph';

test('renders text problem', () => {
  const element: Element = { /* ... */ };
  render(<ElementCard element={element} onSubmit={jest.fn()} />);

  expect(screen.getByText(element.title)).toBeInTheDocument();
});
```

## Troubleshooting

**Problem**: TypeScript errors about Element type
**Solution**: Make sure to import from `@/types/knowledgeGraph`

**Problem**: Video not loading
**Solution**: Check URL format (YouTube/Vimeo/file)

**Problem**: Answers not submitting
**Solution**: Check onSubmit returns Promise<void>

**Problem**: Progress not showing
**Solution**: Verify ElementProgress interface matches backend

## Next Steps

1. Create API client: `frontend/src/integrations/api/knowledgeGraphAPI.ts`
2. Create hooks: `frontend/src/hooks/useElement.ts`
3. Create pages: `frontend/src/pages/lessons/[id].tsx`
4. Add tests: `frontend/src/components/knowledge-graph/__tests__/`

## Support

See full documentation:
- `README.md` - Complete component docs
- `ElementCard.example.tsx` - Visual examples
- `IMPLEMENTATION_SUMMARY.md` - Technical details
