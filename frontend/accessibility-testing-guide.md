# Accessibility Testing Guide

**Created**: December 27, 2025
**Status**: Complete Testing Procedures
**Target**: WCAG 2.1 Level AA

---

## Part 1: Automated Testing Setup

### Install Dependencies

```bash
cd frontend

# Automated accessibility testing
npm install --save-dev jest-axe axe-core

# Screen reader simulation
npm install --save-dev @testing-library/dom testing-library-selector

# Keyboard simulation
npm install --save-dev @testing-library/user-event
```

### Setup axe Testing

Create `src/__tests__/setup-a11y.ts`:

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

export { axe, toHaveNoViolations };
```

Update `jest.config.js`:

```javascript
module.exports = {
  // ... existing config
  setupFilesAfterEnv: ['<rootDir>/src/__tests__/setup-a11y.ts'],
  testEnvironment: 'jsdom',
};
```

### Accessibility Test Template

Create test files with pattern: `*.a11y.test.tsx`

```typescript
// Example: src/components/MaterialCard.a11y.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from '@testing-library/react';
import { MaterialCard } from './MaterialCard';

expect.extend(toHaveNoViolations);

describe('MaterialCard - Accessibility', () => {
  const mockMaterial = {
    id: 1,
    title: 'Test Material',
    description: 'Test description',
    type: 'lesson' as const,
    status: 'active' as const,
    subject: { id: 1, name: 'Math', color: '#007bff' },
    author: { id: 1, first_name: 'John', last_name: 'Doe' },
    difficulty_level: 2,
    tags: ['test'],
    created_at: new Date().toISOString(),
  };

  describe('WCAG Compliance', () => {
    it('should not have accessibility violations', async () => {
      const { container } = render(
        <MaterialCard material={mockMaterial} userRole="student" />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have proper heading hierarchy', () => {
      render(<MaterialCard material={mockMaterial} userRole="student" />);

      // Verify heading exists and is proper level
      const heading = screen.getByRole('heading', { name: mockMaterial.title });
      expect(heading).toBeInTheDocument();
    });

    it('should have alt text on all images', () => {
      render(<MaterialCard material={mockMaterial} userRole="student" />);

      const images = screen.getAllByRole('img');
      images.forEach((img) => {
        expect(img).toHaveAttribute('alt');
        expect(img).toHaveAccessibleName();
      });
    });

    it('should have proper form labels', () => {
      render(<MaterialCard material={mockMaterial} userRole="student" />);

      const inputs = screen.queryAllByRole('textbox');
      inputs.forEach((input) => {
        expect(input).toHaveAccessibleName();
      });
    });

    it('should have visible focus indicators on buttons', async () => {
      const user = userEvent.setup();
      const onView = jest.fn();

      render(
        <MaterialCard
          material={mockMaterial}
          userRole="student"
          onView={onView}
        />
      );

      const viewButton = screen.getByRole('button', { name: /view/i });

      // Tab to button
      await user.tab();

      // Verify focus is visible (browser will handle this)
      expect(viewButton).toHaveFocus();
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      const onView = jest.fn();

      render(
        <MaterialCard
          material={mockMaterial}
          userRole="student"
          onView={onView}
        />
      );

      const viewButton = screen.getByRole('button', { name: /view/i });

      // Tab to button
      await user.tab();
      expect(viewButton).toHaveFocus();

      // Activate with Enter
      await user.keyboard('{Enter}');
      expect(onView).toHaveBeenCalled();
    });
  });

  describe('Icon Buttons', () => {
    it('should have aria-label on icon buttons', async () => {
      const onEdit = jest.fn();
      const onDelete = jest.fn();

      render(
        <MaterialCard
          material={mockMaterial}
          userRole="teacher"
          onEdit={onEdit}
          onDelete={onDelete}
        />
      );

      const editButton = screen.getByRole('button', { name: /edit/i });
      const deleteButton = screen.getByRole('button', { name: /delete/i });

      expect(editButton).toHaveAccessibleName();
      expect(deleteButton).toHaveAccessibleName();
    });
  });

  describe('Loading State', () => {
    it('should announce loading state to screen readers', async () => {
      const { rerender } = render(
        <MaterialCard material={mockMaterial} userRole="student" />
      );

      // Check for aria-busy or role="status" during loading
      // This would be in the button component
    });
  });

  describe('Color Contrast', () => {
    it('should have sufficient color contrast', async () => {
      const { container } = render(
        <MaterialCard material={mockMaterial} userRole="student" />
      );

      // Run contrast checking
      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });

      expect(results).toHaveNoViolations();
    });
  });
});
```

---

## Part 2: Manual Testing Procedures

### Test 1: Keyboard Navigation

**Objective**: Verify all functionality is accessible via keyboard

**Procedure**:

```
1. Load the application
2. Press Tab repeatedly and verify:
   - Focus moves through all interactive elements
   - Focus order is logical (left-to-right, top-to-bottom)
   - Focus indicator is always visible
   - No elements are skipped

