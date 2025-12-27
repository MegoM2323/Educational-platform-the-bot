# Notification Components

Comprehensive notification management components for displaying, managing, and organizing notifications in the application. Includes both active notification center and archived notification archive.

## Components

### NotificationCenter

A full-featured notification center for viewing and managing all active notifications with real-time updates.

#### Features

- **Active Notifications List**: Display all active (non-archived) notifications
- **Real-time WebSocket Updates**: Instant notifications via WebSocket
- **Search & Filter**: Search by title/message and filter by type, priority, and read status
- **Mark as Read**: Single or bulk mark notifications as read
- **Delete Notifications**: Single or bulk delete notifications
- **Pagination**: Navigate through pages of notifications
- **Selection**: Bulk select notifications with select-all option
- **Unread Counter**: Display unread notification count
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Loading States**: Skeleton loading for better UX
- **Toast Notifications**: User feedback via toast messages
- **WebSocket Connection Management**: Auto-reconnect on disconnect

#### Props

```typescript
interface NotificationCenterProps {
  onClose?: () => void; // Callback when close button is clicked
}
```

#### Usage

```tsx
import { NotificationCenter } from '@/components/notifications';
import { useNavigate } from 'react-router-dom';

// As a page
export const NotificationsPage = () => {
  const navigate = useNavigate();
  return <NotificationCenter onClose={() => navigate('/')} />;
};

// As a modal
export const NotificationModal = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)}>View Notifications</button>
      {open && <NotificationCenter onClose={() => setOpen(false)} />}
    </>
  );
};
```

### NotificationArchive

A comprehensive component for managing archived notifications with features for listing, filtering, searching, restoring, and deleting notifications.

#### Features

- **List Archived Notifications**: Display all archived notifications in a paginated table
- **Search**: Search notifications by title or message
- **Filtering**: Filter by notification type (system, message, assignment, feedback, payment, invoice)
- **Sorting**: Sort by date (newest), type, or priority
- **Pagination**: Navigate through pages with customizable items per page
- **Selection**: Bulk select notifications with select-all option
- **Restore**: Restore individual or bulk archived notifications to inbox
- **Delete**: Permanently delete individual or bulk archived notifications
- **Details View**: View full notification details in a modal
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Error Handling**: Graceful error messages and retry functionality
- **Loading States**: Skeleton loading for better UX
- **Toast Notifications**: User feedback via toast messages

#### Props

```typescript
interface NotificationArchiveProps {
  onClose?: () => void; // Callback when back button is clicked
}
```

#### Usage

```tsx
import { NotificationArchive } from '@/components/notifications';

// Basic usage
export const ArchivePage = () => {
  return <NotificationArchive />;
};

// With close callback (for modal)
export const ArchiveModal = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button onClick={() => setOpen(true)}>View Archive</button>
      {open && <NotificationArchive onClose={() => setOpen(false)} />}
    </>
  );
};
```

## Hooks

### useNotificationCenter

Custom React hook for managing active notifications with real-time updates.

#### Features

- Fetch active notifications with pagination
- Filter and search notifications
- Mark notifications as read (single and bulk)
- Delete notifications (single and bulk)
- Real-time WebSocket connection for new notifications
- Unread count tracking
- Auto-reconnection on disconnect
- Loading and error state management
- Refetch capability

#### Return Value

```typescript
{
  // State
  notifications: Notification[];
  isLoading: boolean;
  error: string | null;
  page: number;
  pageSize: number;
  totalCount: number;
  unreadCount: number;
  filters: NotificationFilters;

  // Methods
  setPage: (page: number) => void;
  setFilters: (filters: NotificationFilters) => void;
  markAsRead: (id: number) => Promise<void>;
  markMultipleAsRead: (ids: number[], markAll?: boolean) => Promise<void>;
  deleteNotification: (id: number) => Promise<void>;
  deleteMultiple: (ids: number[]) => Promise<void>;
  refetch: () => Promise<void>;
}
```

