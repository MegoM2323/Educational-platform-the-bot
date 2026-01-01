# Chat Selection State Reset Issues - Fix Documentation

## Task: T_W14_008
**Bug:** A3 - Chat selection/creation fails, state management broken
**Status:** FIXED

---

## Problem Analysis

The Forum component had several critical state management issues when switching between chats:

1. **Message Cache Pollution**: When switching from Chat A to Chat B, messages from Chat A would persist in the cache and could appear in Chat B's UI
2. **Stale WebSocket Messages**: WebSocket messages from the old chat could be delivered to the new chat if timing issues occurred
3. **Pending Requests Not Cancelled**: API requests for the old chat weren't being cancelled, leading to race conditions
4. **Loading State Persistence**: The `isSwitchingChat` loading state could persist across chat switches due to unmounting race conditions
5. **WebSocket Connection Issues**: Old WebSocket connections weren't properly disconnected before new ones were established
6. **Query Key Issues**: While query keys included chatId, there wasn't explicit cache clearing on chat switch

---

## Solutions Implemented

### 1. Forum.tsx - Chat Selection Handler (Lines 1364-1416)

**Key Changes:**
```typescript
const handleSelectChat = async (chat: ForumChat) => {
  // Clear previous timeout to prevent race conditions
  if (switchTimeoutRef.current) {
    clearTimeout(switchTimeoutRef.current);
  }

  switchTimeoutRef.current = setTimeout(async () => {
    setIsSwitchingChat(true);
    setError(null);
    setTypingUsers([]);

    // T008: CRITICAL FIX - Clear old chat messages cache before switching
    const previousChatId = selectedChat?.id;
    if (previousChatId && previousChatId !== chat.id) {
      logger.debug('[Forum] Clearing message cache for previous chat:', previousChatId);
      // Remove the old chat's messages from cache completely
      queryClient.removeQueries({ queryKey: ['forum-messages', previousChatId] });
    }

    // Select new chat (triggers useForumMessages with new chatId)
    setSelectedChat(chat);
    setSearchQuery('');

    // T008: Cancel any pending message requests for the old chat
    if (previousChatId && previousChatId !== chat.id) {
      await queryClient.cancelQueries({ queryKey: ['forum-messages', previousChatId] });
    }

    // Mark chat as read logic...
    // ...

    // Reset loading state with mounted check
    setTimeout(() => {
      if (isMountedRef.current) {
        setIsSwitchingChat(false);
      }
    }, 500);
  }, 200);
};
```

**Fixes:**
- Explicitly clears old chat message cache with `queryClient.removeQueries()`
- Cancels pending requests for old chat to prevent race conditions
- Uses previous chat ID to ensure correct cleanup
- Includes mounted state check to prevent state updates on unmounted components

### 2. Forum.tsx - WebSocket Connection Management (Lines 1300-1389)

**Key Changes:**
```typescript
useEffect(() => {
  if (!selectedChat || !user) return;

  const chatId = selectedChat.id;
  let isEffectActive = true;  // Track effect lifecycle

  logger.debug('[Forum] Chat selected, setting up WebSocket for chat:', chatId);

  const handlers = {
    onMessage: handleWebSocketMessage,
    onTyping: handleTyping,
    onTypingStop: handleTypingStop,
    onError: handleError,
  };

  // Connect to WebSocket
  (async () => {
    try {
      // T008: Check if effect is still active before attempting connection
      if (!isEffectActive) {
        logger.debug('[Forum] Effect unmounted, skipping WebSocket connection');
        return;
      }

      logger.debug('[Forum] Connecting to chat room:', chatId);
      const connectionSuccess = await chatWebSocketService.connectToRoom(chatId, handlers);

      if (!connectionSuccess) {
        logger.error('[Forum] Failed to connect to chat room:', chatId);
        if (isEffectActive) {
          setError('Не удалось подключиться к чату. Проверьте авторизацию.');
          setIsSwitchingChat(false);
        }
      } else {
        logger.debug('[Forum] Successfully connected to chat room:', chatId);
        if (isEffectActive) {
          setIsSwitchingChat(false);
        }
      }
    } catch (error) {
      logger.error('[Forum] WebSocket connection failed:', error);
      if (isEffectActive) {
        setIsSwitchingChat(false);
        setError('Не удалось подключиться к чату');
      }
    }
  })();

  // Set initial connection state
  const initiallyConnected = chatWebSocketService.isConnected();
  logger.debug('[Forum] Initial connection state:', initiallyConnected);
  if (isEffectActive) {
    setIsConnected(initiallyConnected);
    if (initiallyConnected) {
      setError(null);
    }
  }

  // Subscribe to connection changes
  const connectionCallback = (connected: boolean) => {
    logger.debug('[Forum] Connection state changed to:', connected);
    if (isEffectActive) {
      setIsConnected(connected);
      if (!connected) {
        setError('Соединение потеряно. Попытка переподключения...');
      } else {
        setError(null);
      }
    }
  };

  chatWebSocketService.onConnectionChange(connectionCallback);

  // Cleanup: disconnect when chat changes or component unmounts
  return () => {
    isEffectActive = false;

    logger.debug('[Forum] Cleaning up WebSocket for chat:', chatId);
    // T008: Disconnect from the old chat room
    chatWebSocketService.disconnectFromRoom(chatId);
    setTypingUsers([]);

    // T021: Clear all typing timeouts to prevent memory leaks
    typingTimeoutsRef.current.forEach((timeoutId) => clearTimeout(timeoutId));
    typingTimeoutsRef.current.clear();
  };
}, [selectedChat, user, handleWebSocketMessage, handleTyping, handleTypingStop, handleError]);
```

