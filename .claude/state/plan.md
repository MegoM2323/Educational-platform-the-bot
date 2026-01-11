# Refactoring: Rename "forum" → "chat" across codebase

## Overview
Standardize terminology in entire codebase - replace "forum" with "chat" or "чат" (Russian).
- Backend: 175 references
- Frontend: 460 references
- Test files: 200+ references (but will NOT modify as per requirements)

## Frontend Tasks (Priority 1 - MAIN)

### Task 1: Rename directories and files
- [ ] `/frontend/src/components/forum/` → `/frontend/src/components/chat/`
- [ ] `/frontend/src/pages/dashboard/Forum.tsx` → `/frontend/src/pages/dashboard/Chat.tsx`
- [ ] `/frontend/src/hooks/useForumChats.ts` → `/frontend/src/hooks/useChatRooms.ts`
- [ ] `/frontend/src/hooks/useForumMessages.ts` → `/frontend/src/hooks/useChatMessages.ts`
- [ ] `/frontend/src/hooks/useForumMessageUpdate.ts` → `/frontend/src/hooks/useChatMessageUpdate.ts`
- [ ] `/frontend/src/hooks/useForumMessageDelete.ts` → `/frontend/src/hooks/useChatMessageDelete.ts`

**Files to rename (6 directories/17 files):**
```
frontend/src/components/forum/                       → frontend/src/components/chat/
frontend/src/components/forum/__tests__/             → frontend/src/components/chat/__tests__/
frontend/src/components/forum/EditMessageDialog.tsx  → frontend/src/components/chat/EditMessageDialog.tsx
frontend/src/components/forum/MessageActions.tsx     → frontend/src/components/chat/MessageActions.tsx
frontend/src/pages/dashboard/Forum.tsx               → frontend/src/pages/dashboard/Chat.tsx
frontend/src/hooks/useForumChats.ts                  → frontend/src/hooks/useChatRooms.ts
frontend/src/hooks/useForumMessages.ts               → frontend/src/hooks/useChatMessages.ts
frontend/src/hooks/useForumMessageUpdate.ts          → frontend/src/hooks/useChatMessageUpdate.ts
frontend/src/hooks/useForumMessageDelete.ts          → frontend/src/hooks/useChatMessageDelete.ts
```

### Task 2: Update imports and export paths
Update all files that import from renamed files:
- Update route imports in `App.tsx` and dashboard files
- Update hook imports across component files (40+ files)
- Update component imports

### Task 3: Rename exported hook functions
- `useForumChats()` → `useChatRooms()`
- `useForumMessages()` → `useChatMessages()`
- `useForumMessageUpdate()` → `useChatMessageUpdate()`
- `useForumMessageDelete()` → `useChatMessageDelete()`
- Internal variable renames: `forums` → `chatRooms`, `forum` → `chatRoom`

### Task 4: Update variable names in components
- Rename: `forumRoomId` → `chatRoomId`
- Rename: `forumInput` → `chatInput`
- Rename: `forumMessages` → `chatMessages`
- Rename: `isForumPage` → `isChatPage`
- Replace strings: `/forum` → `/chat`, `/dashboard/*/forum` → `/dashboard/*/chat`

### Task 5: Update constants and config
- Check `frontend/src/config/` for `FORUM_*` constants → `CHAT_*`
- Update API endpoint paths if any reference forum

### Task 6: Update route navigation
- Sidebar links: "Forum" → "Чат" (in StudentSidebar, TeacherSidebar, etc.)
- Route params: `/forum` → `/chat` in App.tsx router config
- Navigation state variables

## Backend Tasks (Priority 2)

### Task 7: Update Python variable names
- Replace in `models.py`: Field choices, verbose_name, help_text
- Replace in `apps.py`: verbose_name, comments
- Replace in `signals.py`: comments, variable names
- Replace in `permissions.py`: docstrings, variable names
- Replace in `views.py`: comments, parameter names, docstrings
- Replace in `services/chat_service.py`: method docstrings, comments

### Task 8: Update test files (Python)
**SKIP - per requirements, but list for reference:**
- backend/tests/test_chat_types.py: TestForumSubjectChat → TestChatSubject
- backend/tests/test_e2e_chat_flow.py: comments only
- backend/tests/test_chat_integration.py: comments only
- backend/tests/test_chat_moderation.py: forum_room fixture → chat_room

## Documentation Tasks (NOT doing - per requirements)
- [ ] Skip: README.md, MANUAL_TESTING_CHECKLIST.md
- [ ] Skip: E2E test files and test reports
- [ ] Skip: Git commit history

## Notes
- **DO NOT** rename Django migrations
- **DO NOT** modify test expectations
- **DO NOT** change API endpoint names that are already stable
- **DO NOT** touch git history
- Ensure imports are consistent after refactoring
- Frontend must compile without errors (npm run build)

## Execution Order
1. Rename directories (Task 1)
2. Rename files (Task 1)
3. Update imports (Task 2, 3, 4, 5, 6)
4. Update backend files (Task 7)
5. Run formatter: black
6. Run type checker: mypy
7. Verify frontend build: npm run build --dry-run (if available)

## Status
- [ ] Pending: coder implementation
- [ ] Pending: reviewer check
- [ ] Pending: frontend build test
