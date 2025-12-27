# Frontend Dependencies Audit Report
Generated: 2025-12-27

## Summary
- Total dependencies: 59 production + 25 dev
- Vulnerabilities: 2 moderate (esbuild/vite)
- Outdated packages: 20 with updates available
- Duplicate packages: None detected
- Unused packages: 4 potential candidates

## Vulnerabilities Found

### 1. esbuild (MODERATE - CVSS 5.3)
- **Issue**: esbuild enables any website to send requests to dev server and read response
- **CVE**: GHSA-67mh-4wv8-2f99 (CWE-346: Origin Validation Error)
- **Affected Range**: <=0.24.2
- **Direct Dependency**: vite 5.4.21
- **Fix Available**: vite 7.3.0 (breaking change - major version bump)
- **Current Status**: vite depends on vulnerable esbuild version
- **Resolution**: Upgrade vite to 7.x (requires testing)

### 2. vite (MODERATE)
- **Issue**: Depends on vulnerable esbuild <=0.24.2
- **Current**: 5.4.21
- **Latest**: 7.3.0
- **Risk**: Development server can be exploited in open networks
- **Breaking Changes**: Major version bump requires code review

## Outdated Packages (20 packages)

### Critical Updates (should update)
1. **vite**: 5.4.21 → 7.3.0 (fixes security)
2. **react**: 18.3.1 → 19.2.3 (major version)
3. **react-dom**: 18.3.1 → 19.2.3 (major version)
4. **react-router-dom**: 6.30.2 → 7.11.0 (major version)
5. **react-day-picker**: 8.10.1 → 9.13.0 (major version)
6. **recharts**: 2.15.4 → 3.6.0 (major version)
7. **tailwindcss**: 3.4.19 → 4.1.18 (major version)
8. **zod**: 3.25.76 → 4.2.1 (major version)

### Minor Updates (low priority)
9. **date-fns**: 3.6.0 → 4.1.0
10. **sonner**: 1.7.4 → 2.0.7
11. **lucide-react**: 0.462.0 → 0.562.0
12. **@hookform/resolvers**: 3.10.0 → 5.2.2
13. **@vitejs/plugin-react-swc**: 3.11.0 → 4.2.2
14. **react-resizable-panels**: 2.1.9 → 4.0.15
15. **tailwind-merge**: 2.6.0 → 3.4.0
16. **vaul**: 0.9.9 → 1.1.2
17. **next-themes**: 0.3.0 → 0.4.6
18. **@types packages**: Various updates (non-breaking)
19. **eslint-plugin-react-hooks**: 5.2.0 → 7.0.1
20. **globals**: 15.15.0 → 16.5.0

## Potential Unused Dependencies

### High Confidence - Likely Unused
1. **crypto-js** - Not found in codebase imports
2. **d3** - Imported but may be unused (graph visualization?)

### Moderate Confidence - Worth Checking
3. **canvas-confetti** - Check if celebration effects still used
4. **@types/crypto-js** - Companion to crypto-js

## Duplicate Packages Analysis
✅ No duplicates detected in dependency tree
✅ All peer dependencies resolved correctly

## Update Strategy

### Phase 1: Security Fixes (CRITICAL)
1. Update vite: 5.4.21 → 7.3.0
   - Fixes esbuild vulnerability
   - Breaking change: review breaking changes guide
   - Estimated impact: HIGH (development build system)

### Phase 2: Major Version Updates (PLANNED)
1. React ecosystem: 18.3.1 → 19.2.3
   - Breaking changes in React 19
   - Requires testing of all components
   - Estimated impact: MEDIUM-HIGH

2. Router: 6.30.2 → 7.11.0
   - Check for breaking changes in routing
   - Estimated impact: MEDIUM

3. Validation: zod 3.25.76 → 4.2.1
   - Check schema changes
   - Estimated impact: LOW-MEDIUM

4. UI: tailwindcss 3.4.19 → 4.1.18
   - Major CSS framework update
   - Verify style rendering
   - Estimated impact: MEDIUM

### Phase 3: Minor Updates (DEFERRED)
- Package updates that don't have breaking changes
- Can be done in batches after major updates are tested

## Recommendations

1. **IMMEDIATE**: Fix vite vulnerability (security)
2. **RECOMMENDED**: Update React to 19 (latest, stable)
3. **OPTIONAL**: Conservative approach - update minor versions only
4. **VERIFY**: Test suite execution after each update batch

## Test Coverage
- Unit tests: Available (vitest)
- E2E tests: Available (Playwright)
- Bundle size: Check post-update
- Performance: Monitor

## Risk Assessment

| Update | Severity | Breaking | Testing Required |
|--------|----------|----------|------------------|
| vite 7.3.0 | CRITICAL | Yes | Full dev environment |
| React 19 | HIGH | Yes | Component rendering |
| TailwindCSS 4 | MEDIUM | Yes | Style verification |
| zod 4 | MEDIUM | Maybe | Schema validation |
| Router 7 | MEDIUM | Maybe | Navigation testing |
| Minor updates | LOW | No | Quick check |

## Next Steps
1. Create backup of package-lock.json
2. Run: npm install --save-exact [package@version]
3. Test after each major update
4. Run full test suite before committing
5. Update CHANGELOG.md with changes
