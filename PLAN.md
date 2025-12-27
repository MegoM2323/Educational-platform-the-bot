# T_FE_013 - Unit Test Coverage Implementation Plan

## Status
IN PROGRESS - Phase 1 of 3

## Objective
Achieve 80%+ code coverage across frontend source code (126K+ lines)

## Current State Analysis

### Test Infrastructure
- **Vitest**: Configured with v8 coverage provider
- **React Testing Library**: Installed and ready
- **Test Setup**: Updated for React 19 compatibility
- **Existing Tests**: 113 files, 56K lines
- **Source Code**: 439 files, 126K lines

### Initial Fixes Applied
1. Fixed React 19 DevTools compatibility in `setup.ts`
2. Updated MaterialForm test with QueryClientProvider wrapper
3. Corrected test selectors to match actual component labels
4. Added async/await handling for async component updates

## Test Coverage Gaps by Category

### Components (80+ files untested)
- **Priority 1 (High Impact)**:
  - All layout sidebars (4 files)
  - Dashboard components (15+ files)
  - Knowledge graph components (20+ files)
  - Chat system components (25+ files)

- **Priority 2 (Medium Impact)**:
  - UI primitive components (100+ files)
  - Form components (6 files)
  - Admin panel components (10+ files)

### Utilities (8/11 files have tests)
- **Untested**:
  - `fileDownload.ts`
  - `offlineStorage.ts`
  - `secureStorage.ts`

### Hooks (Many files without dedicated tests)
- Need comprehensive test coverage for all custom hooks
- Focus on state management hooks first

## Three-Phase Implementation Plan

### PHASE 1: Test Infrastructure & Quick Wins (Week 1)
**Goals**: Fix failing tests, establish patterns, achieve 40% coverage

**Subtasks**:
1. ✓ Fix React 19 compatibility in setup.ts
2. ✓ Update MaterialForm test with wrapper
3. Fix remaining form component test errors
4. Create test helper utilities
   - API mock factory
   - Component render wrapper
   - Test data generators
5. Fix 10+ quick-win tests that just need minor adjustments
6. Run full coverage report

**Target Coverage**: 40%

### PHASE 2: Core Coverage (Weeks 2-3)
**Goals**: Test all critical user-facing components, 60% coverage

**Component Testing Priorities**:
1. **Chat System** (5 components)
   - ChatRoom
   - MessageList
   - MessageInput
   - MessageThread
   - ChatNotifications

2. **Knowledge Graph** (8 components)
   - GraphVisualization
   - ElementCard
   - LessonCard
   - UnlockTracker
   - ProgressIndicator
   - ElementForm
   - LessonForm
   - NodeConnector

3. **Dashboards** (12 components)
   - StudentDashboard
   - TeacherDashboard
   - TutorDashboard
   - ParentDashboard
   - AdminDashboard
   - Support components

4. **Layout Components** (4 files)
   - StudentSidebar
   - TeacherSidebar
   - TutorSidebar
   - ParentSidebar

**Hook Testing**:
- useChat - 15 tests
- useAuth - 12 tests
- useAssignments - 10 tests
- useForumChats (improve existing)
- useForumMessages (improve existing)

**Utility Testing**:
- Add tests for: fileDownload, offlineStorage, secureStorage
- Enhance existing validation tests

**Target Coverage**: 60%

### PHASE 3: Final Push & Edge Cases (Week 4)
**Goals**: Reach 80%+ coverage, test error states

**Activities**:
1. Add error state tests for all components
2. Test accessibility features
3. Test responsive behavior
4. Add performance/rendering tests
5. Test edge cases and boundary conditions
6. Generate and review coverage report
7. Identify and document remaining gaps

**Target Coverage**: 80%+

## Test Writing Standards

### Pattern: Component Tests
```tsx
describe('ComponentName', () => {
  const createWrapper = () => {...};

  beforeEach(() => { vi.clearAllMocks(); });

  it('renders correctly', () => {
    render(<Component />, { wrapper: createWrapper() });
    expect(screen.getByText(/text/i)).toBeInTheDocument();
  });

  it('handles user interactions', async () => {
    const user = userEvent.setup();
    render(<Component />, { wrapper: createWrapper() });

    await user.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(screen.getByText(/result/i)).toBeInTheDocument();
    });
  });

  it('handles errors', async () => {
    const mockError = new Error('API failed');
    vi.mocked(api.request).mockRejectedValueOnce(mockError);

    render(<Component />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });
});
```

### Pattern: Hook Tests
```tsx
describe('useCustomHook', () => {
  it('returns correct state', () => {
    const { result } = renderHook(() => useCustomHook(), {
      wrapper: QueryClientProvider
    });

    expect(result.current.state).toBeDefined();
  });

  it('handles async operations', async () => {
    const { result } = renderHook(() => useCustomHook());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });
});
```

### Pattern: Utility Tests
```tsx
describe('utilityFunction', () => {
  it('returns expected output', () => {
    const result = utilityFunction(input);
    expect(result).toBe(expected);
  });

  it('handles edge cases', () => {
    expect(() => utilityFunction(null)).not.toThrow();
  });

  it('validates input', () => {
    expect(() => utilityFunction(invalid)).toThrow();
  });
});
```

## Files Requiring Immediate Attention

### Tests Needing Fixes (Run after Phase 1)
- [ ] src/components/forms/__tests__/MaterialForm.test.tsx (11 failures)
- [ ] Other form tests with async issues

### High-Priority Component Tests to Create
```
frontend/src/components/
├── chat/ (25+ components)
├── knowledge-graph/ (20+ components)
├── dashboard/ (15+ components)
├── admin/ (10+ components)
└── [create __tests__ subdirectories with tests]
```

## Success Metrics

- Coverage Report Shows:
  - **Statements**: 80%+
  - **Branches**: 75%+
  - **Functions**: 80%+
  - **Lines**: 80%+

- All existing tests pass
- New tests follow established patterns
- Error states covered (400, 403, 404, 500)
- User interactions tested (click, type, submit)
- Async operations properly handled

## Dependencies & Blockers

### Required Libraries (Already Installed)
- vitest: v4.0.11
- @testing-library/react: v16.3.0
- @testing-library/user-event: v14.6.1
- @tanstack/react-query: v5.83.0 (need hooks for tests)

### Blockers
- React 19 compatibility issues (FIXED in setup.ts)
- QueryClientProvider required for many components
- Some components may need refactoring for testability

## Next Steps

1. Run coverage report to get baseline
2. Start Phase 1: Fix quick-win tests
3. Create test helper utilities
4. Begin systematic component testing
5. Weekly progress reviews

## Command Reference

```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage

# Run specific test file
npm run test -- src/components/forms/__tests__/MaterialForm.test.tsx

# Run with UI
npm run test:ui
```

---

**Last Updated**: 2025-12-27
**Owner**: @react-frontend-dev
**Phase**: 1 of 3