#### Usage

```tsx
import { useNotificationCenter } from '@/hooks/useNotificationCenter';

function MyComponent() {
  const {
    notifications,
    isLoading,
    unreadCount,
    markAsRead,
    deleteNotification,
  } = useNotificationCenter();

  const handleMarkAsRead = async (id: number) => {
    try {
      await markAsRead(id);
      // Success handling
    } catch (err) {
      // Error handling
    }
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Notifications ({unreadCount} unread)</h1>
      {notifications.map((notif) => (
        <div key={notif.id}>
          <h3>{notif.title}</h3>
          <p>{notif.message}</p>
          {!notif.is_read && (
            <button onClick={() => handleMarkAsRead(notif.id)}>
              Mark as read
            </button>
          )}
          <button onClick={() => deleteNotification(notif.id)}>
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}
```

### useNotificationArchive

Custom React hook for managing notification archive operations.

#### Features

- Fetch archived notifications with pagination
- Filter and search notifications
- Restore single or bulk notifications
- Delete notifications permanently
- Loading and error state management
- Refetch capability

#### Return Value

```typescript
{
  // State
  notifications: NotificationItem[];
  isLoading: boolean;
  error: string | null;
  page: number;
  pageSize: number;
  totalCount: number;
  filters: ArchiveFilters;

  // Methods
  setPage: (page: number) => void;
  setFilters: (filters: ArchiveFilters) => void;
  restoreNotification: (id: number) => Promise<NotificationItem>;
  bulkRestore: (ids: number[]) => Promise<{
    restored_count: number;
    not_found: number;
    errors: string[];
  }>;
  deleteNotification: (id: number) => Promise<void>;
  bulkDelete: (ids: number[]) => Promise<void>;
  refetch: () => Promise<void>;
}
```

#### Usage

```tsx
import { useNotificationArchive } from '@/hooks/useNotificationArchive';

function MyComponent() {
  const {
    notifications,
    isLoading,
    restoreNotification,
    deleteNotification,
  } = useNotificationArchive();

  const handleRestore = async (id: number) => {
    try {
      await restoreNotification(id);
      // Success handling
    } catch (err) {
      // Error handling
    }
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      {notifications.map((notif) => (
        <div key={notif.id}>
          {notif.title}
          <button onClick={() => handleRestore(notif.id)}>Restore</button>
        </div>
      ))}
    </div>
  );
}
```

## API Integration

### NotificationCenter API

The NotificationCenter component requires the following API endpoints:

#### GET /api/notifications/

List active notifications with pagination and filtering.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `limit` (int, optional): Items per page (default: 20)
- `search` (string, optional): Search by title or message
- `type` (string, optional): Filter by notification type
- `priority` (string, optional): Filter by priority level
- `is_read` (boolean, optional): Filter by read status

**Response:**
```json
{
  "count": 50,
  "next": "http://api.example.com/api/notifications/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "New Message",
      "message": "You have a new message from John",
      "type": "message_new",
      "priority": "high",
      "created_at": "2025-12-27T10:00:00Z",
      "is_read": false,
      "is_sent": true,
      "sent_at": "2025-12-27T10:00:00Z",
      "read_at": null,
      "data": {}
    }
  ]
}
```

#### GET /api/notifications/unread_count/

Get the count of unread notifications for the current user.

**Response:**
```json
{
  "unread_count": 5
}
```

#### POST /api/notifications/{id}/mark_read/

Mark a single notification as read.

**Request:**
```json
{}
```

**Response:**
```json
{
  "message": "Notification marked as read"
}
```

#### POST /api/notifications/mark_multiple_read/

Mark multiple notifications as read or all notifications at once.

**Request:**
```json
{
  "mark_all": false,
  "notification_ids": [1, 2, 3]
}
```

