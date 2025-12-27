# Storybook Setup Guide (Optional)

This guide explains how to set up Storybook for interactive component documentation and testing.

## What is Storybook?

Storybook is an isolated development environment for UI components. It allows you to:
- View components in isolation
- Test different states and props
- Document component usage
- Create visual regression tests
- Generate interactive documentation

## Installation

### 1. Install Storybook CLI

```bash
npm install --save-dev @storybook/react@latest @storybook/addon-essentials
```

### 2. Initialize Storybook

```bash
npx storybook@latest init --type react
```

This creates:
- `.storybook/` directory with configuration
- `stories/` directory with example stories
- `package.json` scripts for running Storybook

### 3. Configure for TypeScript

The setup should auto-detect TypeScript. Ensure `tsconfig.json` is properly configured.

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── button.tsx
│   │   │   ├── button.stories.tsx  # Story file
│   │   │   ├── badge.tsx
│   │   │   ├── badge.stories.tsx
│   │   │   └── ...
│   ├── lib/
│   └── ...
├── .storybook/
│   ├── main.ts              # Storybook config
│   ├── preview.ts           # Global preview settings
│   └── manager-head.html    # Custom styles
└── stories/
    └── ...
```

## Creating Stories

### Basic Button Story

Create `frontend/src/components/ui/button.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./button";

/**
 * A flexible button component with multiple variants and sizes.
 * Useful for primary actions, secondary actions, and destructive actions.
 */
const meta = {
  title: "Components/Button",
  component: Button,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "destructive", "outline", "secondary", "ghost", "link"],
    },
    size: {
      control: "select",
      options: ["default", "sm", "lg", "icon"],
    },
    disabled: {
      control: "boolean",
    },
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

// Basic button
export const Default: Story = {
  args: {
    children: "Button",
  },
};

// Variant examples
export const Destructive: Story = {
  args: {
    variant: "destructive",
    children: "Delete",
  },
};

export const Outline: Story = {
  args: {
    variant: "outline",
    children: "Outline",
  },
};

export const Secondary: Story = {
  args: {
    variant: "secondary",
    children: "Secondary",
  },
};

export const Ghost: Story = {
  args: {
    variant: "ghost",
    children: "Ghost",
  },
};

export const Link: Story = {
  args: {
    variant: "link",
    children: "Link",
  },
};

// Size examples
export const Small: Story = {
  args: {
    size: "sm",
    children: "Small Button",
  },
};

export const Large: Story = {
  args: {
    size: "lg",
    children: "Large Button",
  },
};

export const Icon: Story = {
  args: {
    size: "icon",
    children: "I",
  },
};

// Disabled state
export const Disabled: Story = {
  args: {
    disabled: true,
    children: "Disabled",
  },
};

// Interactive story
export const Interactive: Story = {
  args: {
    children: "Click me",
  },
  render: (args) => (
    <div className="space-y-4">
      <Button {...args} />
      <Button {...args} variant="outline" />
      <Button {...args} variant="destructive" />
    </div>
  ),
};
```

### Badge Story

Create `frontend/src/components/ui/badge.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Badge } from "./badge";

const meta = {
  title: "Components/Badge",
  component: Badge,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "secondary", "destructive", "outline"],
    },
  },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    children: "Badge",
  },
};

export const Secondary: Story = {
  args: {
    variant: "secondary",
    children: "Secondary",
  },
};

export const Destructive: Story = {
  args: {
    variant: "destructive",
    children: "Error",
  },
};

export const Outline: Story = {
  args: {
    variant: "outline",
    children: "Outline",
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex gap-2 flex-wrap">
      <Badge>Default</Badge>
      <Badge variant="secondary">Secondary</Badge>
      <Badge variant="destructive">Error</Badge>
      <Badge variant="outline">Outline</Badge>
    </div>
  ),
};
```

### Input Story

Create `frontend/src/components/ui/input.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "./input";