3. Test keyboard activation:
   - Links and buttons: Enter or Space
   - Checkboxes: Space
   - Radio buttons: Arrow keys + Space
   - Dropdowns: Arrow keys + Enter
   - Modals: Escape to close

4. Tab to each component and test:
   - Material card buttons (View, Download, Edit, Delete)
   - Form inputs (Email, Name, etc.)
   - Dropdown selects
   - Checkboxes and radio buttons
   - Modal dialogs

5. Expected Results:
   - All interactive elements reachable by Tab
   - No focus traps (except intentional modals)
   - All functions available via keyboard
```

**Test Cases**:

| Element | Key | Expected Behavior |
|---------|-----|-------------------|
| Button | Enter/Space | Activates action |
| Link | Enter | Navigates to href |
| Input | Tab | Receives focus, can type |
| Select | Arrow Keys | Changes option |
| Select | Enter | Opens dropdown |
| Checkbox | Space | Toggles checked state |
| Modal | Escape | Closes modal |
| Modal | Tab | Cycles through modal elements |

**Checklist**:
- [ ] Can reach all buttons with Tab key
- [ ] Can activate buttons with Enter/Space
- [ ] Can navigate forms with Tab key
- [ ] Tab order is logical
- [ ] Focus indicator is visible
- [ ] No focus traps outside modals
- [ ] Can close modals with Escape
- [ ] Can submit forms with Enter

---

### Test 2: Screen Reader Testing

**Tools**:
- Windows: NVDA (Free) - https://www.nvaccess.org/
- Mac: VoiceOver (Built-in) - Cmd+F5
- Mobile: TalkBack (Android), VoiceOver (iOS)

**NVDA Quick Start** (Windows):

```bash
# Download: https://www.nvaccess.org/download/
# Install and run

# Key shortcuts:
# Num Lock + F7 = Open Elements List
# Insert + H = Next Heading
# Insert + F = Form Fields
# Insert + B = Buttons
# Ctrl + Alt + N = Read entire page
```

**Test Procedure**:

```
1. Start screen reader
2. Load page and verify:
   - Page title announced
   - All headings announced with proper level
   - Navigation structure clear

3. Test form announcements:
   - Tab to each input
   - Verify label announced
   - Verify input type announced (text, password, etc.)
   - Verify error messages announced
   - Verify required indicator announced

4. Test link and button announcements:
   - Verify button purpose is clear
   - Verify link destination is clear
   - Test icon-only buttons have labels

5. Test dynamic content:
   - Update notification - is it announced?
   - Chat message - is it announced?
   - Loading spinner - is it announced?

6. Expected Results:
   - All content announced clearly
   - Labels associated with inputs
   - Errors immediately announced
   - Dynamic content announced via aria-live
```

**Screen Reader Checklist**:
- [ ] Page title announced on load
- [ ] Headings announced with correct level (h1, h2, h3)
- [ ] Navigation landmarks identified
- [ ] Form labels announced with inputs
- [ ] Error messages announced with role="alert"
- [ ] Buttons have descriptive labels
- [ ] Icons have alt text or aria-label
- [ ] Lists announced as "list with X items"
- [ ] Table structure announced properly
- [ ] Updates announced via aria-live regions
- [ ] Modals announced as dialogs
- [ ] Modal content is contained (focus trap)

---

### Test 3: Color Contrast Testing

**Tools**:
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Axe Color Contrast: https://www.deque.com/axe/devtools/
- Chrome DevTools Lighthouse

**Procedure**:

```
1. Open WebAIM Contrast Checker
2. For each text element, check:
   - Foreground color (text color)
   - Background color
   - Calculate contrast ratio

