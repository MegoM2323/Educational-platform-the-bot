# Loading States & Skeleton Loaders Guide

Comprehensive collection of reusable loading state components for building smooth, accessible loading experiences in the THE_BOT platform.

## Table of Contents

- [Quick Start](#quick-start)
- [Components](#components)
- [Accessibility](#accessibility)
- [Performance & CLS](#performance--cls)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Quick Start

### Import Components

```tsx
import {
  Spinner,
  LoadingState,
  ProgressBar,
  CardSkeleton,
  SkeletonWrapper,
} from '@/components/common';
```

### Basic Usage

```tsx
// Simple spinner
<Spinner size="md" />

// Loading state with text
<LoadingState isLoading={loading} text="Loading..." />

// Conditional rendering
<SkeletonWrapper
  isLoading={loading}
  skeleton={<CardSkeleton />}
>
  {/* Actual content */}
</SkeletonWrapper>
```

## Components

### Spinner

Animated loading spinner with configurable sizes.

```tsx
<Spinner
  size="md"           // 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  className="text-primary"
  ariaLabel="Loading data..."
/>
```

**Props:**
- `size`: Size variant (default: 'md')
- `className`: Additional CSS classes
- `ariaLabel`: Accessibility label

**Sizes:**
- `xs`: 12px
- `sm`: 16px
- `md`: 24px (default)
- `lg`: 32px
- `xl`: 40px

---

### LoadingState

Shows a complete loading state with spinner and optional message.

```tsx
<LoadingState
  isLoading={true}
  size="lg"
  text="Loading user data..."
  fullHeight={false}
  ariaLabel="Loading..."
/>
```

**Props:**
- `isLoading`: Show/hide loading state
- `size`: Spinner size variant
- `text`: Optional loading message
- `fullHeight`: Use full viewport height (good for page loads)
- `className`: Additional CSS classes
- `ariaLabel`: Accessibility label

**When to use:**
- Page-level loading
- Full-screen data fetching
- Initial data load

---

### Skeleton

Base skeleton component with animation.

```tsx
<Skeleton
  className="h-4 w-full"
  animated={true}
  aria-hidden="true"
/>
```

**Props:**
- `className`: Custom dimensions and styling
- `animated`: Enable pulse animation (default: true)
- Standard HTML div attributes

---

### TextLineSkeleton

Single line skeleton for headings or short text.

```tsx
<TextLineSkeleton />
<TextLineSkeleton className="w-2/3" />
```

**Use for:**
- Headings
- Labels
- Single text elements

---

### ParagraphSkeleton

Multiple text lines with last line shorter.

```tsx
<ParagraphSkeleton
  lines={3}
  lastLineWidth="2/3"  // 'full' | '3/4' | '2/3' | '1/2'
/>
```

**Use for:**
- Article previews
- Descriptions
- Multi-line text content

---

### CardSkeleton

Complete card skeleton with optional image/header.

```tsx
<CardSkeleton
  hasImage={true}
  hasHeader={true}
/>
```

**Use for:**
- Material cards
- User cards
- Product cards
- Post cards

---

### TableSkeleton

Table structure with rows and columns.

```tsx
<TableSkeleton
  rows={5}
  columns={4}
/>
```

**Use for:**
- Data tables
- Graded submissions
- Progress tables
- Results lists

---

### ListSkeleton

Repeating list items with optional avatars.

```tsx
<ListSkeleton
  count={4}
  hasAvatar={true}
/>
```

**Use for:**
- User lists
- Message threads
- Chat rooms
- Activity feeds

---

### FormSkeleton

Form fields with label and input placeholders.

```tsx
<FormSkeleton fields={5} />
```

**Use for:**
- Form page loads
- Survey loading
- Filter form loading

---

### GridSkeleton

Grid layout with configurable items and aspect ratios.

```tsx
<GridSkeleton
  count={6}
  columns={3}
  aspectRatio="square"  // 'square' | 'video' | '3/4'
/>
```

**Use for:**
- Image galleries
- Material grids
- Dashboard grids
- Product grids

---

### ProgressBar

Animated progress indicator with optional percentage label.

```tsx
<ProgressBar
  progress={65}
  max={100}
  size="md"           // 'sm' | 'md' | 'lg'
  showLabel={true}
  animated={true}
/>
```

**Props:**
- `progress`: Current progress value
- `max`: Maximum value (default: 100)
- `size`: Height variant (default: 'md')
- `showLabel`: Show percentage text
- `animated`: Enable smooth transitions
- `ariaLabel`: Accessibility label

**Use for:**
- File uploads
- Page progress
- Form completion
- Loading status

---

### LoadingOverlay

Overlay with spinner that covers content while loading.

```tsx
<LoadingOverlay
  isLoading={loading}
  message="Processing..."
  blur={true}
>
  <YourContent />
</LoadingOverlay>
```

**Props:**
- `isLoading`: Show/hide overlay
- `message`: Optional status message
- `blur`: Apply backdrop blur (default: true)
- `className`: Additional CSS classes

**Use for:**
- Form submissions
- Data mutations
- Dialog operations
- Modal operations

---

### ShimmerSkeleton

Advanced skeleton with shimmer animation effect.

```tsx
<ShimmerSkeleton className="h-64 w-full rounded-lg" />
```

**Properties:**
- Smooth flowing shimmer animation
- Modern appearance
- Reduces CLS

**Use for:**
- High-visibility placeholders
- Images
- Cards
- Hero sections

---

### PulseSkeleton

Pulsing skeleton with fade animation.

```tsx
<PulseSkeleton className="h-40 w-full">
  {/* Optional content */}
</PulseSkeleton>
```

**Use for:**
- Subtle placeholders
- Background elements
- Secondary content

---

### SkeletonWrapper

Conditional component that switches between skeleton and content.

```tsx
<SkeletonWrapper
  isLoading={loading}
  skeleton={<CardSkeleton />}
>
  {/* Actual content */}
</SkeletonWrapper>
```

**Props:**
- `isLoading`: Show skeleton or content
- `skeleton`: Skeleton component
- `children`: Actual content

**Benefits:**
- Single source of truth for loading state
- Clean conditional logic
- Consistent placeholder sizing

## Accessibility

All loading components include proper accessibility attributes:

### ARIA Attributes

```tsx
// Spinner announces loading state
<Spinner role="status" aria-label="Loading..." aria-live="polite" />

// Progress bar shows progress
<ProgressBar role="progressbar" aria-valuenow={75} aria-valuemin={0} aria-valuemax={100} />

// Skeletons are hidden from screen readers
<Skeleton aria-hidden="true" />
```

### Best Practices

1. **Use `aria-label`** for spinners and loading states
   ```tsx
   <Spinner ariaLabel="Loading user data..." />
   ```

2. **Use `aria-live="polite"`** for status updates
   - Announces changes to screen readers
   - Non-intrusive (doesn't interrupt)

3. **Hide skeletons from screen readers**
   ```tsx
   <Skeleton aria-hidden="true" />
   ```

4. **Provide context** for long-running operations
   ```tsx
   <LoadingState text="This might take a minute..." />
   ```

5. **Use semantic HTML**
   ```tsx
   <div role="status" aria-label="Page loading...">
     <Spinner />
   </div>
   ```

### Testing Accessibility

```tsx
import { screen } from '@testing-library/react';

// Test ARIA attributes
expect(screen.getByRole('status')).toHaveAttribute('aria-label');

// Test live regions
expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');

// Test hidden elements
expect(skeleton).toHaveAttribute('aria-hidden', 'true');
```

## Performance & CLS

### Cumulative Layout Shift (CLS)

Skeletons **reduce CLS** by:
- Providing exact layout before content loads
- Preventing layout jumps on content arrival
- Using same dimensions as final content

### Best Practices

1. **Match skeleton dimensions to content**
   ```tsx
   // Bad: Mismatch causes layout shift
   <SkeletonWrapper
     skeleton={<CardSkeleton />}           // h-40
     isLoading={loading}
   >
     <Card className="h-64">...</Card>    // h-64 - CLS!
   </SkeletonWrapper>

   // Good: Same dimensions
   <SkeletonWrapper
     skeleton={<CardSkeleton className="h-64" />}
     isLoading={loading}
   >
     <Card className="h-64">...</Card>
   </SkeletonWrapper>
   ```

2. **Use responsive skeletons**
   ```tsx
   <SkeletonWrapper
     skeleton={<CardSkeleton className="h-40 sm:h-48 lg:h-64" />}
     isLoading={loading}
   >
     <Card className="h-40 sm:h-48 lg:h-64">...</Card>
   </SkeletonWrapper>
   ```

3. **Preload skeleton on component mount**
   ```tsx
   // Skeleton appears immediately, no flash
   const [loading, setLoading] = useState(true);

   return (
     <SkeletonWrapper
       isLoading={loading}
       skeleton={<CardSkeleton />}
     >
       {data}
     </SkeletonWrapper>
   );
   ```

## Examples

### 1. Loading a User Card

```tsx
function UserProfile({ userId }: { userId: string }) {
  const { user, loading } = useUser(userId);

  return (
    <SkeletonWrapper
      isLoading={loading}
      skeleton={<CardSkeleton hasImage hasHeader />}
    >
      {user && (
        <Card>
          <img src={user.avatar} className="w-full h-40 object-cover" />
          <div className="p-4">
            <h3 className="text-lg font-semibold">{user.name}</h3>
            <p className="text-muted-foreground">{user.bio}</p>
          </div>
        </Card>
      )}
    </SkeletonWrapper>
  );
}
```

### 2. Loading a Data Table

```tsx
function MaterialsList() {
  const { materials, loading } = useMaterials();

  return (
    <div>
      {loading ? (
        <TableSkeleton rows={10} columns={4} />
      ) : (
        <DataTable data={materials} />
      )}
    </div>
  );
}
```

### 3. Loading with Progress

```tsx
function FileUpload() {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  return (
    <LoadingOverlay isLoading={uploading} message="Uploading...">
      <ProgressBar
        progress={uploadProgress}
        showLabel
      />
    </LoadingOverlay>
  );
}
```

### 4. Loading Chat Messages

```tsx
function ChatThread({ threadId }: { threadId: string }) {
  const { messages, loading } = useChatMessages(threadId);

  return (
    <SkeletonWrapper
      isLoading={loading}
      skeleton={<ListSkeleton count={5} hasAvatar />}
    >
      {messages.map(msg => (
        <ChatMessage key={msg.id} message={msg} />
      ))}
    </SkeletonWrapper>
  );
}
```

### 5. Loading a Form

```tsx
function EditProfile() {
  const { profile, loading } = useProfile();
  const { mutate, isPending } = useUpdateProfile();

  return (
    <div>
      {loading ? (
        <FormSkeleton fields={6} />
      ) : (
        <form onSubmit={handleSubmit}>
          {/* Form fields */}
          <LoadingOverlay isLoading={isPending}>
            <Button type="submit">Save</Button>
          </LoadingOverlay>
        </form>
      )}
    </div>
  );
}
```

### 6. Image Gallery Loading

```tsx
function MaterialGallery() {
  const { materials, loading } = useMaterials();

  return (
    <SkeletonWrapper
      isLoading={loading}
      skeleton={
        <GridSkeleton count={9} columns={3} aspectRatio="square" />
      }
    >
      <div className="grid grid-cols-3 gap-4">
        {materials.map(material => (
          <ImageCard key={material.id} material={material} />
        ))}
      </div>
    </SkeletonWrapper>
  );
}
```

## Best Practices

### 1. Choose the Right Component

| Use Case | Component | Notes |
|----------|-----------|-------|
| Full page load | `LoadingState` with `fullHeight` | Shows spinner in viewport |
| Card content | `CardSkeleton` | Maintains card layout |
| Text content | `ParagraphSkeleton` | Matches text dimensions |
| Tables | `TableSkeleton` | Preserves table structure |
| Lists | `ListSkeleton` | Shows item structure |
| Forms | `FormSkeleton` | Shows form fields |
| Galleries | `GridSkeleton` | Maintains grid layout |
| Overlays | `LoadingOverlay` | Covers content during mutation |

### 2. Dimension Matching

```tsx
// GOOD: Skeleton dimensions match final content
<SkeletonWrapper
  isLoading={loading}
  skeleton={<div className="h-64 w-full">...</div>}
>
  <div className="h-64 w-full">{content}</div>
</SkeletonWrapper>

// BAD: Dimension mismatch causes layout shift
<SkeletonWrapper
  isLoading={loading}
  skeleton={<div className="h-40">...</div>}
>
  <div className="h-64">{content}</div>
</SkeletonWrapper>
```

### 3. Responsive Skeletons

```tsx
// Adjust skeleton on different screen sizes
<SkeletonWrapper
  isLoading={loading}
  skeleton={
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  }
>
  {/* Content with same grid structure */}
</SkeletonWrapper>
```

### 4. Accessibility Testing

```tsx
// Test that loading states are announced
test('announces loading to screen readers', () => {
  render(<LoadingState isLoading text="Loading..." />);
  expect(screen.getByRole('status')).toHaveAttribute('aria-label');
});

// Test that skeletons are hidden from screen readers
test('hides skeletons from screen readers', () => {
  const { container } = render(<CardSkeleton />);
  expect(container.querySelector('[aria-hidden="true"]')).toBeInTheDocument();
});
```

### 5. Performance Optimization

```tsx
// Use React.memo to prevent unnecessary re-renders
const MemoizedCardSkeleton = React.memo(CardSkeleton);

// Use useMemo for dynamic skeletons
const dynamicSkeleton = useMemo(
  () => <CardSkeleton className={className} />,
  [className]
);
```

### 6. Error State Handling

```tsx
function SafeDataLoad() {
  const { data, loading, error } = useFetch();

  if (error) {
    return <ErrorState error={error.message} />;
  }

  return (
    <SkeletonWrapper
      isLoading={loading}
      skeleton={<CardSkeleton />}
    >
      {data && <DataCard data={data} />}
    </SkeletonWrapper>
  );
}
```

## TypeScript

All components are fully typed with TypeScript:

```tsx
// Component props are typed
interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  animated?: boolean;
}

// Use type inference
const MySkeleton: React.FC<SkeletonProps> = (props) => {
  return <Skeleton {...props} />;
};
```

## Common Patterns

### Pattern: Loading with Retry

```tsx
function LoadWithRetry() {
  const [retrying, setRetrying] = useState(false);
  const { data, loading, error, refetch } = useFetch();

  const handleRetry = async () => {
    setRetrying(true);
    await refetch();
    setRetrying(false);
  };

  return (
    <div>
      {loading && <CardSkeleton />}
      {error && <ErrorState error={error} onRetry={handleRetry} />}
      {data && <DataCard data={data} />}
    </div>
  );
}
```

### Pattern: Progressive Loading

```tsx
function ProgressiveLoad() {
  const [initialLoading, setInitialLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const { data } = useFetch();

  return (
    <div>
      {initialLoading ? (
        <CardSkeleton />
      ) : (
        <LoadingOverlay isLoading={updating}>
          <DataCard data={data} />
        </LoadingOverlay>
      )}
    </div>
  );
}
```

### Pattern: Optimistic Updates

```tsx
function OptimisticUpdate() {
  const [optimisticData, setOptimisticData] = useState(null);
  const { mutate, isPending } = useMutation();

  const handleUpdate = (newData) => {
    setOptimisticData(newData);
    mutate(newData, {
      onError: () => setOptimisticData(null),
    });
  };

  return (
    <LoadingOverlay isLoading={isPending}>
      <DataCard data={optimisticData || originalData} />
    </LoadingOverlay>
  );
}
```

## Troubleshooting

### Skeleton appears too briefly

**Problem:** Users don't see the skeleton because data loads too fast.

**Solution:** Use a minimum delay with loading state
```tsx
const [minLoadingTime] = useState(300); // ms
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const startTime = Date.now();
  fetchData().then(data => {
    const elapsed = Date.now() - startTime;
    const delay = Math.max(0, minLoadingTime - elapsed);
    setTimeout(() => {
      setData(data);
      setLoading(false);
    }, delay);
  });
}, []);
```

### Layout shift issues

**Problem:** Content jumps when skeleton is replaced.

**Solution:** Ensure exact dimension matching
```tsx
// Get dimensions from CSS
const CARD_HEIGHT = 'h-64';

<SkeletonWrapper
  skeleton={<CardSkeleton className={CARD_HEIGHT} />}
  isLoading={loading}
>
  <Card className={CARD_HEIGHT}>...</Card>
</SkeletonWrapper>
```

### Accessibility issues

**Problem:** Screen readers don't announce loading state.

**Solution:** Use proper ARIA attributes
```tsx
<div role="status" aria-label="Loading user data..." aria-live="polite">
  <Spinner />
</div>
```

## Support

For issues or questions about loading components:
1. Check this guide for examples
2. Review the test file for detailed usage patterns
3. Check TypeScript types for available props
4. Check component JSDoc comments for detailed explanations