const meta = {
  title: "Components/Input",
  component: Input,
  parameters: {
    layout: "centered",
  },
  tags: ["autodocs"],
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Text: Story = {
  args: {
    type: "text",
    placeholder: "Enter text...",
  },
};

export const Email: Story = {
  args: {
    type: "email",
    placeholder: "you@example.com",
  },
};

export const Password: Story = {
  args: {
    type: "password",
    placeholder: "••••••••",
  },
};

export const Number: Story = {
  args: {
    type: "number",
    placeholder: "Enter number",
  },
};

export const Disabled: Story = {
  args: {
    type: "text",
    placeholder: "Disabled input",
    disabled: true,
  },
};

export const WithValue: Story = {
  args: {
    type: "text",
    value: "Default value",
  },
};
```

### Dialog Story

Create `frontend/src/components/ui/dialog.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "./dialog";
import { Button } from "./button";

const meta = {
  title: "Components/Dialog",
  component: Dialog,
  tags: ["autodocs"],
} satisfies Meta<typeof Dialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Dialog>
      <DialogTrigger>Open Dialog</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Dialog Title</DialogTitle>
          <DialogDescription>
            This is a dialog description
          </DialogDescription>
        </DialogHeader>
        <div>Dialog content goes here</div>
        <DialogFooter>
          <Button variant="outline">Cancel</Button>
          <Button>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ),
};

export const ConfirmationDialog: Story = {
  render: () => (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="destructive">Delete</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Item</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this item? This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline">Cancel</Button>
          <Button variant="destructive">Delete</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  ),
};
```

### Card Story

Create `frontend/src/components/ui/card.stories.tsx`:

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "./card";
import { Button } from "./button";

const meta = {
  title: "Components/Card",
  component: Card,
  tags: ["autodocs"],
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Card className="w-96">
      <CardHeader>
        <CardTitle>Card Title</CardTitle>
        <CardDescription>Card description goes here</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Main content area</p>
      </CardContent>
      <CardFooter>
        <Button>Action</Button>
      </CardFooter>
    </Card>
  ),
};

export const SimpleCard: Story = {
  render: () => (
    <Card className="w-96">
      <CardHeader>
        <CardTitle>Simple Card</CardTitle>
      </CardHeader>
      <CardContent>
        This is a simple card without description or footer.
      </CardContent>
    </Card>
  ),
};
```

## Storybook Configuration

### `.storybook/main.ts`

```typescript
import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.{js,jsx,ts,tsx}"],
  addons: [
    "@storybook/addon-essentials",
    "@storybook/addon-a11y",
    "@storybook/addon-interactions",
  ],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  docs: {
    autodocs: "tag",
  },
};

export default config;
```

### `.storybook/preview.ts`

```typescript
import type { Preview } from "@storybook/react";
import "../src/index.css"; // Your Tailwind CSS

const preview: Preview = {
  parameters: {
    layout: "centered",
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    viewport: {
      viewports: {
        mobile: {
          name: "Mobile",
          styles: {
            width: "375px",
            height: "667px",
          },
        },
        tablet: {
          name: "Tablet",
          styles: {
            width: "768px",
            height: "1024px",
          },
        },
      },
    },
  },
};

export default preview;
```

## Running Storybook

### Development Mode

```bash
npm run storybook
```

Opens Storybook at `http://localhost:6006`

### Build Static Site

```bash
npm run build-storybook
```

Creates a static Storybook in `storybook-static/` directory.

## Package.json Scripts

Add to `package.json`:

```json
{
  "scripts": {
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build",
    "storybook:test": "test-storybook"
  }
}
```

## Advanced Features

### 1. Accessibility Testing

Install addon:

```bash
npm install --save-dev @storybook/addon-a11y
```

Add to `.storybook/main.ts`:

```typescript
addons: ["@storybook/addon-a11y"]
```

### 2. Visual Testing

Install addon:

```bash
npm install --save-dev @chromatic-com/storybook
```

### 3. Interaction Testing

Install addon:

```bash
npm install --save-dev @storybook/addon-interactions @storybook/test
```

### 4. Responsive Design Testing

Built-in viewport controls allow testing different screen sizes.

## Best Practices

### 1. One Story Per Variant

```tsx
export const Primary: Story = { /* default variant */ };
export const Secondary: Story = { /* secondary variant */ };
```

### 2. Document Props

```tsx
const meta = {
  argTypes: {
    variant: {
      description: "Button variant",
      control: "select",
    },
  },
};
```

