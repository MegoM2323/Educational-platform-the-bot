# Accessibility Compliance Checklist - T_FE_009

**Quick Reference**: WCAG 2.1 Level AA Compliance
**Status**: Audit Complete - Implementation Ready

---

## Critical Issues (Must Fix)

### Modal & Dialog Components

- [ ] **Focus Trap**: Dialog captures and returns focus (use Radix Dialog)
- [ ] **Escape Key**: ESC closes dialog (Radix handles this)
- [ ] **Announcement**: `aria-modal="true"` on dialog content
- [ ] **Title**: Dialog title linked via `aria-labelledby`
- [ ] **Components to fix**: 8 dialog components in admin/

### Form Elements

- [ ] **Input Labels**: Every input has `<Label htmlFor="id">`
- [ ] **Label-Input Link**: Input has matching `id` attribute
- [ ] **Error Association**: Errors linked via `aria-describedby`
- [ ] **Required Indicator**: Shows "required" in label or input
- [ ] **Invalid State**: Uses `aria-invalid="true"` for errors
- [ ] **Components to fix**: 15+ form components

### Icon Buttons

- [ ] **Aria-Label**: Icon buttons have `aria-label` describing action
- [ ] **Title Attribute**: Buttons have `title` for tooltip
- [ ] **Always Visible**: Not hidden until hover (remove `opacity-0`)
- [ ] **Text Label**: Add text content or visible icon label
- [ ] **Components to fix**: MaterialCard (3 buttons), admin components (10+)

### Images & Media

- [ ] **Alt Text**: All images have descriptive `alt` attribute
- [ ] **Alt Required**: Make `alt` required prop in LazyImage
- [ ] **Meaningful**: Alt describes image content and context
- [ ] **Components to fix**: ProfileCard, ProfileHeader, avatars (20+)

### Loading & Status

- [ ] **Loading Spinner**: Has `role="status"` and `aria-live="polite"`
- [ ] **Status Announcement**: Uses `aria-atomic="true"`
- [ ] **Text**: Clear loading text provided
- [ ] **Icon Hidden**: Spinner icon has `aria-hidden="true"`
- [ ] **Components to fix**: LoadingSpinner, async operations (5)

---

## High Priority Issues (WCAG AA)

### Color Contrast

- [ ] **Text Contrast**: All text ≥ 4.5:1 for normal, ≥ 7:1 for small
- [ ] **Muted Text**: Check `text-muted-foreground` values
- [ ] **Badges**: Status badges meet contrast requirements
- [ ] **Links**: Link colors have sufficient contrast
- [ ] **Disabled**: Disabled elements still readable
- [ ] **Components to fix**: MaterialCard (3 color issues), badges (5+)

### Focus Indicators

- [ ] **Visible Focus**: All interactive elements show focus ring
- [ ] **Contrast**: Focus indicator ≥ 3:1 contrast with surroundings
- [ ] **Consistent**: Same focus style across all elements
- [ ] **Not Removed**: No `outline: none` without replacement
- [ ] **Testing**: Verify with Tab key navigation

### Heading Hierarchy

- [ ] **H1-H6**: Use proper heading levels (not divs with font-size)
- [ ] **Logical Order**: H1 → H2 → H3 (no skipping)
- [ ] **Unique H1**: One H1 per page
- [ ] **Components to fix**: Pages (10+), cards (20+)

### Keyboard Navigation

- [ ] **All Functions**: Everything accessible via keyboard
- [ ] **Tab Order**: Logical order (left-to-right, top-to-bottom)
- [ ] **No Traps**: Tab not trapped outside modals
- [ ] **Enter/Space**: Buttons work with both keys
- [ ] **Testing**: Tab through entire page
- [ ] **Components to fix**: Verify on all interactive elements

### Hover-Only Elements

- [ ] **Always Visible**: Don't hide buttons until hover
- [ ] **Keyboard Access**: Can reach with Tab key
- [ ] **Focus Indicator**: Shows when tabbed to
- [ ] **Components to fix**: MaterialCard (Edit, Delete, Share buttons), admin (10+)

---

## Medium Priority Issues (Best Practices)

### Semantic HTML

- [ ] **Headings**: Use `<h1>-<h6>` not `<div>` with styling
- [ ] **Lists**: Use `<ul>/<ol>/<li>` for lists not `<div>`
- [ ] **Navigation**: Use `<nav>` for navigation regions
- [ ] **Main**: Use `<main>` for primary content
- [ ] **Sections**: Use `<section>` for logical sections
- [ ] **Articles**: Use `<article>` for self-contained content
- [ ] **Components to fix**: Cards (30+), list items (20+), layouts (5)