Or to mark all as read:
```json
{
  "mark_all": true,
  "notification_ids": []
}
```

**Response:**
```json
{
  "message": "Marked as read: 3 notifications"
}
```

#### DELETE /api/notifications/{id}/

Delete a single notification.

**Response:** 204 No Content

#### WebSocket Connection

The component establishes a WebSocket connection for real-time notification updates.

**Connection URL:**
```
ws[s]://[host]/ws/notifications/
```

**Message Format:**
```json
{
  "type": "notification_received",
  "notification": {
    "id": 1,
    "title": "New Message",
    "message": "You have a new message",
    "type": "message_new",
    "priority": "normal",
    "created_at": "2025-12-27T10:00:00Z",
    "is_read": false,
    "is_sent": true
  }
}
```

### NotificationArchive API

The NotificationArchive component requires the following API endpoints:

#### GET /api/notifications/archive/

List archived notifications with pagination and filtering.

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `limit` (int, optional): Items per page (default: 10)
- `search` (string, optional): Search by title or message
- `type` (string, optional): Filter by notification type
- `status` (string, optional): Filter by read/unread status
- `date_from` (string, optional): Filter by created date start
- `date_to` (string, optional): Filter by created date end

**Response:**
```json
{
  "count": 100,
  "next": "http://api.example.com/api/notifications/archive/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "System Update",
      "message": "Your system has been updated",
      "type": "system",
      "priority": "normal",
      "created_at": "2025-12-20T10:00:00Z",
      "archived_at": "2025-12-27T10:00:00Z",
      "is_read": true,
      "data": {}
    }
  ]
}
```

### PATCH /api/notifications/{id}/restore/

Restore an archived notification to the inbox.

**Request:**
```json
{}
```

**Response:**
```json
{
  "id": 1,
  "title": "System Update",
  "message": "Your system has been updated",
  "type": "system",
  "priority": "normal",
  "created_at": "2025-12-20T10:00:00Z",
  "archived_at": null,
  "is_archived": false,
  "is_read": true,
  "data": {}
}
```

### POST /api/notifications/bulk-restore/

Bulk restore multiple archived notifications.

**Request:**
```json
{
  "notification_ids": [1, 2, 3]
}
```

**Response:**
```json
{
  "restored_count": 3,
  "not_found": 0,
  "errors": []
}
```

### DELETE /api/notifications/{id}/

Delete a notification permanently.

**Response:** 204 No Content

## Styling

The component uses Tailwind CSS and shadcn/ui components. All styling is responsive and mobile-friendly.

### Customization

To customize the appearance, you can:

1. **Override Tailwind classes**: Modify the className props in the component
2. **Use CSS modules**: Create a separate CSS module and apply styles
3. **Theme variables**: Adjust via Tailwind CSS theme configuration

### Dark Mode

The component automatically supports dark mode through Tailwind CSS. No additional configuration needed.

## Testing

### Unit Tests

Run component tests:
```bash
npm test -- NotificationArchive.test.tsx
```

Run hook tests:
```bash
npm test -- useNotificationArchive.test.ts
```

### Test Coverage

- Component: 25+ test cases covering all functionality
- Hook: 30+ test cases covering API interactions and state management
- E2E: Manual testing recommended for complex user flows

### Example Test Cases

- Rendering archived notifications
- Filtering and searching
- Sorting options
- Selection (individual and bulk)
- Restore operations (single and bulk)
- Delete operations (single and bulk)
- Pagination
- Error handling
- Loading states
- Modal interactions

## Accessibility

The component includes:

- ARIA labels for screen readers
- Keyboard navigation support
- Focus management
- Semantic HTML structure
- Color contrast compliant
- Skip links for navigation

### Keyboard Shortcuts

- `Tab`: Navigate through elements
- `Space/Enter`: Activate buttons/checkboxes
- `Escape`: Close modal dialogs
- `Arrow keys`: Navigate select dropdowns

