# UI Component Library Documentation

Complete documentation for all reusable UI components in the THE_BOT platform.

## Table of Contents

1. [Button](#button)
2. [Badge](#badge)
3. [Card](#card)
4. [Input](#input)
5. [Alert](#alert)
6. [Dialog](#dialog)
7. [Table](#table)
8. [Tabs](#tabs)
9. [Checkbox](#checkbox)
10. [Spinner](#spinner)

---

## Button

A versatile button component with multiple variants and sizes.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `string` | `"default"` | Style variant: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link` |
| `size` | `string` | `"default"` | Button size: `default`, `sm`, `lg`, `icon` |
| `asChild` | `boolean` | `false` | Render as child component using Slot |
| `className` | `string` | - | Additional CSS classes |
| `disabled` | `boolean` | `false` | Disable the button |
| `onClick` | `function` | - | Click handler |

### Variants

**Default**: Primary button with solid background
```tsx
<Button>Click me</Button>
```

**Destructive**: Red button for destructive actions
```tsx
<Button variant="destructive">Delete</Button>
```

**Outline**: Bordered button without fill
```tsx
<Button variant="outline">Cancel</Button>
```

**Secondary**: Secondary action button
```tsx
<Button variant="secondary">Secondary</Button>
```

**Ghost**: Minimal button without border or fill
```tsx
<Button variant="ghost">Ghost</Button>
```

**Link**: Button styled as a link
```tsx
<Button variant="link">Link Button</Button>
```

### Sizes

```tsx
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>
<Button size="icon">I</Button>
```

### Accessibility

- Focus-visible ring for keyboard navigation
- Disabled state prevents interaction
- Proper role semantics

### Usage Example

```tsx
import { Button } from "@/components/ui/button";

export function LoginForm() {
  return (
    <div className="space-y-4">
      <Button variant="default" size="lg">Sign In</Button>
      <Button variant="outline">Sign Up</Button>
      <Button variant="link">Forgot Password?</Button>
    </div>
  );
}
```

---

## Badge

Small inline label component with color variants.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `string` | `"default"` | Badge style: `default`, `secondary`, `destructive`, `outline` |
| `className` | `string` | - | Additional CSS classes |

### Variants

**Default**: Primary badge with solid background
```tsx
<Badge>New</Badge>
```

**Secondary**: Secondary action badge
```tsx
<Badge variant="secondary">Badge</Badge>
```

**Destructive**: Error/warning badge (red)
```tsx
<Badge variant="destructive">Error</Badge>
```

**Outline**: Bordered badge without fill
```tsx
<Badge variant="outline">Info</Badge>
```

### Usage Examples

```tsx
import { Badge } from "@/components/ui/badge";

// Status indicators
<Badge>Active</Badge>
<Badge variant="secondary">Pending</Badge>
<Badge variant="destructive">Inactive</Badge>

// In a list
<div className="flex gap-2 flex-wrap">
  <Badge>React</Badge>
  <Badge>TypeScript</Badge>
  <Badge>Tailwind</Badge>
</div>
```

### Accessibility

- Focus ring support
- Readable color contrast
- Semantic HTML (div with role)

---

## Card

Container component for grouping related content.

### Components

- **Card**: Main container
- **CardHeader**: Header section
- **CardTitle**: Title text
- **CardDescription**: Subtitle text
- **CardContent**: Main content area
- **CardFooter**: Footer section

### Props

All card components accept standard HTML attributes and `className`.

### Structure

```tsx
<Card>
  <CardHeader>
    <CardTitle>Card Title</CardTitle>
    <CardDescription>Card description goes here</CardDescription>
  </CardHeader>
  <CardContent>
    Main content area
  </CardContent>
  <CardFooter>
    Footer section with actions
  </CardFooter>
</Card>
```

### Usage Examples

**User Profile Card**:
```tsx
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

<Card>
  <CardHeader>
    <CardTitle>Profile</CardTitle>
    <CardDescription>John Doe</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Email: john@example.com</p>
    <p>Role: Student</p>
  </CardContent>
</Card>
```

**Statistics Card**:
```tsx
<Card>
  <CardHeader>
    <CardTitle>Total Users</CardTitle>
  </CardHeader>
  <CardContent>
    <p className="text-3xl font-bold">1,234</p>
  </CardContent>
</Card>
```

### Styling

- Rounded corners (`rounded-lg`)
- Subtle shadow (`shadow-sm`)
- Border and card background color
- Vertical spacing between sections

### Accessibility

- Semantic structure (headers, titles, content)
- Good color contrast
- Readable text hierarchy

---

## Input

Text input field with support for multiple input types.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `type` | `string` | `"text"` | Input type: `text`, `email`, `password`, `number`, `date`, `file`, etc. |
| `placeholder` | `string` | - | Placeholder text |
| `disabled` | `boolean` | `false` | Disable the input |
| `readOnly` | `boolean` | `false` | Make input read-only |
| `className` | `string` | - | Additional CSS classes |

### Input Types

**Text Input**:
```tsx
<Input type="text" placeholder="Enter name" />
```

**Email Input**:
```tsx
<Input type="email" placeholder="Enter email" />
```

**Password Input**:
```tsx
<Input type="password" placeholder="Enter password" />
```

**Number Input**:
```tsx
<Input type="number" placeholder="Enter number" min="0" max="100" />
```

**Date Input**:
```tsx
<Input type="date" />
```

**File Input**:
```tsx
<Input type="file" accept=".pdf,.doc" />
```

### Usage Example

```tsx
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

<div className="space-y-2">
  <Label htmlFor="email">Email</Label>
  <Input
    id="email"
    type="email"
    placeholder="you@example.com"
    onChange={(e) => setEmail(e.target.value)}
  />
</div>
```

### States

**Focused**: Visible ring focus indicator
**Disabled**: Reduced opacity, no pointer
**Placeholder**: Muted text color

### Accessibility

- Label association with `htmlFor`
- Focus ring for keyboard navigation
- Proper semantic structure
- Readable text size

---

## Alert

Container for important messages and notifications.

### Components

- **Alert**: Main container with variant support
- **AlertTitle**: Title text
- **AlertDescription**: Description text

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `string` | `"default"` | Alert style: `default`, `destructive` |
| `className` | `string` | - | Additional CSS classes |

### Variants

**Default**: Information alert
```tsx
<Alert>
  <AlertTitle>Heads up!</AlertTitle>
  <AlertDescription>You can add components to your app.</AlertDescription>
</Alert>
```

**Destructive**: Error alert (red)
```tsx
<Alert variant="destructive">
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>Something went wrong.</AlertDescription>
</Alert>
```

### Usage with Icons

```tsx
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>Failed to save changes.</AlertDescription>
</Alert>
```

### Common Patterns

**Success Message**:
```tsx
<Alert>
  <CheckCircle className="h-4 w-4" />
  <AlertTitle>Success</AlertTitle>
  <AlertDescription>Your profile has been updated.</AlertDescription>
</Alert>
```

**Warning Message**:
```tsx
<Alert variant="destructive">
  <AlertTriangle className="h-4 w-4" />
  <AlertTitle>Warning</AlertTitle>
  <AlertDescription>This action cannot be undone.</AlertDescription>
</Alert>
```

### Accessibility

- `role="alert"` for screen readers
- Icon positioning for visual impact
- Clear text contrast
- Semantic structure

---

## Dialog

Modal dialog with overlay for user interactions.

### Components

- **Dialog**: Root component (Radix Dialog.Root)
- **DialogTrigger**: Opens the dialog
- **DialogContent**: Modal content container
- **DialogHeader**: Header section
- **DialogTitle**: Dialog title
- **DialogDescription**: Dialog description
- **DialogFooter**: Footer with actions
- **DialogClose**: Close button

### Props

Dialog accepts all Radix Dialog props.

### Structure

```tsx
<Dialog>
  <DialogTrigger>Open Dialog</DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>
        Dialog description here
      </DialogDescription>
    </DialogHeader>
    <div>Dialog content</div>
    <DialogFooter>
      <Button variant="outline">Cancel</Button>
      <Button>Save</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Usage Examples

**Confirmation Dialog**:
```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button variant="destructive">Delete</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Delete Item</DialogTitle>
      <DialogDescription>
        Are you sure? This action cannot be undone.
      </DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <DialogClose asChild>
        <Button variant="outline">Cancel</Button>
      </DialogClose>
      <Button variant="destructive">Delete</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Form Dialog**:
```tsx
<Dialog open={isOpen} onOpenChange={setIsOpen}>
  <DialogTrigger>Add Item</DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Add New Item</DialogTitle>
    </DialogHeader>
    <Input placeholder="Item name" />
    <DialogFooter>
      <Button onClick={handleAdd}>Add</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

### Features

- Overlay with semi-transparent backdrop
- Keyboard controls (Escape to close)
- Focus trap inside modal
- Smooth animations
- Responsive sizing

### Accessibility

- Proper focus management
- Escape key closes dialog
- ARIA labels
- Screen reader support

---

## Table

Data table component for displaying tabular information.

### Components

- **Table**: Main wrapper
- **TableHeader**: Header section
- **TableBody**: Body section
- **TableFooter**: Footer section
- **TableRow**: Individual row
- **TableHead**: Header cell
- **TableCell**: Data cell
- **TableCaption**: Table caption/description

### Structure

```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Column 1</TableHead>
      <TableHead>Column 2</TableHead>
      <TableHead>Column 3</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    <TableRow>
      <TableCell>Data 1</TableCell>
      <TableCell>Data 2</TableCell>
      <TableCell>Data 3</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Usage Examples

**User List Table**:
```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Name</TableHead>
      <TableHead>Email</TableHead>
      <TableHead>Role</TableHead>
      <TableHead>Status</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {users.map((user) => (
      <TableRow key={user.id}>
        <TableCell>{user.name}</TableCell>
        <TableCell>{user.email}</TableCell>
        <TableCell>{user.role}</TableCell>
        <TableCell>
          <Badge>{user.status}</Badge>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

**Table with Footer**:
```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Item</TableHead>
      <TableHead className="text-right">Price</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {items.map((item) => (
      <TableRow key={item.id}>
        <TableCell>{item.name}</TableCell>
        <TableCell className="text-right">${item.price}</TableCell>
      </TableRow>
    ))}
  </TableBody>
  <TableFooter>
    <TableRow>
      <TableCell>Total</TableCell>
      <TableCell className="text-right">${total}</TableCell>
    </TableRow>
  </TableFooter>
</Table>
```

### Features

- Horizontal scrolling on small screens
- Hover effect on rows
- Selectable rows (with checkbox)
- Proper spacing and alignment

### Accessibility

- Semantic HTML structure
- Header cells use `<th>`
- Data cells use `<td>`
- Caption support

---

## Tabs

Tabbed interface for switching between content sections.

### Components

- **Tabs**: Root component
- **TabsList**: Container for tab buttons
- **TabsTrigger**: Individual tab button
- **TabsContent**: Content panel for each tab

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `defaultValue` | `string` | - | Default active tab value |
| `value` | `string` | - | Controlled active tab |
| `onValueChange` | `function` | - | Callback when tab changes |

### Structure

```tsx
<Tabs defaultValue="tab1">
  <TabsList>
    <TabsTrigger value="tab1">Tab 1</TabsTrigger>
    <TabsTrigger value="tab2">Tab 2</TabsTrigger>
    <TabsTrigger value="tab3">Tab 3</TabsTrigger>
  </TabsList>
  <TabsContent value="tab1">Content 1</TabsContent>
  <TabsContent value="tab2">Content 2</TabsContent>
  <TabsContent value="tab3">Content 3</TabsContent>
</Tabs>
```

### Usage Examples

**Student Dashboard Tabs**:
```tsx
<Tabs defaultValue="progress">
  <TabsList>
    <TabsTrigger value="progress">Progress</TabsTrigger>
    <TabsTrigger value="assignments">Assignments</TabsTrigger>
    <TabsTrigger value="grades">Grades</TabsTrigger>
  </TabsList>
  <TabsContent value="progress">
    <ProgressChart />
  </TabsContent>
  <TabsContent value="assignments">
    <AssignmentsList />
  </TabsContent>
  <TabsContent value="grades">
    <GradesTable />
  </TabsContent>
</Tabs>
```

**Settings Tabs**:
```tsx
<Tabs defaultValue="account">
  <TabsList>
    <TabsTrigger value="account">Account</TabsTrigger>
    <TabsTrigger value="privacy">Privacy</TabsTrigger>
    <TabsTrigger value="notifications">Notifications</TabsTrigger>
  </TabsList>
  <TabsContent value="account">
    <AccountSettings />
  </TabsContent>
  <TabsContent value="privacy">
    <PrivacySettings />
  </TabsContent>
  <TabsContent value="notifications">
    <NotificationSettings />
  </TabsContent>
</Tabs>
```

### Features

- Active tab highlighting
- Keyboard navigation (arrow keys)
- Smooth focus transitions
- Responsive design

### Accessibility

- ARIA roles and attributes
- Keyboard support (arrow keys, Tab)
- Screen reader friendly
- Focus visible

---

## Checkbox

Toggle checkbox for selection input.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `defaultChecked` | `boolean` | `false` | Initial checked state |
| `checked` | `boolean` | - | Controlled checked state |
| `onCheckedChange` | `function` | - | Callback when state changes |
| `disabled` | `boolean` | `false` | Disable the checkbox |
| `id` | `string` | - | HTML id for label association |

### Usage Examples

**Basic Checkbox**:
```tsx
import { Checkbox } from "@/components/ui/checkbox";

<Checkbox id="terms" />
```

**With Label**:
```tsx
<div className="flex items-center space-x-2">
  <Checkbox id="terms" />
  <label htmlFor="terms">I accept the terms</label>
</div>
```

**Checkbox Group**:
```tsx
const options = ["Option 1", "Option 2", "Option 3"];
const [selected, setSelected] = useState<string[]>([]);

<div className="space-y-2">
  {options.map((option) => (
    <div key={option} className="flex items-center space-x-2">
      <Checkbox
        id={option}
        checked={selected.includes(option)}
        onCheckedChange={(checked) => {
          if (checked) {
            setSelected([...selected, option]);
          } else {
            setSelected(selected.filter((s) => s !== option));
          }
        }}
      />
      <label htmlFor={option}>{option}</label>
    </div>
  ))}
</div>
```

**Controlled Checkbox**:
```tsx
const [isChecked, setIsChecked] = useState(false);

<Checkbox
  checked={isChecked}
  onCheckedChange={setIsChecked}
/>
```

### Features

- Visual check mark indicator
- Smooth transitions
- Disabled state support
- Accessibility features

### Accessibility

- Proper id/label association
- Keyboard navigation (Space to toggle)
- ARIA roles
- Screen reader support

---

## Spinner

Loading indicator component.

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `size` | `string` | `"md"` | Spinner size: `sm`, `md`, `lg` |
| `className` | `string` | - | Additional CSS classes |

### Sizes

```tsx
<Spinner size="sm" />  {/* 16x16 */}
<Spinner size="md" />  {/* 32x32 */}
<Spinner size="lg" />  {/* 48x48 */}
```

### Usage Examples

**Basic Spinner**:
```tsx
import { Spinner } from "@/components/ui/spinner";

<Spinner />
```

**Loading State**:
```tsx
{isLoading ? (
  <Spinner />
) : (
  <Content />
)}
```

**With Custom Color**:
```tsx
<Spinner className="text-red-500" />
<Spinner className="text-green-500" />
```

**Overlay Spinner**:
```tsx
{isLoading && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <Spinner size="lg" className="text-white" />
  </div>
)}
```

**Inline Spinner**:
```tsx
<button disabled={isLoading}>
  {isLoading && <Spinner size="sm" className="mr-2" />}
  {isLoading ? "Loading..." : "Submit"}
</button>
```

### Features

- Smooth rotation animation
- Multiple size options
- Color customization
- Lightweight SVG

### Accessibility

- Semantic role (could be improved with aria-label)
- Visual indication of loading state
- Should accompany text like "Loading..."

---

## Best Practices

### 1. Component Composition

Combine components to create complex UI:

```tsx
<Card>
  <CardHeader>
    <CardTitle>User Settings</CardTitle>
  </CardHeader>
  <CardContent className="space-y-4">
    <div>
      <Label>Email</Label>
      <Input type="email" />
    </div>
    <div>
      <Label>Notifications</Label>
      <div className="flex items-center space-x-2">
        <Checkbox id="emails" />
        <label htmlFor="emails">Email notifications</label>
      </div>
    </div>
  </CardContent>
  <CardFooter className="space-x-2">
    <Button variant="outline">Cancel</Button>
    <Button>Save</Button>
  </CardFooter>
</Card>
```

### 2. Responsive Design

All components support Tailwind's responsive modifiers:

```tsx
<Button className="w-full md:w-auto">
  Responsive Button
</Button>
```

### 3. Dark Mode

All components respect the Tailwind dark mode:

```tsx
<Card className="dark:bg-slate-950">
  <CardContent>Dark mode aware</CardContent>
</Card>
```

### 4. Accessibility

Always include proper labels and ARIA attributes:

```tsx
<div className="space-y-2">
  <Label htmlFor="password">Password</Label>
  <Input
    id="password"
    type="password"
    aria-describedby="password-help"
  />
  <p id="password-help">At least 8 characters</p>
</div>
```

### 5. State Management

Use React hooks for component state:

```tsx
const [open, setOpen] = useState(false);

<Dialog open={open} onOpenChange={setOpen}>
  <DialogTrigger onClick={() => setOpen(true)}>Open</DialogTrigger>
</Dialog>
```

---

## Component Variants Summary

| Component | Variants | Sizes | Notes |
|-----------|----------|-------|-------|
| Button | 6 | 4 | Most flexible component |
| Badge | 4 | 1 | Fixed size |
| Card | - | - | Container component |
| Input | 10+ types | - | Form input |
| Alert | 2 | - | Message container |
| Dialog | - | - | Modal overlay |
| Table | - | - | Data display |
| Tabs | - | - | Navigation component |
| Checkbox | - | - | Selection input |
| Spinner | - | 3 | Loading indicator |

---

## Import Examples

```tsx
// Buttons
import { Button } from "@/components/ui/button";

// Data Display
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";

// Containers
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

// Forms
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";

// Navigation
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

// Feedback
import { Spinner } from "@/components/ui/spinner";
```

---

## Testing Components

### Button Testing

```tsx
import { render, screen } from "@testing-library/react";
import { Button } from "@/components/ui/button";

test("renders button with text", () => {
  render(<Button>Click me</Button>);
  expect(screen.getByText("Click me")).toBeInTheDocument();
});

test("handles click events", () => {
  const handleClick = jest.fn();
  render(<Button onClick={handleClick}>Click</Button>);
  screen.getByText("Click").click();
  expect(handleClick).toHaveBeenCalled();
});
```

### Dialog Testing

```tsx
test("opens and closes dialog", () => {
  render(
    <Dialog>
      <DialogTrigger>Open</DialogTrigger>
      <DialogContent>Dialog content</DialogContent>
    </Dialog>
  );
  expect(screen.queryByText("Dialog content")).not.toBeInTheDocument();
  screen.getByText("Open").click();
  expect(screen.getByText("Dialog content")).toBeInTheDocument();
});
```

---

## Styling & Customization

All components use Tailwind CSS and can be customized via `className`:

```tsx
// Custom styles
<Button className="bg-gradient-to-r from-blue-500 to-purple-600">
  Custom Button
</Button>

// Size override
<Input className="h-12 text-lg" />

// Color override
<Badge className="bg-yellow-500 text-black">Custom</Badge>
```

---

## Related Documentation

- [Tailwind CSS Documentation](https://tailwindcss.com)
- [Radix UI Documentation](https://www.radix-ui.com)
- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Last Updated**: December 27, 2025
**Version**: 1.0.0
**Status**: Complete - All core components documented
