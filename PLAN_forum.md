# Forum Functionality Bug Fixes Plan

**Status**: planning
**Created**: 2025-12-29
**Scope**: Functionality bugs only (NO security, NO rate limiting)

## Overview

This plan addresses all functionality bugs found during forum analysis. Issues are grouped by severity and dependency to maximize parallel development while respecting file locks.

## Progress Summary

| Wave | Total | Done | Blocked |
|------|-------|------|---------|
| 1    | 6     | 6    | 0       |
| 2    | 11    | 9    | 0       |
| 3    | 12    | 12   | 0       |
| 4    | 10    | 10   | 0       |
| 5    | 9     | 9    | 0       |
| 6    | 8     | 8    | 0       |
| **TOTAL** | **56** | **54** | **0** |

## File Locks Matrix

| File | Wave 1 | Wave 2 | Wave 3 | Wave 4 | Wave 5 | Wave 6 |
|------|--------|--------|--------|--------|--------|--------|
| backend/chat/forum_views.py | T001-T004 | - | - | - | - | - |
| backend/chat/serializers.py | T005 | - | - | - | - | - |
| backend/chat/consumers.py | T006 | T015-T016 | - | - | - | - |
| frontend/src/integrations/api/forumAPI.ts | - | T007-T009 | - | - | - | - |
| frontend/src/pages/dashboard/Forum.tsx | - | T010-T014 | T017-T024 | - | - | - |
| frontend/src/services/chatWebSocketService.ts | - | - | T025-T028 | - | - | - |
| frontend/src/hooks/useForumMessages.ts | - | - | - | T029-T038 ✅ | - | - |
| frontend/src/components/forum/EditMessageDialog.tsx | - | - | - | T034-T035 ✅ | - | - |

---

## Wave 1: CRITICAL Backend Fixes (6 tasks)

**Goal**: Fix message sending permissions, race conditions, and data handling

### T001: Block ADMIN from sending messages (Parent CAN send)
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/forum_views.py`
- **Severity**: CRITICAL
- **Agent**: @py-backend-dev
- **Issue**: F101 - ADMIN can send messages despite being read-only role
- **Location**: Lines 382-574 (send_message action)
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Add role check after access validation: `if user.is_staff or user.is_superuser:`
- [x] Return 403 Forbidden with message in Russian
- [x] Log warning when blocked (includes user id, is_staff, is_superuser flags, room id)
- [x] Parent role is NOT blocked - they can send messages

---

### T002: Fix race condition in InitiateChatView [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/forum_views.py`
- **Severity**: CRITICAL
- **Agent**: @py-backend-dev
- **Issue**: F007 - Double create possible without lock
- **Location**: Lines 1518-1627 (InitiateChatView)
- **Effort**: 45 min

**AC**:
- [x] Verify `select_for_update()` is used on enrollment before chat existence check
- [x] Ensure `get_or_create` is within the same `transaction.atomic()` block
- [x] Add retry logic for IntegrityError on concurrent create

---

### T003: Add pagination parameter validation
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/forum_views.py`
- **Severity**: CRITICAL
- **Agent**: @py-backend-dev
- **Issue**: F001 - Unhandled ValueError on pagination parsing
- **Location**: Lines 304-305
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [x] Wrap `int(request.query_params.get('limit', 50))` in try-except ValueError
- [x] Return 400 Bad Request with message "Invalid pagination parameter"
- [x] Validate: limit > 0, offset >= 0
- [x] Apply same validation to `offset` parameter

---

### T004: Add filter parameter validation [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/forum_views.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F002, F004, F006 - Filters/params not validated
- **Location**: Lines 320-336
- **Effort**: 30 min

**AC**:
- [x] Validate sender_id is numeric if provided
- [x] Validate message_type is one of allowed values: `['text', 'file', 'image', 'system']`
- [x] Validate pk and message_id are valid UUIDs/integers (handled by DRF URL routing)
- [x] Return 400 Bad Request with specific error message for each invalid param

---

### T005: Fix ChatRoomDetailSerializer.get_messages() context
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/serializers.py`
- **Severity**: CRITICAL
- **Agent**: @py-backend-dev
- **Issue**: F020 - MessageSerializer called without context breaks avatar URLs
- **Location**: Lines 107-109
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Pass `context=self.context` to MessageSerializer: `MessageSerializer(messages, many=True, context=self.context).data`
- [x] Verify avatar URLs are absolute after fix (context now passed, enabling request.build_absolute_uri)