**Fixes:**
- Uses `isEffectActive` flag to track effect lifecycle and prevent state updates on unmounted components
- Ensures old WebSocket connection is disconnected before establishing new one
- Guards all state updates with `isEffectActive` check
- Properly logs connection state transitions for debugging
- Clears all typing timeouts to prevent memory leaks

### 3. useForumMessages Hook (Lines 10-71)

**Key Changes:**
```typescript
export const useForumMessages = (chatId: number | null) => {
  const MESSAGES_PER_PAGE = 50;

  return useInfiniteQuery<ForumMessage[], Error>({
    // T008: Query key includes chatId to ensure cache isolation between chats
    queryKey: ['forum-messages', chatId],
    queryFn: async ({ pageParam = 0, signal }) => {
      if (!chatId) {
        throw new Error('Chat ID is required');
      }
      // ... fetch logic ...
    },
    // ...
    // T008: Enable query only when chatId is available and valid
    enabled: !!chatId && chatId > 0,
    // T008: Keep data fresh but don't background refetch frequently
    staleTime: 1000 * 60,
    // T008: Refetch when component mounts to ensure fresh data for new chat
    refetchOnMount: 'stale',
    refetchOnWindowFocus: false,
    // ... retry logic ...
  });
};
```

**Fixes:**
- Query key explicitly includes chatId for proper cache isolation
- Enables query only when chatId is valid (> 0)
- Uses `refetchOnMount: 'stale'` to fetch fresh data when mounting with new chat
- Prevents cross-chat cache pollution through proper query key structure

---

## Acceptance Criteria Status

✅ **Switching chats clears old messages**
- Implemented via `queryClient.removeQueries()` in handleSelectChat
- Old chat cache is completely cleared before new chat is selected

✅ **No messages from old chat appear in new chat**
- Cache isolation through query keys: `['forum-messages', chatId]`
- Explicit cache clearing before chat switch
- Pending requests are cancelled to prevent race conditions

✅ **Loading state properly indicates fetch in progress**
- `isSwitchingChat` flag controls loading UI
- 500ms timeout ensures sufficient time for WebSocket connection
- Mounted state check prevents stale state updates

✅ **No stale WebSocket messages**
- Old WebSocket connection is disconnected in effect cleanup
- New connection established only after old one is fully disconnected
- Message handlers check selectedChat to ensure message is for current chat

✅ **Chat icons/titles update immediately**
- Chat selection updates `selectedChat` state immediately
- UI renders with new chat data from the selected chat object
- Avatar and title are derived from selectedChat properties

---

## Testing

A comprehensive test suite was created in:
`frontend/src/pages/dashboard/__tests__/Forum.chat-state.test.tsx`

**Test Coverage:**
1. Cache clearing on chat switch
2. Request cancellation for old chat
3. Chat title/icon immediate updates
4. Stale message prevention
5. Loading state reset
6. WebSocket disconnection/reconnection
7. Chat as read marking
8. Rapid switch handling (debounce)
9. Cache isolation between chats

---

## Files Modified

### 1. `frontend/src/pages/dashboard/Forum.tsx`
- **Lines 1364-1416**: Enhanced `handleSelectChat` function with cache clearing and request cancellation
- **Lines 1300-1389**: Improved WebSocket connection effect with proper lifecycle management
- **Tags**: T008 (Chat State Reset)

### 2. `frontend/src/hooks/useForumMessages.ts`
- **Lines 10-71**: Enhanced query configuration with proper cache isolation
- **Tags**: T008 (Query Key Configuration)

### 3. `frontend/src/pages/dashboard/__tests__/Forum.chat-state.test.tsx` (NEW)
- Comprehensive test suite for chat state management
- Tests for all acceptance criteria

---

## Logging & Debugging

Added detailed logging for troubleshooting:
```
[Forum] Chat selected, setting up WebSocket for chat: 123
[Forum] Clearing message cache for previous chat: 100
[Forum] Connecting to chat room: 123
[Forum] Successfully connected to chat room: 123
[Forum] Cleaning up WebSocket for chat: 123
[Forum] Initial connection state: true
[Forum] Connection state changed to: true
```

---

## Performance Considerations

1. **Memory**: Explicit cache cleanup prevents accumulation of old chat data
2. **Network**: Request cancellation prevents unnecessary API calls
3. **React**: Mounted state checks prevent unnecessary re-renders
4. **WebSocket**: Proper connection management prevents memory leaks

---

## Migration Notes

This fix is backward compatible. No changes to component APIs or interfaces required. The fix improves internal state management without affecting parent components.

---

## Related Issues

- T010: Admin read-only mode
- T013: Chat blocking/locking
- T014: Lock indicators
- T048: Pin/lock functionality
- T050: Pinned message display
- T051: Typing indicators
- T052-T055: Error handling and validation

---

## Author

Frontend Development Team
Fix implemented for T_W14_008: Chat Selection State Reset Issues

Generated: 2025-12-29
