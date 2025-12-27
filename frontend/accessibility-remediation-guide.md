# Accessibility Remediation Guide - Phase 1 & 2

**Target**: WCAG 2.1 Level AA Compliance
**Status**: Implementation Guide for Developers
**Created**: December 27, 2025

---

## Quick Start: Top 5 Fixes

### 1. Add Focus Trap to Modals (CRITICAL)

**Before**:
```tsx
export const CreateUserDialog = ({ open, onOpenChange, onSuccess }) => {
  const [step, setStep] = useState<Step>('form');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
        </DialogHeader>
        {/* Form content */}
      </DialogContent>
    </Dialog>
  );
};
```

**After** (Using Radix UI Dialog - already has focus trap!):
```tsx
export const CreateUserDialog = ({ open, onOpenChange, onSuccess }) => {
  const [step, setStep] = useState<Step>('form');
  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open && step === 'form') {
      // Focus first input when dialog opens
      setTimeout(() => firstInputRef?.current?.focus(), 0);
    }
  }, [open, step]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-modal="true"
        role="dialog"
        aria-labelledby="dialog-title"
      >
        <DialogHeader>
          <DialogTitle id="dialog-title">Create User</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {/* First input will receive focus automatically */}
          <Input
            ref={firstInputRef}
            placeholder="Email"
            autoFocus // Radix Dialog will manage focus
          />
          {/* More inputs... */}
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handleSubmit}>Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
```

**Key Points**:
- Radix Dialog already implements focus trap (good!)
- Use `aria-modal="true"` and `role="dialog"`
- Ensure first focusable element gets focus
- ESC key automatically handled by Radix

---

### 2. Add ARIA Labels to Icon Buttons (HIGH)

**Before**:
```tsx
<Button
  variant="ghost"
  size="sm"
  onClick={() => onEdit?.(material)}
  className="opacity-0 group-hover:opacity-100 transition-opacity"
>
  <Edit className="h-4 w-4" />
</Button>

<Button
  variant="ghost"
  size="sm"
  onClick={() => onDelete?.(material)}
  className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600"
>
  <Trash2 className="h-4 w-4" />
</Button>
```

**After**:
```tsx
<Button
  variant="ghost"
  size="sm"
  onClick={() => onEdit?.(material)}
  aria-label={`Edit material: ${material.title}`}
  title="Edit material"
  className="opacity-100 transition-opacity focus:ring-2 focus:ring-offset-2 focus:ring-primary"
>
  <Edit className="h-4 w-4 mr-1" aria-hidden="true" />
  <span className="hidden sm:inline">Edit</span>
</Button>

<Button
  variant="ghost"
  size="sm"
  onClick={() => onDelete?.(material)}
  aria-label={`Delete material: ${material.title}`}
  title="Delete material"
  className="opacity-100 transition-opacity text-red-600 focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
>
  <Trash2 className="h-4 w-4 mr-1" aria-hidden="true" />
  <span className="hidden sm:inline">Delete</span>
</Button>
```

**Key Changes**:
- Add `aria-label` with context (what is being edited/deleted)
- Add `title` attribute for tooltip on hover
- Change `opacity-0` to `opacity-100` (always visible)
- Add `aria-hidden="true"` to decorative icons
- Add visible text label (hide on mobile with `hidden sm:inline`)

---

### 3. Add Form Label Associations (HIGH)

**Before**:
```tsx
export const CreateUserDialog = ({ open, onOpenChange, onSuccess }) => {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
  });

  return (
    <DialogContent>
      <Input
        type="email"
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
      />
      <Input
        type="text"
        placeholder="First Name"
        value={formData.first_name}
        onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
      />
    </DialogContent>
  );
};
```

