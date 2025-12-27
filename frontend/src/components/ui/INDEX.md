# UI Component Library Index

Quick reference guide for all available UI components.

## Components by Category

### Action Components

#### Button
- **File**: `button.tsx`
- **Variants**: 6 (default, destructive, outline, secondary, ghost, link)
- **Sizes**: 4 (default, sm, lg, icon)
- **Usage**: Primary interactive element for user actions
- **Key Props**: `variant`, `size`, `disabled`, `onClick`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#button)

### Display Components

#### Badge
- **File**: `badge.tsx`
- **Variants**: 4 (default, secondary, destructive, outline)
- **Usage**: Status indicators and labels
- **Key Props**: `variant`, `className`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#badge)

#### Card
- **File**: `card.tsx`
- **Sub-components**: CardHeader, CardTitle, CardDescription, CardContent, CardFooter
- **Usage**: Content containers and grouping
- **Key Props**: `className`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#card)

#### Alert
- **File**: `alert.tsx`
- **Sub-components**: AlertTitle, AlertDescription
- **Variants**: 2 (default, destructive)
- **Usage**: Important messages and notifications
- **Key Props**: `variant`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#alert)

#### Spinner
- **File**: `spinner.tsx`
- **Sizes**: 3 (sm, md, lg)
- **Usage**: Loading indicators
- **Key Props**: `size`, `className`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#spinner)

### Data Components

#### Table
- **File**: `table.tsx`
- **Sub-components**: TableHeader, TableBody, TableFooter, TableRow, TableHead, TableCell, TableCaption
- **Usage**: Tabular data display
- **Features**: Scrollable, hoverable rows, proper semantics
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#table)

### Form Components

#### Input
- **File**: `input.tsx`
- **Types**: text, email, password, number, date, file, etc.
- **Usage**: Text input fields
- **Key Props**: `type`, `placeholder`, `disabled`, `onChange`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#input)

#### Checkbox
- **File**: `checkbox.tsx`
- **Usage**: Selection inputs and toggles
- **Key Props**: `checked`, `onCheckedChange`, `disabled`, `id`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#checkbox)

### Modal Components

#### Dialog
- **File**: `dialog.tsx`
- **Sub-components**: DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogClose
- **Usage**: Modal dialogs and overlays
- **Features**: Focus trap, keyboard controls, animations
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#dialog)

### Navigation Components