3. Compare against WCAG standards:
   - Large text (18pt+): 3:1 (AA), 7:1 (AAA)
   - Normal text (<18pt): 4.5:1 (AA), 7:1 (AAA)
   - Graphical elements: 3:1 (AA)

4. Elements to check:
   - Muted text (text-muted-foreground)
   - Status badges
   - Links
   - Buttons
   - Form validation messages
   - Placeholder text
   - Disabled elements

5. Expected Results:
   - All text ≥ 4.5:1 contrast
   - All badges ≥ 4.5:1 contrast
   - All graphics ≥ 3:1 contrast
```

**Sample Test Cases**:

| Element | Foreground | Background | Ratio | WCAG AA | Status |
|---------|-----------|-----------|-------|---------|--------|
| Normal text | #333 | #fff | 12.63:1 | ✓ | Pass |
| Muted text | #999 | #fff | 5.47:1 | ✓ | Pass |
| Muted text | #aaa | #fff | 4.48:1 | ✓ | Pass |
| Disabled text | #bbb | #fff | 3.96:1 | ✗ | Fail |

**Contrast Checklist**:
- [ ] Body text ≥ 4.5:1
- [ ] Heading text ≥ 4.5:1
- [ ] Button text ≥ 4.5:1
- [ ] Link text ≥ 4.5:1
- [ ] Label text ≥ 4.5:1
- [ ] Error text ≥ 4.5:1
- [ ] Placeholder text ≥ 4.5:1
- [ ] Muted/secondary text ≥ 4.5:1
- [ ] Icons ≥ 3:1
- [ ] Focus indicator ≥ 3:1

---

### Test 4: Zoom and Text Scaling

**Objective**: Content remains readable at larger sizes

**Procedure**:

```
1. Open application
2. Zoom to 200% (Ctrl/Cmd + scroll or Ctrl/Cmd +)
3. Verify:
   - No horizontal scrolling required
   - All content readable
   - Buttons/links still clickable
   - Layout doesn't break

4. Test browser text sizing:
   - Right-click → Settings
   - Set text size to 150%, 200%
   - Verify same criteria as above

5. Test mobile zoom:
   - On mobile device, pinch to zoom
   - Verify all content accessible
   - No fixed-width elements blocking view
```

**Checklist**:
- [ ] Content readable at 200% zoom
- [ ] No horizontal scrolling at 200% zoom
- [ ] Buttons/links still accessible at 200% zoom
- [ ] Form inputs functional at 200% zoom
- [ ] Text enlargement works properly
- [ ] Mobile zoom works properly

---

### Test 5: High Contrast Mode

**Windows High Contrast** (Windows only):

```
1. Enable High Contrast Mode:
   - Settings → Ease of Access → High Contrast
   - Select a high contrast theme

2. Test application:
   - Are focus indicators still visible?
   - Are important elements still distinguishable?
   - Do text colors have sufficient contrast?
   - Are subtle borders/separators visible?

3. Expected Results:
   - All interactive elements clearly visible
   - Focus indicator obvious in high contrast
   - Content doesn't rely solely on colors
```

---

### Test 6: Color Blindness Simulation

**Tools**:
- Stark (Figma plugin)
- Color Blindness Simulator
- Chrome extension: Spectrum

**Procedure**:

```
1. Use color blindness simulator
2. View application in different color blindness modes:
   - Deuteranopia (red-green, common)
   - Protanopia (red-green, common)
   - Tritanopia (blue-yellow, rare)
   - Achromatopsia (monochrome, very rare)

3. Verify:
   - Information conveyed by color also conveyed by another method
   - Status indicators not just colors
   - Links not distinguished only by color
   - Charts have patterns, not just colors

4. Expected Results:
   - All information still understandable
   - No information lost in color-blind view
