# Answer Submission Integration

Complete offline-first answer submission system with error handling, retry logic, and excellent UX.

## Architecture

### Core Components

1. **offlineStorage** (`utils/offlineStorage.ts`)
   - localStorage-based caching
   - Answer queue management
   - Retry attempt tracking
   - Auto-cleanup on success

2. **answerSubmissionService** (`services/answerSubmissionService.ts`)
   - Network status monitoring
   - Online/offline submission logic
   - Auto-sync on network restore
   - Exponential backoff retry

3. **useAnswerSubmission** (`hooks/useAnswerSubmission.ts`)
   - React state management
   - Network status subscription
   - Submission status tracking
   - Pending count monitoring

4. **LessonViewer** (integration)
   - UI feedback for all states
   - Offline/online indicators
   - Retry buttons
   - Loading states

## Features

### Offline Support

**When offline:**
- Answers cached to localStorage
- User can continue working
- "Saved locally" indicator shown
- Pending count badge displayed

**When online restored:**
- Auto-sync pending answers
- Progress notification
- Cache cleared on success

### Error Handling

**Network Error:**
```
"Вы офлайн. Ответы будут сохранены локально и отправлены при подключении к сети."
```
- Answer cached
- Offline indicator shown
- Auto-sync when connected

**Server Error (500):**
```
"Ошибка: Server error"
```
- Answer cached
- Manual retry button
- Automatic retry on network restore

**Validation Error (400):**
```
"Ошибка: Invalid answer format"
```
- Answer NOT cached (invalid data)
- Error message shown
- User can fix and resubmit

**Session Expired (401):**
```
"Ошибка: Session expired. Please log in again."
```
- Answer cached
- Redirect to login (handled by unifiedAPI)

### Retry Logic

**Automatic Retry:**
- Triggered on network restore
- Exponential backoff: 1s, 2s, 4s, 8s
- Max 5 attempts per answer
- Failed after max attempts: removed from cache

**Manual Retry:**
- "Retry" button on error messages
- "Sync Now" button when pending submissions exist
- Retries all pending answers

### User Feedback

**Submission States:**
1. **Idle** - No submission in progress
2. **Loading** - "Сохранение..." with spinner
3. **Success** - "Сохранено ✓" (green, 2 seconds)
4. **Offline** - "Сохранено локально. Будет отправлено при подключении к сети."
5. **Error** - Error message with retry button

**Indicators:**
- Offline banner (red, top of page)
- Pending submissions alert (blue, with count)
- Submission status (under element card)
- Navigation buttons disabled while submitting

## Usage

### Basic Integration

```typescript
import { useAnswerSubmission } from '@/hooks/useAnswerSubmission';

const {
  submitAnswer,
  retry,
  isLoading,
  status,
  error,
  pendingCount,
  isNetworkOnline,
} = useAnswerSubmission();

// Submit answer
await submitAnswer({
  elementId: 'elem_123',
  answer: 'User answer text',
  lessonId: 'lesson_456',
  graphId: 'graph_789',
  graphLessonId: 'gl_abc',
});

// Check status
if (status === 'success') {
  // Move to next element
}

if (status === 'offline') {
  // Answer cached, allow user to continue
}

if (status === 'error') {
  // Show error, offer retry
}
```

### Network Status Monitoring

```typescript
import { answerSubmissionService } from '@/services/answerSubmissionService';

// Subscribe to network changes
const unsubscribe = answerSubmissionService.onNetworkStatusChange((status) => {
  console.log('Network status:', status);
  // { isOnline: boolean, effectiveType?: string, downlink?: number }
});

// Cleanup
unsubscribe();
```

### Manual Cache Management

```typescript
import { offlineStorage } from '@/utils/offlineStorage';

// Get pending answers
const pending = offlineStorage.getPendingAnswers();
console.log(`${pending.length} answers pending`);

// Get specific answer
const answer = offlineStorage.getAnswer('elem_123', 'lesson_456');

// Clear all cache
offlineStorage.clearAll();

// Get last sync time
const lastSync = offlineStorage.getLastSyncTime();
```

## Data Flow