### 3. Meaningful Names

Use clear, descriptive story names:
- Good: `PrimaryButtonLarge`
- Bad: `Button1`

### 4. Test User Interactions

```tsx
export const Interactive: Story = {
  play: async ({ canvasElement }) => {
    const button = canvasElement.querySelector("button");
    await userEvent.click(button);
  },
};
```

### 5. Document Accessibility

```tsx
const meta = {
  parameters: {
    accessibility: {
      config: {
        rules: [
          {
            id: "color-contrast",
            enabled: true,
          },
        ],
      },
    },
  },
};
```

## Deploying Storybook

### GitHub Pages

```bash
npm run build-storybook
# Deploy storybook-static/ to GitHub Pages
```

### Vercel

```bash
npm run build-storybook
```

Connect your repo to Vercel, set build command to `npm run build-storybook`

### AWS S3

```bash
npm run build-storybook
# Upload storybook-static/ to S3
```

## Complete Story Examples

### Full Button Story Template

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { Button } from "./button";

/**
 * Button component description and usage documentation.
 *
 * - **Variants**: default, destructive, outline, secondary, ghost, link
 * - **Sizes**: default, sm, lg, icon
 * - **States**: normal, hover, focus, disabled
 *
 * Use Button for user actions like submitting forms or triggering dialogs.
 */
const meta = {
  title: "Components/Button",
  component: Button,
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component: "A versatile button component for user interactions.",
      },
    },
  },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      description: "Button style variant",
      control: "select",
      options: ["default", "destructive", "outline", "secondary", "ghost", "link"],
    },
    size: {
      description: "Button size",
      control: "select",
      options: ["default", "sm", "lg", "icon"],
    },
    disabled: {
      description: "Disable the button",
      control: "boolean",
    },
    onClick: {
      action: "clicked",
    },
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

// Standard stories
export const Primary: Story = { args: { children: "Button" } };
export const Secondary: Story = { args: { variant: "secondary", children: "Button" } };
export const Destructive: Story = { args: { variant: "destructive", children: "Delete" } };
export const Outline: Story = { args: { variant: "outline", children: "Button" } };
export const Ghost: Story = { args: { variant: "ghost", children: "Button" } };
export const Link: Story = { args: { variant: "link", children: "Button" } };

export const Sizes: Story = {
  render: (args) => (
    <div className="space-x-2">
      <Button {...args} size="sm">Small</Button>
      <Button {...args} size="default">Default</Button>
      <Button {...args} size="lg">Large</Button>
      <Button {...args} size="icon">I</Button>
    </div>
  ),
};

export const States: Story = {
  render: (args) => (
    <div className="space-x-2">
      <Button {...args}>Normal</Button>
      <Button {...args} disabled>Disabled</Button>
    </div>
  ),
};
```

## Troubleshooting

### Storybook not finding components

Ensure `stories` path in `.storybook/main.ts` matches your file structure:

```typescript
stories: ["../src/**/*.stories.{js,jsx,ts,tsx}"]
```

### Tailwind CSS not applied

Import CSS in `.storybook/preview.ts`:

```typescript
import "../src/index.css";
```

### TypeScript errors

Ensure `tsconfig.json` includes:

```json
{
  "include": ["src", ".storybook"]
}
```

### Performance issues

Split stories into smaller files and disable unused addons in `.storybook/main.ts`.

## Additional Resources

- [Storybook Documentation](https://storybook.js.org)
- [React Component Story Format](https://storybook.js.org/docs/react/api/csf)
- [Interaction Testing](https://storybook.js.org/docs/react/writing-tests/interaction-testing)
- [Accessibility Testing](https://storybook.js.org/docs/react/writing-tests/accessibility-testing)

## Next Steps

1. Install Storybook: `npx storybook@latest init`
2. Create `.stories.tsx` files for each component
3. Run: `npm run storybook`
4. Visit: `http://localhost:6006`
5. Explore components in isolation
6. Document edge cases and states
7. Build and deploy static site

---

**Status**: Optional Setup Guide
**Last Updated**: December 27, 2025
**Purpose**: Interactive component documentation and testing
