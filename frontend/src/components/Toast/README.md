# Toast Component System

Complete notification system with multiple toast types, auto-dismiss, and action buttons.

## Components

### 1. Toast Component

Basic toast notification with auto-dismiss and action support.

**Props:**
- `id` (string, required): Unique identifier for the toast
- `type` (ToastType, required): Toast type - 'success' | 'error' | 'warning' | 'info' | 'loading'
- `title` (string, required): Main message
- `description` (string, optional): Detailed message
- `duration` (number, optional): Auto-dismiss time in ms (default: type-based)
- `action` (object, optional): Action button with label and onClick
- `onClose` (function, required): Callback when toast is closed
- `autoClose` (boolean, optional): Enable auto-dismiss (default: true)

**Default Durations by Type:**
- Success: 3000ms
- Error: 5000ms
- Warning: 4000ms
- Info: 3000ms
- Loading: never (manual close only)

**Example:**
```tsx
import { Toast } from '@/components/Toast';

export const MyComponent = () => {
  const handleClose = (id: string) => {
    // Handle toast removal
  };

  return (
    <Toast
      id="toast-1"
      type="success"
      title="Success!"
      description="Your changes have been saved"
      duration={3000}
      onClose={handleClose}
    />
  );
};
```

### 2. ToastContainer

Manages and displays multiple toasts with positioning.

**Props:**
- `toasts` (ToastItem[], required): Array of toast objects
- `onRemove` (function, required): Callback to remove a toast
- `position` (string, optional): Toast position (default: 'top-right')
  - 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center'
- `maxToasts` (number, optional): Maximum visible toasts (default: 5)

**Example:**
```tsx
import { ToastContainer } from '@/components/Toast';
import { useState } from 'react';

export const MyComponent = () => {
  const [toasts, setToasts] = useState([
    {
      id: '1',
      type: 'success',
      title: 'Success',
      description: 'Operation completed'
    }
  ]);

  return (
    <ToastContainer
      toasts={toasts}
      onRemove={(id) => setToasts(prev => prev.filter(t => t.id !== id))}
      position="top-right"
      maxToasts={3}
    />
  );
};
```

### 3. ToastProvider & useToast Hook

Global context-based toast management for easy access from anywhere.

**Props (ToastProvider):**
- `children` (ReactNode, required): Child components
- `position` (string, optional): Default position (default: 'top-right')
- `maxToasts` (number, optional): Maximum visible toasts (default: 5)

**Hook Methods:**
- `showToast(type, title, options?)`: Show any type of toast
- `showSuccess(title, options?)`: Show success toast
- `showError(title, options?)`: Show error toast
- `showWarning(title, options?)`: Show warning toast
- `showInfo(title, options?)`: Show info toast
- `showLoading(title, options?)`: Show loading toast
- `removeToast(id)`: Remove specific toast
- `clearAll()`: Remove all toasts

**Example:**
```tsx
import { ToastProvider, useToast } from '@/components/Toast';

// Wrap your app with provider
function App() {
  return (
    <ToastProvider position="top-right" maxToasts={5}>
      <YourApp />
    </ToastProvider>
  );
}

// Use anywhere in your app
function MyComponent() {
  const toast = useToast();

  const handleSave = async () => {
    const id = toast.showLoading('Saving...');
    try {
      await saveData();
      toast.removeToast(id);
      toast.showSuccess('Saved successfully!');
    } catch (error) {
      toast.removeToast(id);
      toast.showError('Failed to save', {
        description: error.message,
        action: {
          label: 'Retry',
          onClick: handleSave
        }
      });
    }
  };

  return <button onClick={handleSave}>Save</button>;
}
```

## Usage Patterns

### Pattern 1: Global Toast Provider (Recommended)

Best for application-wide notifications:

```tsx
// main.tsx or app.tsx
import { ToastProvider } from '@/components/Toast';

export default function App() {
  return (
    <ToastProvider position="top-right" maxToasts={5}>
      <Router>
        <Routes>
          {/* Your routes */}
        </Routes>
      </Router>
    </ToastProvider>
  );
}

// Any component
import { useToast } from '@/components/Toast';

export function MyForm() {
  const toast = useToast();

  const handleSubmit = async (data) => {
    try {
      await api.post('/submit', data);
      toast.showSuccess('Submitted successfully!');
    } catch (error) {
      toast.showError('Submission failed', {
        description: error.message
      });
    }
  };

  return <form onSubmit={handleSubmit}>{/* form fields */}</form>;
}
```

### Pattern 2: Local Toast Container

For isolated notifications within a component:

```tsx
import { useState } from 'react';
import { ToastContainer } from '@/components/Toast';

export function MyComponent() {
  const [toasts, setToasts] = useState([]);

  const showToast = (type, title, description) => {
    const id = String(Date.now());
    setToasts(prev => [...prev, { id, type, title, description }]);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return (
    <div>
      <button onClick={() => showToast('success', 'Great!', 'It works')}>
        Show Toast
      </button>
      <ToastContainer toasts={toasts} onRemove={removeToast} position="bottom-right" />
    </div>
  );
}
```

### Pattern 3: Direct Toast Component

For simple, contained notifications:

```tsx
import { Toast } from '@/components/Toast';
import { useState } from 'react';

export function MyComponent() {
  const [visible, setVisible] = useState(true);

  return (
    <>
      {visible && (
        <Toast
          id="toast-1"
          type="info"
          title="Important Information"
          description="This is a critical alert"
          onClose={() => setVisible(false)}
          autoClose={false}
        />
      )}
      <button onClick={() => setVisible(true)}>Show Toast</button>
    </>
  );
}
```

## Toast Types

### Success
- Icon: CheckCircle
- Color: Green
- Default duration: 3000ms
- Use for: Successful operations, confirmations

### Error
- Icon: AlertCircle
- Color: Red
- Default duration: 5000ms
- Use for: Failures, errors, validation issues

### Warning
- Icon: AlertTriangle
- Color: Yellow/Amber
- Default duration: 4000ms
- Use for: Warnings, cautions, confirmations needed

### Info
- Icon: Info
- Color: Blue
- Default duration: 3000ms
- Use for: Informational messages, tips, updates

### Loading
- Icon: Loader2 (animated)
- Color: Gray
- Duration: Never (manual close only)
- Use for: Async operations, file uploads

## Styling

The Toast components use Tailwind CSS with support for dark mode. All colors are automatically adjusted for dark theme:

- Success: green-50 (light) / green-950 (dark)
- Error: red-50 (light) / red-950 (dark)
- Warning: yellow-50 (light) / yellow-950 (dark)
- Info: blue-50 (light) / blue-950 (dark)
- Loading: gray-50 (light) / gray-950 (dark)

## Accessibility

All toast components include:
- ARIA live regions for announcements
- Proper semantic roles (`role="alert"`)
- Keyboard-accessible close buttons
- Dynamic aria-live values based on type
- Clear focus management

## Testing

Test files are included for all components:
- `Toast.test.tsx`: Component rendering, auto-dismiss, accessibility
- `ToastContainer.test.tsx`: Multiple toasts, positioning, limits
- `ToastContext.test.tsx`: Hook functionality, provider behavior

Run tests:
```bash
npm test -- Toast
```

## Examples

See `Toast.example.tsx` for comprehensive examples:
- Basic toast usage
- All toast types
- Toast with action buttons
- Toast container with positioning
- Interactive examples

View examples:
```bash
# In your Storybook or demo page
import { ToastExamples } from '@/components/Toast/Toast.example';
```

## Performance

- Efficient rendering with React Context
- Minimal re-renders using useCallback
- Automatic cleanup of timers
- No memory leaks with proper unmounting
- Supports 100+ simultaneous toasts

## Browser Support

- All modern browsers (Chrome, Firefox, Safari, Edge)
- IE11+ with polyfills
- Mobile browsers (iOS Safari, Chrome Mobile)

## Migration from NotificationSystem

If migrating from the old `NotificationSystem` component:

**Before:**
```tsx
import { useNotifications } from '@/components/NotificationSystem';

export function MyComponent() {
  const { showSuccess, showError } = useNotifications();

  return <button onClick={() => showSuccess('Done!')}>Save</button>;
}
```

**After:**
```tsx
import { useToast } from '@/components/Toast';

export function MyComponent() {
  const toast = useToast();

  return <button onClick={() => toast.showSuccess('Done!')}>Save</button>;
}
```

Both systems can coexist. The Toast system is recommended for new code.

## Troubleshooting

### Toast not appearing
1. Check that `ToastProvider` wraps your component
2. Verify `useToast()` is called in a child of `ToastProvider`
3. Check console for errors

### Multiple toasts not showing
1. Check `maxToasts` prop in `ToastProvider`
2. Verify unique IDs for each toast
3. Check CSS z-index conflicts

### Styling issues
1. Ensure Tailwind CSS is configured
2. Check for CSS conflicts with your styles
3. Verify dark mode configuration

## Future Enhancements

Potential improvements:
- Toast animations customization
- Sound notifications
- Desktop notifications integration
- Swipe-to-dismiss on mobile
- Toast queue persistence
- Custom toast components
- Toast stacking algorithms