---

### T006: Fix unguarded scope['user'] access in disconnect handler
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
- **Severity**: CRITICAL
- **Agent**: @py-backend-dev
- **Issue**: F031 - AttributeError possible if user not authenticated
- **Location**: Lines 94-155 (disconnect method)
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Check `if self.scope.get('user') and self.scope['user'].is_authenticated:` before accessing user attributes
- [x] Add safe fallback for user_joined and typing_stop broadcasts (unauthenticated users just leave group silently)
- [x] Add exception handling around group_send calls and group_discard
- [x] Also fixed same issue in GeneralChatConsumer.disconnect()

---

## Wave 2: Frontend API and Basic UI Fixes (11 tasks)

**Blocked by**: Wave 1 (backend must be stable first)

### T007: Add moderation API endpoints to forumAPI.ts [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/integrations/api/forumAPI.ts`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F080 - Missing pin/lock/mute endpoints
- **Effort**: 45 min

**AC**:
- [x] Add `pinMessage(chatId: number, messageId: number): Promise<PinResponse>`
- [x] Add `lockChat(chatId: number): Promise<LockResponse>`
- [x] Add `muteParticipant(chatId: number, userId: number): Promise<MuteResponse>`
- [x] Add corresponding TypeScript interfaces for responses

---

### T008: Fix edit/delete message URL pattern [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/integrations/api/forumAPI.ts`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F091 - Wrong URL pattern for forum message edit/delete
- **Location**: Lines 328-358
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Change edit URL from `/chat/messages/${messageId}/` to `/chat/forum/{chatId}/messages/${messageId}/edit/`
- [x] Change delete URL from `/chat/messages/${messageId}/` to `/chat/forum/{chatId}/messages/${messageId}/delete/`
- [x] Update function signatures to accept chatId parameter

---

