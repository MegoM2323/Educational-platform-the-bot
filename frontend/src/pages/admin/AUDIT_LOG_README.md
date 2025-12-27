# Audit Log Viewer - Admin Page

## Overview

The Audit Log Viewer is an admin-only page for viewing system audit trails and tracking admin actions across the platform. It provides comprehensive filtering, sorting, pagination, and export capabilities to help administrators monitor and analyze system activity.

## Features

### Core Features
- **Table Display**: Shows audit logs with timestamp, user, action, resource, status, and IP address
- **Filtering**: Multiple filter options for precise data exploration
- **Sorting**: Default sort by timestamp (newest first)
- **Pagination**: 50 rows per page with navigation controls
- **Search**: Full-text search in log details
- **Expandable Rows**: Click to expand for additional details (IP, user agent, duration, old/new values)
- **CSV Export**: Export filtered logs to CSV file
- **Real-time Refresh**: Auto-refresh every 30 seconds (optional)
- **Responsive Design**: Mobile, tablet, and desktop layouts

### Filter Options

1. **User Filter**: Dropdown to select specific users
2. **Action Filter**: Filter by action type (create, read, update, delete, export, login, logout)
3. **Resource Filter**: Filter by resource type (User, Material, Assignment, ChatRoom, Message, Payment)
4. **Status Filter**: Filter by success or failed status
5. **Date Range**: Start and end dates for log filtering
6. **Full-text Search**: Search in log details field

### Table Columns

| Column | Description | Type |
|--------|-------------|------|
| Timestamp | When the action occurred (ISO format, sortable) | datetime |
| User | Email and full name of user who performed action | text |
| Action | Type of action (create/read/update/delete/export/login/logout) | enum |
| Resource | Type of resource affected (User/Material/Assignment/etc) | text |
| Status | Success or failed status of the action | enum |
| IP Address | IP address from which action was performed | text |
| Details | Truncated details/description of the action | text |

### Expandable Row Details

When expanding a row, the following additional information is displayed:

```json
{
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "duration_ms": 245,
  "old_values": {...},
  "new_values": {...}
}
```

### Details Modal

Click "View full details (JSON)" to open a modal with complete JSON representation of:
- Timestamp
- User information
- Action and resource type
- Status
- IP address and user agent
- Duration (ms)
- Old values (for updates)
- New values (for updates)

## Implementation Files

### Main Component
**File**: `frontend/src/pages/admin/AuditLog.tsx`

Main React component implementing the audit log viewer UI with all features.

**Key Exports**:
- `AuditLog` - Main component (default export)
- `DetailsPanel` - Expandable row details
- `DetailsModal` - Full details modal
- `Tooltip` - Simple tooltip component

### API Integration
**File**: `frontend/src/integrations/api/adminAPI.ts`

API methods for audit log operations:

```typescript
// Get audit logs with filters and pagination
adminAPI.getAuditLogs({
  user_id?: number;
  action?: string;
  resource?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
  format?: string; // 'csv' for CSV export
})

// Get single audit log details
adminAPI.getAuditLogDetail(logId: number)

// Get audit log statistics
adminAPI.getAuditLogStats()
```

### Custom Hook
**File**: `frontend/src/hooks/useAuditLogs.ts`

Custom React hooks for audit log management:

```typescript
// Main hook for audit log operations
const {
  logs,
  isLoading,
  error,
  totalCount,
  currentPage,
  pageSize,
  fetchLogs,
  fetchLogDetails,
  exportToCSV,
  clearError,
} = useAuditLogs(pageSize?: number)

// Hook for loading users for filter dropdown
const {
  users,
  isLoading,
  error,
  fetchUsers,
} = useAuditLogUsers()
```

### Tests
**Files**:
- `frontend/src/pages/admin/__tests__/AuditLog.test.tsx` - Unit tests
- `frontend/src/pages/admin/__tests__/AuditLog.integration.test.tsx` - Integration tests

## Usage

### Basic Import and Usage

```tsx
import AuditLog from '@/pages/admin/AuditLog';

function AdminPanel() {
  return <AuditLog />;
}
```

### Using the Custom Hook

```tsx
import { useAuditLogs, useAuditLogUsers } from '@/hooks/useAuditLogs';

function MyComponent() {
  const { logs, isLoading, error, fetchLogs } = useAuditLogs(50);
  const { users, fetchUsers } = useAuditLogUsers();

  useEffect(() => {
    fetchLogs(1, {
      action: 'create',
      status: 'failed',
    });
    fetchUsers();
  }, []);

  return (
    <div>
      {isLoading && <div>Loading...</div>}
      {error && <div>Error: {error}</div>}
      {logs.map((log) => (
        <div key={log.id}>{log.action} on {log.resource}</div>
      ))}
    </div>
  );
}
```

## API Endpoints

The component expects the following backend endpoints:

### List Audit Logs
```
GET /api/admin/audit-logs/
Query Parameters:
- page: number (default: 1)
- page_size: number (default: 50)
- user_id: number (optional)
- action: string (optional)
- resource: string (optional)
- status: string (optional)
- date_from: string (YYYY-MM-DD, optional)
- date_to: string (YYYY-MM-DD, optional)
- search: string (optional)
- ordering: string (default: '-timestamp')
- format: string ('csv' for CSV export)

Response:
{
  count: number,
  next: string | null,
  previous: string | null,
  results: AuditLogEntry[]
}
```

### Get Audit Log Details
```
GET /api/admin/audit-logs/{id}/

Response:
{
  id: number,
  timestamp: string,
  user: {...},
  action: string,
  resource: string,
  status: string,
  ip_address: string,
  user_agent?: string,
  duration_ms?: number,
  old_values?: object,
  new_values?: object,
  details?: string
}
```

### Get Audit Log Statistics
```
GET /api/admin/audit-logs/stats/

Response:
{
  success: boolean,
  data: {
    total_logs: number,
    today_logs: number,
    failed_actions: number,
    unique_users: number,
    most_active_action: string,
    most_active_resource: string
  }
}
```

## Type Definitions

```typescript
interface AuditLogEntry {
  id: number;
  timestamp: string; // ISO format
  user: {
    id: number;
    email: string;
    full_name: string;
  };
  action: 'create' | 'read' | 'update' | 'delete' | 'export' | 'login' | 'logout';
  resource: 'User' | 'Material' | 'Assignment' | 'ChatRoom' | 'Message' | 'Payment' | string;
  status: 'success' | 'failed';
  ip_address: string;
  user_agent?: string;
  duration_ms?: number;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  details?: string;
}

interface AuditLogFilters {
  user_id?: number;
  action?: string;
  resource?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
}
```

## Styling

The component uses:
- **Tailwind CSS** for layout and responsive design
- **shadcn/ui** components for UI elements (Table, Button, Input, Label, Badge, etc.)
- **Lucide React** for icons
- **Sonner** for toast notifications

### Responsive Breakpoints

- **Mobile** (< 768px): Single column layout, horizontal scroll table
- **Tablet** (768px - 1024px): Two-column filter grid
- **Desktop** (> 1024px): Three-column filter grid

## Features in Detail

### Auto-Refresh
- Enabled by default, updates every 30 seconds
- Can be toggled on/off with checkbox
- Respects current filter state

### CSV Export
- Exports all matching logs (up to 10,000)
- Respects current filters
- Downloads as `audit-logs-YYYY-MM-DD.csv`

### Error Handling
- Network errors shown in error card with retry button
- Toast notifications for user feedback
- Logging via logger utility for debugging

### Loading States
- Loading spinner during data fetch
- Disabled pagination buttons while loading
- Disabled export button with no logs

### Empty State
- Shows "No audit logs found" message
- Displays option to clear filters if active filters applied

## Testing

### Run Unit Tests
```bash
npm test -- src/pages/admin/__tests__/AuditLog.test.tsx
```

### Run Integration Tests
```bash
npm test -- src/pages/admin/__tests__/AuditLog.integration.test.tsx
```

### Test Coverage
- Filtering functionality
- Sorting and pagination
- CSV export
- Expandable rows
- Details modal
- Error handling
- Refresh functionality
- Responsive design
- Accessibility

## Performance Considerations

1. **Pagination**: Default 50 rows per page limits DOM nodes
2. **Virtualization**: Consider for large datasets (>1000 rows)
3. **Caching**: Consider memoization for expensive computations
4. **Network**: Auto-refresh can be disabled for high-traffic scenarios

## Accessibility

The component includes:
- Proper semantic HTML (table, heading hierarchy)
- ARIA labels on all inputs
- Keyboard navigation support
- Focus management
- Color contrast compliance (WCAG AA)
- Screen reader friendly
- Tooltip descriptions for IP addresses

## Future Enhancements

1. **Advanced Analytics**: Charts showing action trends over time
2. **Real-time Updates**: WebSocket integration for live updates
3. **Report Generation**: Scheduled email reports
4. **User Activity Timeline**: Visual timeline of user actions
5. **Geolocation**: Display geolocation for IP addresses
6. **Bulk Actions**: Select multiple logs for batch operations
7. **Custom Alerts**: Set up alerts for specific action types
8. **Audit Log Retention**: Configurable retention policies

## Security Considerations

1. **Authentication**: Requires admin role
2. **Authorization**: Backend enforces permissions
3. **Data Sensitivity**: Logs may contain sensitive information
4. **Export**: CSV files should be handled securely
5. **Rate Limiting**: Consider rate limiting on log endpoint

## Troubleshooting

### Logs not loading
- Check network connection
- Verify admin permissions
- Check backend API availability
- Review console errors

### Filters not working
- Clear browser cache
- Verify filter values are correct
- Check date format (YYYY-MM-DD)
- Review network requests

### Export failing
- Check file permissions
- Verify CSV format is supported
- Check available disk space
- Review browser console

## Related Documentation

- [Admin Dashboard](./AdminDashboard.tsx)
- [API Guide](/docs/API_GUIDE.md)
- [Admin API Endpoints](/docs/API_ENDPOINTS.md#admin-endpoints)
- [Security Best Practices](/docs/SECURITY.md)