**After**:
```tsx
export const CreateUserDialog = ({ open, onOpenChange, onSuccess }) => {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  return (
    <DialogContent>
      <div className="space-y-4">
        {/* Email Field */}
        <div className="space-y-2">
          <Label htmlFor="email-input" className="text-sm font-medium">
            Email Address <span className="text-red-600" aria-label="required">*</span>
          </Label>
          <Input
            id="email-input"
            type="email"
            placeholder="example@email.com"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
            aria-required="true"
            aria-describedby={errors.email ? 'email-error' : undefined}
            aria-invalid={Boolean(errors.email)}
          />
          {errors.email && (
            <p id="email-error" className="text-sm text-red-600" role="alert">
              {errors.email}
            </p>
          )}
        </div>

        {/* First Name Field */}
        <div className="space-y-2">
          <Label htmlFor="first-name-input" className="text-sm font-medium">
            First Name <span className="text-red-600" aria-label="required">*</span>
          </Label>
          <Input
            id="first-name-input"
            type="text"
            placeholder="John"
            value={formData.first_name}
            onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
            required
            aria-required="true"
            aria-describedby={errors.first_name ? 'first-name-error' : undefined}
            aria-invalid={Boolean(errors.first_name)}
          />
          {errors.first_name && (
            <p id="first-name-error" className="text-sm text-red-600" role="alert">
              {errors.first_name}
            </p>
          )}
        </div>
      </div>
    </DialogContent>
  );
};
```

**Key Changes**:
- Use `<Label htmlFor="id">` to associate label with input
- Use unique `id` for each input (e.g., `email-input`, `first-name-input`)
- Add `aria-required="true"` for required fields
- Use `aria-describedby` to link error messages
- Use `aria-invalid="true"` for invalid fields
- Error messages have `role="alert"` for announcement

---

### 4. Add Alt Text to Images (CRITICAL)

**Before**:
```tsx
import { LazyImage } from '@/components/LazyImage';

export const ProfileCard = ({ user }) => {
  return (
    <div className="flex gap-4">
      <LazyImage src={user.avatar_url} />
      <div>
        <h3>{user.first_name} {user.last_name}</h3>
        <p>{user.bio}</p>
      </div>
    </div>
  );
};
```

**After**:
```tsx
import { LazyImage } from '@/components/LazyImage';

export const ProfileCard = ({ user }) => {
  return (
    <div className="flex gap-4">
      <LazyImage
        src={user.avatar_url}
        alt={`${user.first_name} ${user.last_name}'s profile picture`}
        className="h-24 w-24 rounded-full object-cover"
      />
      <div>
        <h3>{user.first_name} {user.last_name}</h3>
        <p>{user.bio}</p>
      </div>
    </div>
  );
};
```

**LazyImage.tsx** should be updated:
```tsx
interface LazyImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string; // Make alt required
  fallbackSrc?: string;
}

export const LazyImage = ({
  src,
  alt,
  fallbackSrc,
  ...props
}: LazyImageProps) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(false);

  return (
    <img
      src={error ? fallbackSrc : src}
      alt={alt} // Always required
      loading="lazy"
      onLoad={() => setIsLoaded(true)}
      onError={() => setError(true)}
      {...props}
    />
  );
};
```

**Alt Text Guidelines**:
- Describe the image content
- Be concise but descriptive
- Don't start with "Image of" or "Picture of"
- Include relevant context (e.g., person's name, subject)

---

### 5. Fix Loading Spinner Accessibility (HIGH)

**Before**:
```tsx
export const LoadingSpinner = ({ size = "md", text = "Загрузка..." }) => {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8"
  };

  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <Loader2 className={`${sizeClasses[size]} animate-spin`} />
      {text && <p className="text-sm text-muted-foreground">{text}</p>}
    </div>
  );
};
```

**After**:
```tsx
interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  text?: string;
  ariaLabel?: string;
}

export const LoadingSpinner = ({
  size = "md",
  text = "Загрузка...",
  ariaLabel = "Loading"
}: LoadingSpinnerProps) => {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-8 h-8"
  };

  return (
    <div
      className="flex flex-col items-center justify-center gap-2"
      role="status"
      aria-label={ariaLabel}
      aria-live="polite"
      aria-atomic="true"
    >
      <Loader2
        className={`${sizeClasses[size]} animate-spin`}
        aria-hidden="true"
      />
      {text && (
        <p className="text-sm text-foreground font-medium">
          {text}
        </p>
      )}
    </div>
  );
};
```

**Key Changes**:
- Add `role="status"` to identify it as a status update
- Add `aria-live="polite"` to announce when it appears
- Add `aria-atomic="true"` to announce entire spinner
- Change `text-muted-foreground` to `text-foreground` (better contrast)
- Add `font-medium` for better visibility
- Add `aria-hidden="true"` to icon (decorative)

---

## Accessibility Component Library

### Accessible Button Pattern

```tsx
import React from 'react';
import { Button as BaseButton, ButtonProps as BaseButtonProps } from '@/components/ui/button';