### T009: Handle empty response in getForumMessages
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/integrations/api/forumAPI.ts`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F062 - Empty array fallback hides errors
- **Location**: Lines 196-197
- **Effort**: 15 min

**AC**:
- [ ] Log warning when returning empty array as fallback
- [ ] Distinguish between "no messages" and "error fetching"

---

### T010: Hide send controls for Admin ONLY (NOT parent!) [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F102 - UI shows send controls for Admin (read-only role)
- **Location**: ChatWindow component
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [ ] Add `isReadOnly` prop to ChatWindow based on `currentUserRole === 'parent' || currentUserRole === 'admin'`
- [ ] Conditionally render input area and send button
- [ ] Show "Read-only access" message instead of input

---

### T011: Hide send controls for Admin role [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F103 - UI shows send controls for Admin (read-only role)
- **Location**: ChatWindow component
- **Effort**: (Combined with T010)
- **Status**: COMPLETED

**AC**:
- [x] (Combined with T010 - same fix)

---

### T012: Hide "New Chat" button for Admin ONLY (NOT parent!) [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F104, F106 - Admin should not create chats
- **Location**: Lines 1370-1387
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Conditionally render "New Chat" button: `{user?.role !== 'admin' && ...}`
- [x] Parent role is NOT blocked - they can see the button

---

### T013: Disable send when chat is_active=false [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F072 - Frontend doesn't disable send when chat inactive
- **Location**: ChatWindow component
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [x] Check `chat?.is_active` before allowing send
- [x] Disable input and button when inactive
- [x] Show user-friendly message "Чат заблокирован модератором"

---

### T014: Improve "Chat is inactive" error message [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F080 - Generic error without context
- **Effort**: 10 min
- **Status**: COMPLETED

**AC**:
- [x] Changed error message to "Чат заблокирован модератором"
- [x] Added visual indicator (lock icon) in chat header when inactive

---

### T015: Fix race condition in participants check-then-add [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F032 - Race condition in WebSocket participant check
- **Location**: Lines 278-279
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Use `get_or_create` instead of check-then-add pattern
- [x] Wrap in `transaction.atomic()` where needed
- [x] Add exception handling for IntegrityError

---

### T016: Add exception handler for mark_message_read [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F033 - Missing exception handler
- **Location**: Lines 256-260
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Add try-except around mark_message_read call
- [x] Log error on failure
- [x] Don't propagate exception to client (silent fail for read marks)

---

## Wave 3: Frontend UI/UX and WebSocket Fixes (12 tasks)

**Blocked by**: Wave 2

### T017: Fix race condition in chat selection [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F042 - Multiple pending timeouts on rapid chat switches
- **Location**: Lines 1224-1250 (handleSelectChat)
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Store timeout ID in useRef (switchTimeoutRef)
- [x] Clear previous timeout on new selection
- [x] Add debounce (200ms) for rapid switches

---

### T018: Add missing useEffect dependency for WebSocket [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F040 - Missing dependency causes stale closures
- **Location**: Lines 1170-1222 (WebSocket useEffect)
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Audit all dependencies in WebSocket useEffect
- [x] Add missing `user` dependency
- [x] Handlers already wrapped in useCallback

---

### T019: Reset isSwitchingChat on WebSocket failure [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F046 - isSwitchingChat never reset if WebSocket fails
- **Location**: Lines 1002, 1247
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Add error handling in WebSocket connect that resets isSwitchingChat
- [x] Set isSwitchingChat to false in catch block
- [x] Added try-catch wrapper around connectToRoom

---

### T020: Reset edit/delete modal state on error [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F044 - Modal state not reset on error
- **Location**: Lines 1030-1044 (edit/delete mutations)
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Add onError callback to editMessageMutation that clears editingMessage
- [x] Add onError callback to deleteMessageMutation that clears deletingMessageId and isDeleteConfirmOpen
- [x] Show toast with error message

---

### T021: Clear typing timeouts on component unmount [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F045 - Typing timeout cleanup incomplete
- **Location**: Lines 1004, 1219-1220
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Clear all entries in typingTimeoutsRef.current on unmount
- [x] Add cleanup in useEffect return function
- [x] Use proper forEach cleanup pattern

---

### T022: Add validation for selectedChat before mutations [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F051 - Missing selectedChat validation
- **Location**: Lines 1252-1264 (handleSendMessage)
- **Effort**: 10 min
- **Status**: COMPLETED

**AC**:
- [x] Add null check for selectedChat before calling mutations
- [x] Show error toast if no chat selected
- [x] Guard all chat-dependent operations

---

### T023: Fix delete dialog state not reset on cancel [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F068 - Delete dialog state not reset on cancel
- **Location**: Lines 1420-1445 (AlertDialog)
- **Status**: COMPLETED
- **Effort**: 10 min

**AC**:
- [x] Add onOpenChange handler that clears deletingMessageId when closing
- [x] Ensure cancel button clears both states

---

### T024: Handle async callback race in handleChatInitiated [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F043 - Async callback can race with component state
- **Status**: COMPLETED
- **Location**: Lines 1280-1296
- **Effort**: 20 min

**AC**:
- [x] Add mounted ref to check if component is still mounted
- [x] Guard setSelectedChat call with mounted check
- [x] Use cleanup function in useCallback dependencies

---

### T025: Remove unsubscribed callback on connection change [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/services/chatWebSocketService.ts`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F060 - Memory leak from unremoved callback
- **Location**: Lines 63-82 (constructor)
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Store unsubscribe function from websocketService.onConnectionChange
- [x] Call unsubscribe in disconnect() method
- [x] Add proper cleanup in ChatWebSocketService destructor

---