### Online Submission

```
User submits answer
  ↓
useAnswerSubmission hook
  ↓
answerSubmissionService
  ↓
Check network (fetch /api/health/)
  ↓
Network OK → lessonService.submitElementAnswer()
  ↓
API returns success
  ↓
Update UI (status: 'success')
  ↓
Invalidate TanStack Query cache
  ↓
Show "Saved ✓" (2 seconds)
  ↓
Return to 'idle'
```

### Offline Submission

```
User submits answer
  ↓
useAnswerSubmission hook
  ↓
answerSubmissionService
  ↓
Check network (fetch /api/health/)
  ↓
Network FAIL → offlineStorage.saveAnswer()
  ↓
Update UI (status: 'offline')
  ↓
Show "Saved locally" message
  ↓
Allow user to continue
```

### Auto-Sync on Network Restore

```
Network restored (window.addEventListener('online'))
  ↓
answerSubmissionService.autoSyncPendingAnswers()
  ↓
Get pending answers from offlineStorage
  ↓
For each pending answer:
  ↓
  Try lessonService.submitElementAnswer()
  ↓
  Success → offlineStorage.updateAnswerStatus('submitted')
  ↓
  Fail → offlineStorage.updateAnswerStatus('failed')
  ↓
  Max retries → remove from cache
  ↓
Update pending count
  ↓
Show sync complete notification
```

## localStorage Schema

```typescript
interface CachedAnswer {
  element_id: string;
  answer: any;
  lesson_id: string;
  graph_id?: string;
  graph_lesson_id: string;
  timestamp: string;  // ISO 8601
  attempts: number;   // 0-5
  status: 'pending' | 'failed' | 'submitted';
  error?: string;
}

// Storage key: 'kg_offline_answers'
{
  "answers": {
    "lesson_456_elem_123": CachedAnswer,
    "lesson_456_elem_124": CachedAnswer
  },
  "lastSync": "2025-12-08T12:34:56.789Z"
}
```

## UI Components

### Offline Indicator

```tsx
{!isNetworkOnline && (
  <Alert variant="destructive">
    <WifiOff className="h-4 w-4" />
    <AlertDescription>
      Вы офлайн. Ответы будут сохранены локально и отправлены при подключении к сети.
    </AlertDescription>
  </Alert>
)}
```

### Pending Submissions

```tsx
{pendingCount > 0 && isNetworkOnline && (
  <Alert className="border-blue-500 bg-blue-50">
    <Loader2 className="h-4 w-4 animate-spin" />
    <AlertDescription>
      <span>Синхронизация {pendingCount} ответов...</span>
      <Button onClick={() => retry()}>Повторить</Button>
    </AlertDescription>
  </Alert>
)}
```

### Submission Status

```tsx
{status === 'loading' && (
  <div className="flex items-center gap-2">
    <Loader2 className="h-4 w-4 animate-spin" />
    <span>Сохранение...</span>
  </div>
)}

{status === 'success' && (
  <div className="text-green-600">
    <CheckCircle className="h-4 w-4" />
    <span>Сохранено ✓</span>
  </div>
)}

{status === 'offline' && (
  <Badge variant="outline">
    <WifiOff className="h-3 w-3" />
    Сохранено локально. Будет отправлено при подключении к сети.
  </Badge>
)}

{status === 'error' && (
  <Alert variant="destructive">
    <AlertDescription>
      Ошибка: {error}
      <Button onClick={() => retry()}>Повторить</Button>
    </AlertDescription>
  </Alert>
)}
```

## Error Messages

### User-Friendly Errors

| Scenario | Message | Action |
|----------|---------|--------|
| Network down | "Вы офлайн. Ответы будут сохранены локально и отправлены при подключении к сети." | Cache answer, show offline indicator |
| Server error | "Ошибка: Server error. Retrying..." | Cache answer, auto-retry |
| Validation error | "Ошибка: Invalid answer format. Please check..." | Show error, don't cache |
| Session expired | "Ошибка: Session expired. Please log in again." | Cache answer, redirect to login |
| Max retries | "Ошибка: Unable to submit. Please check your connection." | Remove from cache, show manual retry |