```

---

## Part 3: Automated Testing with CI/CD

### GitHub Actions Workflow

Create `.github/workflows/accessibility.yml`:

```yaml
name: Accessibility Tests

on: [push, pull_request]

jobs:
  accessibility:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run accessibility tests
        working-directory: frontend
        run: npm run test:a11y

      - name: Run axe automation tests
        working-directory: frontend
        run: npm run test:axe

      - name: Generate accessibility report
        working-directory: frontend
        if: always()
        run: npm run test:a11y -- --coverage

      - name: Upload coverage
        uses: actions/upload-artifact@v2
        if: always()
        with:
          name: accessibility-report
          path: frontend/coverage/a11y/
```

### Add Test Scripts to package.json

```json
{
  "scripts": {
    "test:a11y": "jest --testPathPattern='\\.a11y\\.test\\.tsx$' --coverage",
    "test:axe": "jest --testPathPattern='\\.a11y\\.test\\.tsx$' --maxWorkers=1",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  }
}
```

---

## Part 4: Reporting Issues

### Issue Template: Accessibility Violation

When documenting issues, use this format:

```markdown
## [WCAG] Component Name - Issue Title

**Severity**: Critical/High/Medium/Low
**WCAG Criterion**: 1.4.3 Contrast (Minimum) (Level AA)
**Affected Component**:
**Affected Users**: Users with color blindness, low vision, etc.

### Problem Description
Clear description of the accessibility issue.

### Steps to Reproduce
1. Open the component
2. Use screen reader or keyboard
3. Observe the issue

### Expected Behavior
What should happen according to WCAG guidelines.

### Actual Behavior
What actually happens.

### Possible Solutions
Suggested fixes or references to WCAG documentation.

### Test Case
```tsx
// Code demonstrating the issue
```
```

---

## Part 5: Continuous Monitoring

### Weekly Accessibility Checklist

```markdown
## Weekly Accessibility Review

- [ ] Run automated accessibility tests
- [ ] Review accessibility issues from last week
- [ ] Test keyboard navigation on updated pages
- [ ] Test with screen reader on new components
- [ ] Check color contrast of new elements
- [ ] Review pull requests for accessibility
- [ ] Document any new accessibility patterns
- [ ] Update accessibility documentation
```

### Monthly Accessibility Audit

```markdown
## Monthly Full Audit

- [ ] Run full axe scan
- [ ] Manual keyboard navigation test
- [ ] Screen reader testing session (2+ hours)
- [ ] Color contrast audit
- [ ] Zoom/text sizing test
- [ ] High contrast mode test
- [ ] Color blindness simulation test
- [ ] Performance check (impacts accessibility)
- [ ] Browser compatibility check
- [ ] Mobile accessibility test
- [ ] Generate report
- [ ] Update documentation
- [ ] Plan next month's fixes
```

---

## Part 6: Tools and Resources

### Automated Testing Tools
- axe-core: Automated accessibility testing
- WAVE: Visual accessibility feedback
- Lighthouse: Built-in Chrome DevTools
- Pa11y: Command-line accessibility testing

### Screen Readers
- NVDA: Windows (free)
- JAWS: Windows (commercial)
- VoiceOver: macOS/iOS (free, built-in)
- TalkBack: Android (free, built-in)

### Color Checking
- WebAIM Contrast Checker
- Stark (Figma)
- Spectrum Chrome extension
- Color Blindness Simulator

### Learning Resources
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)
- [A11y Project](https://www.a11yproject.com/)
- [Inclusive Components](https://inclusive-components.design/)

---

## Summary

**Testing Frequency**:
- Automated tests: On every commit
- Manual tests: Weekly
- Full audit: Monthly

**Responsible Parties**:
- Developers: Automated tests + keyboard navigation
- QA Team: Manual testing + screen reader
- Product: Prioritize fixes

**Success Criteria**:
- 100% axe test pass rate
- Full keyboard navigation working
- Screen reader announces all content clearly
- All text ≥ 4.5:1 contrast
- WCAG 2.1 Level AA compliant

---

**Status**: Ready for Implementation
**Next Step**: Set up automated testing and run baseline audit