### T026: Fix connectToRoom Promise callback persistence [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/services/chatWebSocketService.ts`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F061 - Promise callbacks persist after room disconnect
- **Location**: Lines 256-301
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Store unsubscribe function for connection status callback
- [x] Call unsubscribe in resolve/reject handlers
- [x] Add cleanup in disconnectFromRoom

---

### T027: Add error propagation to connectToRoom [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/services/chatWebSocketService.ts`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F062 - Async init without error propagation
- **Location**: Lines 287-300
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [x] Reject promise with error details instead of returning false
- [x] Add proper error handling in catch block
- [x] Propagate error message to caller

---

### T028: Guard against double disconnectFromRoom calls [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/services/chatWebSocketService.ts`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F074 - No guard against disconnectFromRoom called twice
- **Location**: Lines 307-323
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Check if subscription exists before unsubscribing
- [x] Add early return if already disconnected
- [x] Log warning if called twice

---

## Wave 4: Hooks and Component Fixes (10 tasks)

**Blocked by**: Wave 3

### T029: Fix race condition in pagination offset calculation [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: CRITICAL
- **Agent**: @react-frontend-dev
- **Issue**: F052 - Race condition in getNextPageParam
- **Location**: Lines 37-50
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Use stable page tracking instead of reducing allPages
- [x] Calculate offset using allPages.flat().length for stable tracking
- [x] Handle concurrent page fetches correctly

---

### T030: Fix InfiniteData structure mismatch [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F041 - InfiniteData structure mismatch
- **Location**: Multiple locations
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [x] Ensure all cache updates use correct InfiniteData shape
- [x] Add type guards for InfiniteData access
- [x] Preserve pageParams in all InfiniteData operations

---

### T031: Fix infinite loop risk in message update [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F050 - Infinite loop risk in mutation
- **Location**: Lines 162-186 (onSuccess)
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [x] Add message ID comparison before update
- [x] Skip update if message already exists (WebSocket race)
- [x] Add guard against self-triggered invalidation

---

