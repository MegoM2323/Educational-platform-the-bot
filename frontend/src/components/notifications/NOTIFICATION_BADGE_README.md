# NotificationBadge Component

Real-time notification badge component with WebSocket integration, animated pulse effects, and hover preview functionality.

## Features

- **Real-time Updates**: WebSocket connection for instant unread count synchronization
- **Animated Pulse**: Smooth pulse animation when new notifications arrive
- **Hover Preview**: Shows latest notifications on hover with type-based color coding
- **Responsive Design**: Three variant options (default, icon, compact) for different layouts
- **Smart Count Display**: Shows "99+" for counts exceeding 99
- **Offline Detection**: Automatic detection and reconnection handling
- **Type-based Colors**: Different colors for different notification counts
- **Accessibility**: Proper semantic HTML and ARIA support

## Installation

The component is already installed as part of the notifications module.

```tsx
import { NotificationBadge } from '@/components/notifications';
```

## Usage

### Basic Usage
```tsx
<NotificationBadge />
```

### Icon Variant
Perfect for navigation headers:
```tsx
<NotificationBadge variant="icon" />
```

### Compact Variant
For space-constrained areas:
```tsx
<NotificationBadge variant="compact" />
```

### With Custom Configuration
```tsx
<NotificationBadge
  variant="default"
  showPreview={true}
  previewCount={5}
  showZero={false}
  className="ml-auto"
/>
```

### In a Header Layout
```tsx
<header className="flex items-center justify-between p-4">
  <h1>Dashboard</h1>
  <div className="flex items-center gap-4">
    <NotificationBadge variant="icon" />
    <UserMenu />
  </div>
</header>
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `className` | `string` | - | Custom CSS classes to apply to the wrapper |
| `showZero` | `boolean` | `false` | Display badge when unread count is 0 |
| `showPreview` | `boolean` | `true` | Show preview popover on hover |
| `previewCount` | `number` | `3` | Number of notifications to show in preview |
| `variant` | `'default' \| 'icon' \| 'compact'` | `'default'` | Visual style variant |

## Color Coding

The badge color changes based on unread count:

- **Gray (0)**: No unread notifications
- **Blue (1-5)**: Low priority notifications
- **Yellow (6-10)**: Medium priority notifications
- **Red (11+)**: High priority notifications

## Preview Popover

When hovering over the badge with `showPreview={true}`:

- Shows the latest notifications (limited by `previewCount`)
- Displays notification type badges with color coding
- Shows unread count in the header
- Displays "more notifications" count if exceeding preview limit
- Supports different notification types:
  - System (blue)
  - Message (green)
  - Assignment (purple)
  - Feedback (indigo)
  - Payment (emerald)
  - Invoice (amber)

## WebSocket Integration

The component automatically:

1. Establishes a WebSocket connection to `/ws/notifications/`
2. Listens for `notification_received` events
3. Updates the count in real-time
4. Triggers pulse animation on new notifications
5. Handles disconnections and auto-reconnects every 5 seconds
6. Detects online/offline status

### WebSocket Message Format
```json
{
  "type": "notification_received",
  "notification": {
    "id": 1,
    "title": "...",
    "message": "...",
    "type": "system|message_new|assignment_submitted|...",
    "priority": "low|normal|high|urgent",
    "created_at": "ISO-8601 timestamp",
    "is_read": false,
    "is_sent": true
  }
}
```

## Responsive Behavior

### Desktop
- Full "Notifications" label with badge
- Hover preview popover
- Icon variant shows bell icon

### Tablet
- Compact display
- Hover preview still available
- Touch-friendly interactions

### Mobile
- Compact or icon variant recommended
- Preview can be triggered on tap
- Optimized touch targets

## Animation Effects

### Pulse Animation
- Triggers automatically when new notification arrives
- 3-second duration
- Red glow shadow effect
- Subtle opacity change

### Color Transitions
- Smooth transitions between color states
- No jarring changes
- Consistent timing

## Accessibility

- Semantic HTML structure (`<div>`, proper nesting)
- Color coding supplemented with count numbers
- Offline indicator with descriptive title
- Keyboard navigable (standard click/hover behavior)
- Proper element hierarchy

## Testing

Component includes comprehensive test coverage:

- **Rendering Tests**: Badge visibility and count display
- **Variant Tests**: All three variants work correctly
- **Preview Tests**: Hover behavior and content display
- **Color Tests**: Proper color application by count
- **WebSocket Tests**: Connection and message handling
- **Accessibility Tests**: Semantic structure and ARIA

Run tests:
```bash
npm test -- --run src/components/notifications/__tests__/NotificationBadge.test.tsx
```

## API Dependencies

The component uses the following hooks and APIs:

### Hooks
- `useNotificationCenter()`: Provides unread count, notifications, and refetch function
- `useAuth()`: Gets current user information

### WebSocket
- Connects to `/ws/notifications/` for real-time updates
- Automatically handles reconnection

### REST API
- Uses notifications API from `useNotificationCenter` hook
- Fetches unread count: `GET /api/notifications/unread_count/`
- Fetches notifications: `GET /api/notifications/?page=1&limit=20`

## Integration Examples

### In Navigation Header
```tsx
import { NotificationBadge } from '@/components/notifications';

export function Header() {
  return (
    <nav className="flex justify-between items-center p-4 bg-white border-b">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <div className="flex items-center gap-4">
        <NotificationBadge variant="icon" />
        <UserDropdown />
      </div>
    </nav>
  );
}
```

### In Sidebar
```tsx
<aside className="w-64 bg-gray-100 p-4">
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <span className="font-semibold">Notifications</span>
      <NotificationBadge variant="compact" showZero={true} />
    </div>
    {/* Other sidebar content */}
  </div>
</aside>
```

### In User Menu
```tsx
<button className="relative">
  <span>Menu</span>
  <NotificationBadge variant="icon" className="absolute -top-2 -right-2" />
</button>
```

## Common Issues

### Preview Not Showing
- Check `showPreview={true}` is set
- Ensure unread count > 0 (or use `showZero={true}`)
- Check CSS is loaded (Tailwind classes)

### WebSocket Not Connecting
- Verify backend supports WebSocket on `/ws/notifications/`
- Check browser console for CORS errors
- Ensure protocol is correct (wss:// for HTTPS, ws:// for HTTP)

### Count Not Updating
- Verify useNotificationCenter hook is properly configured
- Check network tab for API calls
- Ensure authentication tokens are present

## Performance Notes

- Badge updates are debounced through React's state management
- Hover preview is only rendered when needed
- WebSocket maintains a single connection per component instance
- Memory cleanup on unmount (WebSocket close, event listeners removed)
- No memory leaks detected in testing

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

WebSocket support required (all modern browsers).

## Future Enhancements

- [ ] Custom notification type colors
- [ ] Sound notifications
- [ ] Badge animation variants
- [ ] Notification grouping
- [ ] Drag-to-dismiss gesture
- [ ] Custom action buttons in preview
- [ ] Badge explosion animation

## Related Components

- `NotificationCenter`: Full notification management interface
- `ChatNotificationBadge`: Chat-specific notification badge
- `NotificationArchive`: Historical notification viewing