## Performance

### Network Check Optimization

- HEAD request to `/api/health/` (5s timeout)
- Cached network status (updated on events)
- Debounced network checks
- Connection API integration (if available)

### localStorage Optimization

- Single JSON object (not per-answer keys)
- Cleanup on success
- Max 5 retry attempts (auto-remove)
- Lazy loading (read only when needed)

### UI Optimization

- Optimistic updates (immediate UI feedback)
- Debounced status changes (avoid flicker)
- Auto-hide success message (2 seconds)
- Minimal re-renders

## Testing

### Unit Tests

```typescript
// Test offline storage
describe('offlineStorage', () => {
  it('saves answer to localStorage', () => {
    offlineStorage.saveAnswer({ ... });
    expect(localStorage.getItem('kg_offline_answers')).toBeDefined();
  });

  it('retrieves pending answers', () => {
    const pending = offlineStorage.getPendingAnswers();
    expect(pending).toHaveLength(1);
  });

  it('removes answer after max retries', () => {
    // Simulate 5 failed attempts
    for (let i = 0; i < 5; i++) {
      offlineStorage.updateAnswerStatus('elem_123', 'lesson_456', 'failed');
    }
    expect(offlineStorage.getAnswer('elem_123', 'lesson_456')).toBeNull();
  });
});
```

### Integration Tests

```typescript
// Test auto-sync
describe('answerSubmissionService', () => {
  it('auto-syncs on network restore', async () => {
    // Save answer offline
    await answerSubmissionService.submitAnswer({ ... });

    // Trigger online event
    window.dispatchEvent(new Event('online'));

    // Wait for sync
    await waitFor(() => {
      expect(offlineStorage.getPendingCount()).toBe(0);
    });
  });
});
```

### E2E Tests

```typescript
// Test full user flow
test('submit answer offline then sync', async ({ page }) => {
  // Go offline
  await page.context().setOffline(true);

  // Submit answer
  await page.fill('[data-testid="answer-input"]', 'My answer');
  await page.click('[data-testid="submit-button"]');

  // Check offline indicator
  await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();

  // Go online
  await page.context().setOffline(false);

  // Wait for sync
  await expect(page.locator('[data-testid="sync-complete"]')).toBeVisible();
});
```

## Accessibility

- All error messages announced to screen readers
- Keyboard navigation for retry buttons
- ARIA labels on status indicators
- Clear visual feedback for all states
- Loading states with spinner + text

## Browser Compatibility

- localStorage: All modern browsers
- Online/offline events: All modern browsers
- Connection API: Chrome/Edge (graceful fallback)
- Fetch with timeout: All modern browsers

## Future Enhancements

1. **IndexedDB Migration**
   - Better performance for large datasets
   - More storage capacity
   - Structured queries

2. **Service Worker Integration**
   - Background sync
   - Offline-first architecture
   - Push notifications

3. **Conflict Resolution**
   - Handle concurrent edits
   - Merge strategies
   - Version control

4. **Analytics**
   - Track offline usage
   - Monitor sync success rate
   - Network quality metrics

## Troubleshooting

### Answers not syncing

1. Check network status: `answerSubmissionService.getNetworkStatus()`
2. Check pending count: `offlineStorage.getPendingCount()`
3. Check localStorage: Open DevTools → Application → Local Storage
4. Manual sync: `answerSubmissionService.retryFailedSubmissions()`

### localStorage full

- Max size: ~5-10MB per origin
- Clear old data: `offlineStorage.clearAll()`
- Migrate to IndexedDB if needed

### Network detection issues

- Check `/api/health/` endpoint availability
- Verify CORS headers
- Check timeout settings (5s default)
- Test with browser offline mode

## Related Files

- `/frontend/src/utils/offlineStorage.ts` - localStorage management
- `/frontend/src/services/answerSubmissionService.ts` - Submission logic
- `/frontend/src/hooks/useAnswerSubmission.ts` - React integration
- `/frontend/src/pages/lessons/LessonViewer.tsx` - UI integration
- `/frontend/src/services/lessonService.ts` - API client
