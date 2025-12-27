# Image Component Integration Checklist

This checklist helps integrate the Image optimization component throughout the application and replace existing img tags.

## Phase 1: Core Integration (High Priority)

### 1. Material Thumbnails
- [ ] MaterialCard component
  - [ ] Replace thumbnail img with Image component
  - [ ] Add lazyObserver={true} for list views
  - [ ] Set aspectRatio={4/3}
  - [ ] Add quality={75}

- [ ] MaterialListItem component
  - [ ] Replace thumbnail with Image
  - [ ] Add lazy loading
  - [ ] Handle error gracefully

### 2. User Avatars
- [ ] ProfileCard component
  - [ ] Replace img with AvatarImage
  - [ ] Width={100}
  - [ ] className="rounded-full"

- [ ] StudentSubmissionsList
  - [ ] Replace avatar images with AvatarImage
  - [ ] Use lazy loading

- [ ] TeacherDashboard
  - [ ] Replace all avatar images with AvatarImage

### 3. Knowledge Graph Elements
- [ ] Element preview images
  - [ ] Replace with Image component
  - [ ] Add aspectRatio
  - [ ] Enable lazy loading

- [ ] Lesson thumbnail
  - [ ] Replace with Image
  - [ ] Optimize for different screen sizes

### 4. Assignment/Submission Images
- [ ] Assignment submission thumbnails
  - [ ] Replace with Image component
  - [ ] Error handling for failed uploads

- [ ] Student work images
  - [ ] Replace with Image
  - [ ] Maintain quality for grading

## Phase 2: Secondary Integration (Medium Priority)

### 5. Forum/Chat Images
- [ ] Forum post images
  - [ ] Replace with Image component
  - [ ] Add lazy loading
  - [ ] Responsive sizing

- [ ] Chat image attachments
  - [ ] Replace with Image
  - [ ] Error fallback

- [ ] User profile backgrounds
  - [ ] Replace with BackgroundImage component
  - [ ] Add overlay support

### 6. Admin Panel
- [ ] Dashboard graphs/images
  - [ ] Replace with Image where applicable
  - [ ] Add quality control

- [ ] User management avatars
  - [ ] Replace with AvatarImage

- [ ] Analytics visualizations
  - [ ] Replace static images with Image component

### 7. Reports
- [ ] Report graphs/charts
  - [ ] Replace with Image component
  - [ ] High quality for printing

- [ ] Student photos in reports
  - [ ] Replace with AvatarImage

## Phase 3: Edge Cases (Low Priority)

### 8. Dynamic Content
- [ ] User-uploaded content
  - [ ] Validate image URLs
  - [ ] Add error handling
  - [ ] Add virus scan integration hooks

- [ ] External content
  - [ ] CDN URL support
  - [ ] Fallback handling

### 9. Special Cases
- [ ] Background patterns
  - [ ] Use BackgroundImage component
  - [ ] Optimize CSS-only patterns

- [ ] Hero images
  - [ ] Full optimization
  - [ ] High quality (90+)
  - [ ] No lazy loading for LCP

## Testing Checklist

### Unit Tests
- [ ] Image component renders
- [ ] Lazy loading works
- [ ] WebP support detected
- [ ] Error handling works
- [ ] Aspect ratio applied
- [ ] Blur effect visible
- [ ] Accessibility attributes present
- [ ] onLoad/onError callbacks fired

### Integration Tests
- [ ] Material page loads with optimized images
- [ ] Profile page renders avatars correctly
- [ ] Gallery scrolls smoothly with lazy loading
- [ ] Error states display fallback images
- [ ] Responsive layouts work across devices

### E2E Tests
- [ ] Images load visually
- [ ] Blur transition visible
- [ ] Error fallback appears on network error
- [ ] Lazy loading triggers on scroll
- [ ] Mobile viewport shows correct sizes

### Performance Tests
- [ ] LCP metric improved
- [ ] CLS metric is 0 or near-zero
- [ ] File sizes reduced 60%+
- [ ] WebP used when supported
- [ ] No layout shifts on load

## Code Review Points

When reviewing PRs with Image component changes:

1. **Accessibility**
   - [ ] Alt text is descriptive (not generic)
   - [ ] Alt text includes context (e.g., "John Doe, Grade 8 student")
   - [ ] Decorative elements have aria-hidden

2. **Performance**
   - [ ] Dimensions specified (width, height)
   - [ ] Aspect ratio set for dynamic content
   - [ ] Lazy loading enabled for non-critical images
   - [ ] Quality optimized appropriately
   - [ ] WebP support enabled