### ARIA Labels

- [ ] **Descriptions**: Long text descriptions use `aria-describedby`
- [ ] **Labels**: Form fields have labels or `aria-label`
- [ ] **Icons**: Meaningful icons have `aria-label` or alt text
- [ ] **Hidden**: Decorative icons have `aria-hidden="true"`
- [ ] **Live Regions**: Updates announced via `aria-live`
- [ ] **Components to fix**: 30+ components need ARIA improvement

### Links & Buttons

- [ ] **Descriptive Text**: "Click here" → "View material details"
- [ ] **Purpose Clear**: Button/link purpose obvious from text
- [ ] **No Icon-Only**: Text or `aria-label` always present
- [ ] **Differentiated**: Visually distinct from surrounding text
- [ ] **Components to fix**: Material cards (5), navigation (10+)

### Form Improvements

- [ ] **Grouped Inputs**: Related fields in `<fieldset>` with `<legend>`
- [ ] **Placeholders**: Not used as labels (placeholder != label)
- [ ] **Helper Text**: Instructions linked via `aria-describedby`
- [ ] **Validation**: Real-time feedback with `aria-invalid`
- [ ] **Components to fix**: All forms (10+)

### Dynamic Content

- [ ] **Chat Messages**: Announced via `aria-live="polite"`
- [ ] **Notifications**: Toast notifications announced
- [ ] **Updates**: AJAX updates announced to screen readers
- [ ] **Focused**: Focus moved to new content when appropriate
- [ ] **Components to fix**: Chat, notifications, real-time updates (5)

---

## Lower Priority (Nice-to-Have)

### Mobile Accessibility

- [ ] **Touch Targets**: 44x44px minimum (WCAG AAA)
- [ ] **Zoom**: Works at 200% zoom
- [ ] **Text Sizing**: Works with browser text sizing
- [ ] **Orientation**: Works in portrait and landscape
- [ ] **Testing**: Test on mobile devices

### Advanced Patterns

- [ ] **Skip Links**: "Skip to main content" link
- [ ] **Language**: `<html lang="ru">` attribute set
- [ ] **Character Encoding**: `<meta charset="UTF-8">`
- [ ] **Viewport**: Proper viewport meta tag
- [ ] **Page Title**: Unique, descriptive page titles

---

## Testing Verification Checklist

### Automated Testing

- [ ] Jest-axe tests pass
- [ ] Lighthouse score ≥ 90 (Accessibility)
- [ ] No axe violations in critical components
- [ ] CI/CD includes accessibility checks

### Manual Keyboard Testing

- [ ] Tab navigates all interactive elements
- [ ] Tab order is logical
- [ ] Focus indicator visible at all times
- [ ] All buttons/links activate with Enter/Space
- [ ] All forms work with keyboard only
- [ ] Modals can be closed with Escape

### Screen Reader Testing

- [ ] Page title announced
- [ ] Navigation structure clear
- [ ] All form labels announced
- [ ] Error messages announced
- [ ] Button purposes clear
- [ ] Images have alt text
- [ ] Dynamic content announced
- [ ] Lists announced properly
- [ ] Tables announced properly
- [ ] Modals announced as dialogs

### Visual Testing

- [ ] All text ≥ 4.5:1 contrast
- [ ] Focus indicators visible
- [ ] Color not sole information method
- [ ] Works at 200% zoom
- [ ] Works in high contrast mode
- [ ] Works with color blindness filters
- [ ] Buttons/links clearly clickable

---

## Implementation Timeline

### Phase 1: Critical (Week 1-2)
**Effort**: 16-24 hours | **Team**: 2-3 developers

**Tasks**:
1. [ ] Focus trap in modals (Verify Radix handles)
2. [ ] Form label associations (15+ components)
3. [ ] Icon button aria-labels (10+ buttons)
4. [ ] Image alt text (20+ images)
5. [ ] Loading spinner aria-live (5 components)

**Success Criteria**:
- All icon buttons have labels
- All form inputs have labels
- All images have alt text
- Focus works in modals
- Loading states announced

### Phase 2: High Priority (Week 3-4)
**Effort**: 20-32 hours | **Team**: 2-3 developers

**Tasks**:
1. [ ] Fix color contrast (20+ elements)
2. [ ] Add heading hierarchy (30+ elements)
3. [ ] Make hover buttons visible (10+ buttons)
4. [ ] Keyboard navigation testing (entire app)
5. [ ] Setup automated testing (CI/CD)