## Performance Considerations

1. **Pagination**: Limits data loading to 10 items per page by default
2. **Memoization**: Uses React.useMemo for expensive computations
3. **Lazy Loading**: Table only renders visible rows
4. **Debouncing**: Search input includes debouncing
5. **API Caching**: Consider implementing caching for repeated requests

### Performance Tips

1. Use pagination for large datasets (>1000 items)
2. Implement request debouncing for search
3. Consider infinite scroll for better UX with many items
4. Use React.lazy() for code splitting
5. Monitor API response times

## Error Handling

The component handles various error scenarios:

1. **Network Errors**: Shows retry button
2. **API Errors**: Displays user-friendly error messages
3. **Validation Errors**: Highlights invalid inputs
4. **Permission Errors**: Shows appropriate error messages
5. **Timeout Errors**: Implements automatic retry with exponential backoff

### Error Messages

All error messages are translatable and user-friendly:
- "Failed to load archived notifications"
- "Failed to restore notification"
- "Failed to delete notification"
- Network error messages

## Browser Support

- Chrome/Edge: Latest 2 versions
- Firefox: Latest 2 versions
- Safari: Latest 2 versions
- Mobile: iOS Safari 12+, Chrome Android

## Dependencies

- React 18+
- TypeScript 4.5+
- Tailwind CSS 3+
- shadcn/ui components
- lucide-react (icons)
- sonner (toast notifications)
- React Router (for navigation)

## Migration Guide

### From Other Notification Components

If migrating from another notification archive solution:

1. **API Endpoints**: Ensure your backend implements the required endpoints
2. **Data Format**: Map your notification data to the expected format
3. **Styling**: Adjust Tailwind classes if needed
4. **Hooks**: Replace existing hooks with useNotificationArchive
5. **Testing**: Update test files for your specific use case

## Troubleshooting

### Notifications Not Loading

**Problem**: Component shows "No archived notifications" despite having data

**Solution**:
1. Verify API endpoint is accessible: `/api/notifications/archive/`
2. Check authentication token is being sent
3. Verify user has permission to view archived notifications
4. Check browser console for API errors

### Restore Not Working

**Problem**: Restore button doesn't work or shows error

**Solution**:
1. Verify PATCH endpoint exists: `/api/notifications/{id}/restore/`
2. Check notification is actually archived (is_archived=true)
3. Verify user owns the notification
4. Check network tab for API response

### Styling Issues

**Problem**: Component looks broken or styles not applying

**Solution**:
1. Verify Tailwind CSS is properly configured
2. Check shadcn/ui components are installed
3. Verify lucide-react icons are available
4. Check for CSS conflicts with other components

### Performance Issues

**Problem**: Component is slow or laggy

**Solution**:
1. Reduce page size for pagination
2. Implement virtual scrolling for large lists
3. Add request debouncing for search
4. Check API response times
5. Profile React rendering with DevTools

## Future Enhancements

Potential features for future releases:

- [ ] Virtual scrolling for large lists
- [ ] Export to CSV/PDF
- [ ] Archive scheduling (auto-archive old notifications)
- [ ] Advanced filtering UI
- [ ] Notification categories/tags
- [ ] Archive retention policies
- [ ] Undo/redo for restore/delete
- [ ] Notification templates
- [ ] Analytics dashboard
- [ ] Notification webhooks

## Contributing

To contribute improvements:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

See LICENSE file in the project root.

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review test files for usage examples
3. Check component examples file
4. Open an issue on GitHub
5. Contact development team

## Version History

### v1.0.0 (Current)

Initial release with full functionality:
- Archive listing with pagination
- Search and filtering
- Restore and delete operations
- Bulk operations
- Responsive design
- Comprehensive testing

### Future Versions

- v1.1.0: Virtual scrolling, advanced filtering
- v1.2.0: Export functionality, analytics
- v2.0.0: Redesign with new UI library