interface AccessibleButtonProps extends BaseButtonProps {
  // For icon-only buttons
  ariaLabel?: string;
  // For buttons with aria-describedby
  ariaDescribedBy?: string;
}

export const AccessibleButton = React.forwardRef<
  HTMLButtonElement,
  AccessibleButtonProps
>(({ ariaLabel, ariaDescribedBy, children, ...props }, ref) => {
  // Warn if icon-only button without label
  if (!children && !ariaLabel && !props.title) {
    console.warn(
      'Button without text content should have aria-label or title attribute'
    );
  }

  return (
    <BaseButton
      ref={ref}
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      {...props}
    >
      {children}
    </BaseButton>
  );
});

AccessibleButton.displayName = 'AccessibleButton';
```

### Accessible Form Field Pattern

```tsx
interface AccessibleInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  helperText?: string;
  required?: boolean;
}

export const AccessibleInput = React.forwardRef<
  HTMLInputElement,
  AccessibleInputProps
>(({ label, error, helperText, required, id, ...props }, ref) => {
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
  const errorId = error ? `${inputId}-error` : undefined;
  const helperId = helperText ? `${inputId}-help` : undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor={inputId} className="text-sm font-medium">
        {label}
        {required && (
          <span className="text-red-600 ml-1" aria-label="required">
            *
          </span>
        )}
      </Label>
      <Input
        ref={ref}
        id={inputId}
        required={required}
        aria-required={required}
        aria-invalid={Boolean(error)}
        aria-describedby={[errorId, helperId].filter(Boolean).join(' ') || undefined}
        {...props}
      />
      {error && (
        <p id={errorId} className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
      {helperText && (
        <p id={helperId} className="text-sm text-muted-foreground">
          {helperText}
        </p>
      )}
    </div>
  );
});

AccessibleInput.displayName = 'AccessibleInput';
```

### Accessible Select Pattern

```tsx
interface AccessibleSelectProps {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
  error?: string;
  required?: boolean;
  placeholder?: string;
}

export const AccessibleSelect = ({
  label,
  value,
  onValueChange,
  options,
  error,
  required,
  placeholder
}: AccessibleSelectProps) => {
  const selectId = `select-${Math.random().toString(36).substr(2, 9)}`;
  const errorId = error ? `${selectId}-error` : undefined;

  return (
    <div className="space-y-2">
      <Label htmlFor={selectId} className="text-sm font-medium">
        {label}
        {required && (
          <span className="text-red-600 ml-1" aria-label="required">
            *
          </span>
        )}
      </Label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger
          id={selectId}
          aria-label={label}
          aria-required={required}
          aria-invalid={Boolean(error)}
          aria-describedby={errorId}
        >
          <SelectValue placeholder={placeholder || 'Select an option'} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {error && (
        <p id={errorId} className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
};
```

---

## Fixing Specific Components

### MaterialCard.tsx Remediation

**Current Issues**:
1. Hover-only buttons not keyboard accessible
2. Icon buttons without labels
3. Difficulty indicator uses only color
4. No proper heading hierarchy

**Remediation Steps**:

```tsx
// 1. Make edit/delete buttons always visible
// Change from:
className="opacity-0 group-hover:opacity-100 transition-opacity"
// To:
className="opacity-100 transition-opacity"

// 2. Add aria-labels to all buttons
<Button
  aria-label={`Edit material: ${material.title}`}
  title="Edit material"
>
  <Edit className="h-4 w-4 mr-1" aria-hidden="true" />
  <span className="hidden sm:inline">Edit</span>
</Button>

// 3. Fix difficulty indicator
const getDifficultyColor = (level: number) => {
  // Add both color and text
  return {
    color: level <= 2 ? 'text-green-700' : level <= 3 ? 'text-yellow-700' : 'text-red-700',
    text: level <= 2 ? 'Easy' : level <= 3 ? 'Medium' : 'Hard'
  };
};

// Use in component:
<div className="flex items-center gap-2">
  <span className="text-sm font-medium" aria-label={`Difficulty: ${getDifficultyColor(material.difficulty_level).text}`}>
    {getDifficultyColor(material.difficulty_level).text}
  </span>
  <div className="flex space-x-1" aria-hidden="true">
    {/* Visual difficulty bars */}
  </div>
</div>

// 4. Fix heading hierarchy
// Change CardTitle to use proper heading level
<h3 className="text-lg leading-tight line-clamp-2">
  {material.title}
</h3>
```

---

### Chat Notification Badge Remediation

**Before**:
```tsx
<Badge
  variant="destructive"
  className={cn(
    'ml-auto h-5 min-w-[20px] flex items-center justify-center text-xs animate-pulse',
    className
  )}
>
  {totalUnread > 99 ? '99+' : totalUnread}
</Badge>
```

**After**:
```tsx
<Badge
  variant="destructive"
  className={cn(
    'ml-auto h-5 min-w-[20px] flex items-center justify-center text-xs animate-pulse',
    className
  )}
  aria-label={`${totalUnread} unread messages`}
  aria-live="polite"
  aria-atomic="true"
  role="status"
>
  {totalUnread > 99 ? '99+' : totalUnread}
</Badge>
```

---

## Testing Accessibility Fixes

### Automated Testing with axe

```tsx
import { axe, toHaveNoViolations } from 'jest-axe';
import { render } from '@testing-library/react';

expect.extend(toHaveNoViolations);

describe('Accessibility', () => {
  it('should not have accessibility violations', async () => {
    const { container } = render(
      <MaterialCard
        material={mockMaterial}
        userRole="student"
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper focus management in modal', async () => {
    const { container } = render(
      <CreateUserDialog open={true} onOpenChange={() => {}} onSuccess={() => {}} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper form labels', async () => {
    const { container } = render(
      <CreateUserDialog open={true} onOpenChange={() => {}} onSuccess={() => {}} />
    );
    const inputs = container.querySelectorAll('input');
    inputs.forEach((input) => {
      expect(input).toHaveAttribute('id');
      expect(container.querySelector(`label[for="${input.id}"]`)).toBeInTheDocument();
    });
  });
});
```

### Manual Keyboard Navigation Test

```
1. Load page
2. Press Tab key repeatedly
3. Verify:
   - Focus indicator visible on all interactive elements
   - Tab order is logical (left-to-right, top-to-bottom)
   - No focus traps (except intentional modal traps)
   - All buttons activate with Enter/Space
   - Forms submit with Enter
4. Press Escape to close dialogs
5. Alt+Tab to focus different elements
```

### Screen Reader Testing Checklist

Using NVDA (Windows) or VoiceOver (Mac):

```
[ ] Page heading is announced
[ ] Form labels announced with inputs
[ ] Error messages announced
[ ] Button purposes clear (not just "button")
[ ] Image alt text announced
[ ] Links have descriptive text
[ ] Lists announced as "list with X items"
[ ] Modals announced as "modal dialog"
[ ] Loading status announced
[ ] Notification updates announced
[ ] Icons have labels or are marked decorative
```

---

## Summary of Changes by Priority

### Priority 1: Today/This Week
- [x] Audit complete and documented
- [ ] Add focus trap to modals (check if Radix Dialog does this)
- [ ] Add aria-labels to icon buttons
- [ ] Add alt text to images
- [ ] Fix form label associations
- [ ] Fix loading spinner accessibility

**Estimated Time**: 8-16 hours (3-5 components per developer)
**Developers Needed**: 2-3

### Priority 2: Next 1-2 Weeks
- [ ] Fix color contrast issues
- [ ] Add heading hierarchy
- [ ] Make hover buttons always visible
- [ ] Test keyboard navigation
- [ ] Test with screen reader
- [ ] Automated accessibility tests

**Estimated Time**: 16-24 hours
**Developers Needed**: 2-3

### Priority 3: Next 2-4 Weeks
- [ ] Add semantic HTML
- [ ] Implement skip links
- [ ] Fix list structures
- [ ] Mobile accessibility
- [ ] Advanced ARIA patterns
- [ ] Continuous testing setup

**Estimated Time**: 24-40 hours
**Developers Needed**: 2-3

---

**Status**: Ready for Implementation
**Next Step**: Assign Priority 1 fixes to developers