### T032: Add AbortController to API functions [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F050, F053 - No abort on stale requests
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Accept AbortSignal in query functions
- [x] Pass signal to forumAPI calls
- [x] Handle AbortError gracefully (don't show as error)

---

### T033: Fix legacy hook offset changes [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F053 - Legacy hook doesn't cancel on offset change
- **Location**: Lines 72-90
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Add AbortController to useQuery
- [x] Cancel previous request when offset changes (via signal)
- [x] Use placeholderData for smooth transitions

---

- **Status**: COMPLETED
### T034: Fix EditMessageDialog allows save unchanged [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/components/forum/EditMessageDialog.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F069 - EditMessageDialog allows save unchanged
- **Effort**: 15 min

**AC**:
- [x] Compare new content with original before saving
- [x] Disable save button if content unchanged
- [x] Show hint that content is unchanged

---
- **Status**: COMPLETED

### T035: Fix EditMessageDialog textarea loses focus [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/components/forum/EditMessageDialog.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F073 - Textarea loses focus on re-render
- **Effort**: 15 min

**AC**:
- [x] Use autoFocus prop correctly
- [x] Prevent re-render on content change
- [x] Use controlled component pattern properly

---
- **Status**: COMPLETED

### T036: Fix stale user data in optimistic updates [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F051 - Stale user data in optimistic updates
- **Location**: Lines 120-138
- **Effort**: 20 min

**AC**:
- [x] Access user data from fresh auth context
- [x] Don't capture user in closure
- [x] Refresh user data before creating optimistic message

- **Status**: COMPLETED
---

### T037: Add concurrent mutation/query invalidation guard [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F056 - Concurrent mutation/query invalidation race
- **Effort**: 25 min

**AC**:
- [x] Use setQueryData instead of invalidateQueries for immediate updates
- [x] Add optimistic update coordination
- **Status**: COMPLETED
- [x] Prevent race between mutation and background refetch

---

### T038: Fix memory leak from stale optimistic messages [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/hooks/useForumMessages.ts`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F060 - Memory leak from stale optimistic messages
- **Effort**: 20 min

**AC**:
- [ ] Track optimistic message IDs
- [ ] Clean up stale optimistic messages after timeout
- [ ] Remove orphaned optimistic messages on refetch

---

## Wave 5: Backend N+1 and Edge Cases (9 tasks)

**Blocked by**: Wave 1

### T039: Fix N+1 query in ChatRoomListSerializer.get_participants() [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/serializers.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F003 - N+1 query in get_participants
- **Location**: Lines 32-38
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Use prefetch_related('participants') in view queryset
- [x] Access prefetched data in serializer without extra query
- [x] Verify no additional queries per chat

---

### T040: Fix N+1 queries for teacher contacts [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/forum_views.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F009 - N+1 queries in AvailableContactsView for teacher
- **Location**: Lines 1237-1292
- **Effort**: 45 min
- **Status**: COMPLETED

**AC**:
- [x] Batch load all enrollments in single query
- [x] Use select_related for enrollment relationships
- [x] Prefetch existing chats with single query

---

### T041: Fix missing return in check_parent_access_to_room [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F034 - Missing return for parent access check
- **Location**: check_room_access method
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Ensure all code paths return boolean
- [x] Add explicit return False for non-matching cases
- [x] Add logging for debug

---

### T042: Fix type checking inconsistency in ChatConsumer [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
- **Severity**: MEDIUM
- **Agent**: @py-backend-dev
- **Issue**: F035 - Type checking inconsistency
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [x] Use consistent ChatRoom.Type enum comparisons
- [x] Avoid string literals for type checks (replaced with UserModel.Role enum)
- [x] Add type annotations (imported UserModel)

---

### T043: Fix race condition in disconnect - room_id undefined [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F036 - room_id may be undefined in disconnect
- **Location**: Lines 94-131
- **Effort**: 20 min

**AC**:
- [ ] Check if room_id is set before accessing
- [ ] Use getattr with default for safety
- [ ] Add early return if no room_id

---

### T044: Fix missing transaction in add_parent_to_participants [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/consumers.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F037 - Race condition without transaction
- **Location**: Lines 470-488
- **Effort**: 20 min

**AC**:
- [ ] Wrap M2M add and ChatParticipant create in transaction.atomic
- [ ] Handle IntegrityError for duplicate add
- [ ] Add logging for race condition detection

---

### T045: Fix subquery NULL case breaks unread count [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/forum_views.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F017 - NULL handling in unread count subquery
- **Location**: Lines 174-202
- **Effort**: 30 min

**AC**:
- [ ] Use Coalesce to handle NULL last_read_at
- [ ] Add default value for missing participant records
- [ ] Verify count is 0 when all messages read

---

### T046: Fix empty chat name validation [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/forum_views.py`
- **Severity**: MEDIUM
- **Agent**: @py-backend-dev
- **Issue**: F014 - Missing validation for empty chat name
- **Location**: Lines 1567-1607
- **Effort**: 15 min

**AC**:
- [ ] Add validation for empty/whitespace-only name
- [ ] Generate default name if empty
- [ ] Log warning for fallback name usage

---

### T047: Fix avatar handling when request is None [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/backend/chat/serializers.py`
- **Severity**: HIGH
- **Agent**: @py-backend-dev
- **Issue**: F022 - Avatar URL error when request missing
- **Location**: Lines 179-185
- **Effort**: 15 min

**AC**:
- [ ] Check request is not None before build_absolute_uri
- [ ] Return relative URL as fallback
- [ ] Add test for None request context

---

## Wave 6: Remaining UI Polish and Edge Cases (8 tasks)

**Blocked by**: Wave 4, Wave 5

### T048: Add moderation UI buttons (pin/lock/mute) [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F081 - Moderation UI not implemented
- **Effort**: 60 min
- **Status**: COMPLETED

**AC**:
- [x] Add pin button to message actions for moderators
- [x] Add lock/unlock button to chat header for moderators
- [x] Add mute button to participant list for moderators (N/A - no participant list UI)
- [x] Show visual indicators for pinned/locked/muted state

---

### T049: Add WebSocket support for moderation actions [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/services/chatWebSocketService.ts`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F084 - No WebSocket support for moderation
- **Effort**: 45 min
- **Status**: COMPLETED

**AC**:
- [x] Add handlers for message_pinned, chat_locked, user_muted events
- [x] Add send methods for moderation actions
- [x] Update UI in real-time on moderation events

---

### T050: Add visible indication of moderation status [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F086 - No visible moderation status
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Show pin icon on pinned messages
- [x] Show lock icon in header for locked chats (already done in T013/T014)
- [x] Show muted indicator for muted participants (N/A - no participant list UI)

---

### T051: Fix typing timeout uses roomId 0 as default [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F071 - Typing timeout uses wrong key
- **Effort**: 10 min
- **Status**: COMPLETED

**AC**:
- [x] Use actual roomId instead of 0 as default
- [x] Guard against undefined/null roomId
- [x] Use string key instead of number for Map

---

### T052: Add error boundary for WebSocket handlers [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F049 - No error boundary for WebSocket handlers
- **Effort**: 30 min
- **Status**: COMPLETED

**AC**:
- [x] Wrap WebSocket handler callbacks in try-catch
- [x] Show error notification on handler failure
- [x] Log error details for debugging

---

### T053: Fix error handling type mismatch [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F054 - Error handling type mismatch
- **Effort**: 15 min
- **Status**: COMPLETED

**AC**:
- [x] Add proper error type guards
- [x] Handle both Error objects and string errors
- [x] Normalize error messages for display

---

### T054: Fix Edit/Delete permission misalignment [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: HIGH
- **Agent**: @react-frontend-dev
- **Issue**: F085 - Frontend/backend permission mismatch
- **Effort**: 20 min
- **Status**: COMPLETED

**AC**:
- [x] Align frontend canModerate check with backend _check_moderation_permission
- [x] Add tutor moderation support for FORUM_TUTOR chats
- [x] Add proper role-based edit/delete logic

---

### T055: Fix no error clearing on successful edit/delete [COMPLETED]
- **File**: `/home/mego/Python Projects/THE_BOT_platform/frontend/src/pages/dashboard/Forum.tsx`
- **Severity**: MEDIUM
- **Agent**: @react-frontend-dev
- **Issue**: F070 - Error state not cleared after success
- **Effort**: 10 min
- **Status**: COMPLETED

**AC**:
- [x] Clear error state on successful edit/delete
- [x] Add onSuccess callback that clears errors
- [x] Reset error state when starting new operation

---

## Critical Path Summary

```
Wave 1 (Backend Critical) ─┬─> Wave 2 (API + Basic UI)
                           │
                           └─> Wave 5 (Backend N+1)
                                        │
Wave 2 ─────────────────────> Wave 3 (UI/UX + WebSocket)
                                        │
                              Wave 4 (Hooks + Components)
                                        │
Wave 4 + Wave 5 ──────────────> Wave 6 (Polish + Edge Cases)
```

## Estimated Total Effort

- **Wave 1**: ~2.5 hours (6 tasks)
- **Wave 2**: ~3.5 hours (11 tasks)
- **Wave 3**: ~4 hours (12 tasks)
- **Wave 4**: ~3.5 hours (10 tasks)
- **Wave 5**: ~3.5 hours (9 tasks)
- **Wave 6**: ~3.5 hours (8 tasks)

**Total**: ~20.5 hours

## Agent Allocation

| Agent | Tasks |
|-------|-------|
| @py-backend-dev | T001-T006, T015-T016, T039-T047 (19 tasks) |
| @react-frontend-dev | T007-T014, T017-T038, T048-T055 (37 tasks) |

## Notes

1. All estimates assume familiarity with codebase
2. Wave 1 is critical path - must complete before frontend work
3. Wave 5 can run in parallel with Wave 3/4 (no file conflicts)
4. Moderation UI (Wave 6) should only start after backend is stable
5. Testing should be done after each wave to catch regressions