#### Tabs
- **File**: `tabs.tsx`
- **Sub-components**: TabsList, TabsTrigger, TabsContent
- **Usage**: Tabbed content switching
- **Key Props**: `defaultValue`, `value`, `onValueChange`
- **Documentation**: [Full Guide](./COMPONENT_LIBRARY.md#tabs)

---

## Quick Import Guide

```tsx
// Buttons & Actions
import { Button } from "@/components/ui/button";

// Data Display
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableRow,
  TableHead,
  TableCell,
  TableCaption
} from "@/components/ui/table";

// Containers
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter
} from "@/components/ui/card";
import {
  Alert,
  AlertTitle,
  AlertDescription
} from "@/components/ui/alert";

// Modals
import {
  Dialog,
  DialogTrigger,
  DialogPortal,
  DialogOverlay,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription
} from "@/components/ui/dialog";

// Forms
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";

// Navigation
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent
} from "@/components/ui/tabs";

// Feedback
import { Spinner } from "@/components/ui/spinner";
```

---

## Component Props Quick Reference

### Button Props
```tsx
interface ButtonProps {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
  asChild?: boolean;
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
}
```

### Badge Props
```tsx
interface BadgeProps {
  variant?: "default" | "secondary" | "destructive" | "outline";
  className?: string;
}
```

### Input Props
```tsx
type InputProps = React.ComponentProps<"input"> & {
  className?: string;
  type?: string;
  placeholder?: string;
  disabled?: boolean;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}
```

### Checkbox Props
```tsx
interface CheckboxProps {
  defaultChecked?: boolean;
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  className?: string;
}
```

### Dialog Props
```tsx
interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  defaultOpen?: boolean;
}
```

### Tabs Props
```tsx
interface TabsProps {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
}
```

### Spinner Props
```tsx
interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}
```

### Alert Props
```tsx
interface AlertProps {
  variant?: "default" | "destructive";
  className?: string;
}
```

---

## Common Usage Patterns

### Form with Multiple Inputs
```tsx
<Card>
  <CardHeader>
    <CardTitle>Login Form</CardTitle>
  </CardHeader>
  <CardContent className="space-y-4">
    <div>
      <Label htmlFor="email">Email</Label>
      <Input
        id="email"
        type="email"
        placeholder="you@example.com"
      />
    </div>
    <div>
      <Label htmlFor="password">Password</Label>
      <Input
        id="password"
        type="password"
        placeholder="••••••••"
      />
    </div>
    <div className="flex items-center space-x-2">
      <Checkbox id="remember" />
      <Label htmlFor="remember">Remember me</Label>
    </div>
  </CardContent>
  <CardFooter>
    <Button className="w-full">Sign In</Button>
  </CardFooter>
</Card>
```

### Data Table
```tsx
<Card>
  <CardHeader>
    <CardTitle>Users</CardTitle>
  </CardHeader>
  <CardContent>
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Email</TableHead>
          <TableHead>Role</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.map((user) => (
          <TableRow key={user.id}>
            <TableCell>{user.name}</TableCell>
            <TableCell>{user.email}</TableCell>
            <TableCell>
              <Badge>{user.role}</Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </CardContent>
</Card>
```

### Modal Dialog
```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button>Open Dialog</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Confirm Action</DialogTitle>
      <DialogDescription>
        Are you sure you want to proceed?
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <DialogClose asChild>
        <Button variant="outline">Cancel</Button>
      </DialogClose>
      <Button>Confirm</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Tabbed Content
```tsx
<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="analytics">Analytics</TabsTrigger>
    <TabsTrigger value="settings">Settings</TabsTrigger>
  </TabsList>
  <TabsContent value="overview">
    <Card>
      <CardContent>Overview content</CardContent>
    </Card>
  </TabsContent>
  <TabsContent value="analytics">
    <Card>
      <CardContent>Analytics content</CardContent>
    </Card>
  </TabsContent>
  <TabsContent value="settings">
    <Card>
      <CardContent>Settings content</CardContent>
    </Card>
  </TabsContent>
</Tabs>
```

### Loading State
```tsx
{isLoading ? (
  <div className="flex items-center justify-center p-8">
    <Spinner size="lg" />
    <span className="ml-2">Loading...</span>
  </div>
) : (
  <DataContent />
)}
```

### Error Alert
```tsx
{error && (
  <Alert variant="destructive">
    <AlertTriangle className="h-4 w-4" />
    <AlertTitle>Error</AlertTitle>
    <AlertDescription>{error.message}</AlertDescription>
  </Alert>
)}
```

---

## Accessibility Features

All components include built-in accessibility:

- **Semantic HTML**: Proper use of headings, buttons, inputs
- **Focus Management**: Visible focus rings and keyboard navigation
- **ARIA Labels**: Screen reader support
- **Color Contrast**: Accessible color combinations
- **Keyboard Support**: Full keyboard navigation capability
- **Responsive**: Works on all device sizes

---

## Theming

### Dark Mode
All components support Tailwind dark mode:

```tsx
<Button className="dark:bg-slate-800">Themed Button</Button>
```

### Custom Colors
Override default colors with Tailwind classes:

```tsx
<Button className="bg-custom-blue text-custom-white">
  Custom Colored Button
</Button>
```

### Size Customization
Adjust component sizes with Tailwind utilities:

```tsx
<Card className="w-96 sm:w-full">
  Responsive Card
</Card>
```

---

## File Structure

```
frontend/src/components/ui/
├── button.tsx              # Button component
├── badge.tsx               # Badge component
├── card.tsx                # Card and sub-components
├── input.tsx               # Input component
├── alert.tsx               # Alert and sub-components
├── dialog.tsx              # Dialog and sub-components
├── table.tsx               # Table and sub-components
├── tabs.tsx                # Tabs and sub-components
├── checkbox.tsx            # Checkbox component
├── spinner.tsx             # Spinner component
├── COMPONENT_LIBRARY.md    # Full documentation
└── INDEX.md                # This file
```

---

## Performance Considerations

1. **Button**: Lightweight, minimal dependencies
2. **Badge**: Pure CSS styling, no JS overhead
3. **Card**: Layout only, no state management
4. **Input**: Native HTML input, minimal overhead
5. **Alert**: Static component, no animations
6. **Dialog**: Uses Radix primitives for accessibility
7. **Table**: Simple semantic HTML structure
8. **Tabs**: Efficient state management with Radix
9. **Checkbox**: Optimized Radix component
10. **Spinner**: SVG-based animation

---

## Browser Support

All components support:
- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)

---

## Related Libraries

- **Radix UI**: Low-level primitives used for Dialog, Tabs, Checkbox
- **Class Variance Authority (CVA)**: Variant management for Button, Badge
- **Tailwind CSS**: All styling
- **Lucide React**: Icon library integration

---

## Tips & Tricks

### Combining Components
```tsx
// Button in Card footer
<Card>
  <CardContent>Content</CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>
```

### Dynamic Variants
```tsx
const variantMap = {
  success: "default",
  error: "destructive",
  warning: "outline"
};

<Button variant={variantMap[status]}>
  {label}
</Button>
```

### Disabled States
```tsx
<Button disabled={!isFormValid}>
  Submit
</Button>

<Input disabled={isLoading} />
```

### Conditional Rendering
```tsx
{showDialog && (
  <Dialog open={showDialog} onOpenChange={setShowDialog}>
    {/* ... */}
  </Dialog>
)}
```

---

## Troubleshooting

### Button not responding to clicks
- Check if `disabled` prop is true
- Verify `onClick` handler is passed correctly

### Dialog not appearing
- Ensure `DialogContent` is inside `Dialog`
- Check if parent has `position: relative` that might cause issues

### Table text overlapping
- Add more padding with `p-4` in TableCell
- Ensure column widths with `w-1/2` or similar

### Spinner animation not playing
- Check if CSS animations are enabled
- Verify no conflicting CSS in parent

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Dec 27, 2025 | Initial complete documentation |

---

## Contributing

When adding new components:

1. Follow existing naming conventions
2. Add JSDoc comments to code
3. Include usage examples
4. Document all props
5. Test accessibility
6. Update this INDEX file

---

**Last Updated**: December 27, 2025
**Status**: Complete
**Maintained By**: Frontend Team

For detailed documentation, see [COMPONENT_LIBRARY.md](./COMPONENT_LIBRARY.md)