3. **Error Handling**
   - [ ] Error image provided or fallback UI acceptable
   - [ ] onError callback if needed
   - [ ] User feedback for failed images

4. **Responsive Design**
   - [ ] Sizes attribute for responsive layouts
   - [ ] Different image sizes for different viewports
   - [ ] Mobile-friendly sizing

5. **Consistency**
   - [ ] Uses existing Image components (not img tag)
   - [ ] Props follow project conventions
   - [ ] Classes match design system

## Files to Modify

### Component Updates
```
frontend/src/components/
├── MaterialCard.tsx                    # Add Image for thumbnail
├── MaterialListItem.tsx                # Add Image for thumbnail
├── ProfileCard.tsx                     # Add AvatarImage
├── StudentSubmissionsList.tsx          # Add AvatarImage for students
├── knowledge-graph/                    # Add Image for elements
├── assignments/                        # Add Image for submissions
├── student/                            # Add Image for materials
├── teacher/                            # Add AvatarImage for students
├── admin/                              # Add Image/AvatarImage
├── chat/                               # Add Image for attachments
└── reports/                            # Add Image for graphs
```

### Style/CSS Updates
```
frontend/src/styles/
├── image-optimization.css              # NEW: Image component styles
├── responsiveness.css                  # UPDATE: Media queries
└── accessibility.css                   # UPDATE: ARIA styles
```

## Migration Path

### Step 1: Validation (Week 1)
- [ ] All tests pass
- [ ] Type checking passes
- [ ] Linting passes
- [ ] Performance baseline measured

### Step 2: Phase 1 - Core Components (Week 1-2)
- [ ] MaterialCard updated
- [ ] ProfileCard updated
- [ ] Tests passing
- [ ] Performance metrics verified

### Step 3: Phase 2 - Secondary Components (Week 2-3)
- [ ] Forum/Chat images updated
- [ ] Admin panel updated
- [ ] Reports updated
- [ ] Integration tests passing

### Step 4: Phase 3 - Edge Cases (Week 3)
- [ ] Dynamic content handled
- [ ] External content support
- [ ] Special cases covered
- [ ] E2E tests passing

### Step 5: Cleanup (Week 4)
- [ ] Remove old LazyImage component
- [ ] Remove unused img tags
- [ ] Documentation updated
- [ ] Performance audit complete

## Performance Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| LCP | < 2.5s | TBD | [ ] |
| CLS | < 0.1 | TBD | [ ] |
| FID | < 100ms | TBD | [ ] |
| Image Size | -60% | TBD | [ ] |

## Documentation Updates

- [ ] README.md updated with Image component reference
- [ ] Component storybook entry created (if using Storybook)
- [ ] Developer guide updated
- [ ] Migration guide created
- [ ] Best practices documented

## QA Sign-off

- [ ] QA team reviewed component
- [ ] QA tested on multiple browsers
- [ ] QA tested on mobile devices
- [ ] Performance verified
- [ ] Accessibility verified
- [ ] Error scenarios tested

## Deployment

- [ ] Code review approved
- [ ] CI/CD pipeline passing
- [ ] Staging environment deployed
- [ ] Production rollout plan ready
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented

## Post-Deployment

- [ ] Monitor error rates
- [ ] Track Core Web Vitals
- [ ] Gather user feedback
- [ ] Performance metrics validation
- [ ] Identify additional optimizations
- [ ] Plan next phase

## Notes

### Common Issues
1. **WebP not serving**: Verify CDN supports WebP
2. **Layout shift**: Always set width/height or aspectRatio
3. **Slow loading**: Adjust lazyMargin for earlier loading
4. **Missing images**: Provide errorImage prop

### Tips
- Start with high-traffic pages for maximum impact
- Test on slow networks (3G/4G) to verify optimization
- Use Chrome DevTools to measure performance impact
- Monitor CLS with Web Vitals library
- Gather real user monitoring data

### References
- [IMAGE_OPTIMIZATION_GUIDE.md](./IMAGE_OPTIMIZATION_GUIDE.md)
- [Image.examples.tsx](./Image.examples.tsx)
- [Image.test.tsx](./__tests__/Image.test.tsx)

## Sign-off

- [ ] Developer: _____________ Date: _____
- [ ] Code Reviewer: ________ Date: _____
- [ ] QA Lead: ____________ Date: _____
- [ ] Product Owner: _______ Date: _____