**Success Criteria**:
- All text ≥ 4.5:1 contrast
- All pages have proper heading structure
- All buttons always keyboard-accessible
- Keyboard navigation fully functional
- Automated tests passing

### Phase 3: Medium Priority (Week 5-8)
**Effort**: 24-40 hours | **Team**: 2-3 developers

**Tasks**:
1. [ ] Add semantic HTML (30+ components)
2. [ ] Implement skip links
3. [ ] Fix list structures (20+ items)
4. [ ] ARIA descriptions (30+ elements)
5. [ ] Mobile accessibility testing

**Success Criteria**:
- Semantic HTML used properly
- Skip links implemented
- ARIA descriptions complete
- Mobile accessibility verified

---

## Component Fix Priority

### Priority 1 (CRITICAL)
```
1. admin/CreateUserDialog.tsx - Form labels + focus trap
2. admin/EditUserDialog.tsx - Form labels + focus trap
3. MaterialCard.tsx - Icon labels + button visibility
4. LoadingSpinner.tsx - aria-live + role
5. forms/ApplicationForm.tsx - Label associations
6. forms/MaterialForm.tsx - Label associations
```

### Priority 2 (HIGH)
```
7. ChatNotificationBadge.tsx - aria-label
8. knowledge-graph/ElementCard.tsx - Icon labels
9. LazyImage.tsx - Alt text enforcement
10. admin/BroadcastModal.tsx - Focus trap
11. invoices/CreateInvoiceForm.tsx - Form labels
12. ProfileCard.tsx - Alt text + contrast
```

### Priority 3 (MEDIUM)
```
13-30. Remaining form components (label associations)
31-50. Other feature components (ARIA improvements)
51-100. UI components (semantic HTML)
101-175. All other components (testing + verification)
```

---

## Useful Tools & Resources

### Command Line Tools
```bash
# Run axe tests
npm run test:a11y

# Lighthouse audit
lighthouse http://localhost:8080 --view

# Pa11y CLI
pa11y http://localhost:8080
```

### Browser Extensions
- axe DevTools (Chrome/Firefox)
- WAVE (Chrome/Firefox)
- Lighthouse (Chrome)
- Spectrum (Chrome) - Color blindness

### Online Tools
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- WCAG Standards: https://www.w3.org/WAI/WCAG21/quickref/
- ARIA Guidelines: https://www.w3.org/WAI/ARIA/apg/

### Screen Readers
- NVDA (Windows): https://www.nvaccess.org/
- VoiceOver (Mac): Built-in, Cmd+F5
- TalkBack (Android): Built-in
- VoiceOver (iOS): Built-in

---

## Success Criteria

**Compliance Level**: WCAG 2.1 Level AA ✓

**When Complete**:
- [ ] All critical issues fixed
- [ ] 0 High priority violations
- [ ] axe automated tests passing
- [ ] Manual keyboard testing passing
- [ ] Screen reader testing passing
- [ ] Color contrast verified
- [ ] Focus indicators visible
- [ ] All forms accessible
- [ ] All buttons accessible
- [ ] All images have alt text

**Certification**:
- [ ] Accessibility audit report generated
- [ ] WCAG 2.1 AA certification achieved
- [ ] Continuous monitoring implemented
- [ ] Team trained on accessibility

---

**Status**: Ready for Phase 1 Implementation
**Start Date**: 2025-12-27
**Target Completion**: 2026-02-15 (8 weeks)
**Responsible**: Frontend Team
**Reviewer**: QA Team

---

## Notes for Developers

1. **Focus on keyboard users**: If you can navigate and use the feature with keyboard only, it's likely accessible
2. **Test with screen reader**: Every component should work with NVDA or VoiceOver
3. **Use semantic HTML**: Proper elements (`<button>`, `<a>`, `<h1>-h6>`) work better than divs
4. **Always associate labels**: Forms must have labels, and labels must be associated with inputs
5. **Contrast matters**: Not just for color-blind users, but also low-vision and in bright sunlight
6. **Test edge cases**: Empty states, error states, loading states, disabled states
7. **Don't hide focus**: Focus indicators are critical, never use `outline: none` without replacement
8. **Use ARIA for custom components**: If you build custom interactive elements, use ARIA to describe them

---

**Document Version**: 1.0
**Last Updated**: 2025-12-27
**Next Review**: After Phase 1 Completion
