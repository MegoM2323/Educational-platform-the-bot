# T_NOTIF_008B: Notification Analytics Frontend - Quick Reference

## Component Location
- **Main Component**: `frontend/src/pages/admin/NotificationAnalytics.tsx`
- **Route**: `/admin/notifications`
- **Menu Item**: "Аналитика уведомлений" in Admin Sidebar

## Quick Start

### View the Dashboard
```bash
# Navigate to
http://localhost:8080/admin/notifications

# Or click on "Аналитика уведомлений" in the admin sidebar
```

### Import in Other Components
```tsx
import NotificationAnalytics from '@/pages/admin/NotificationAnalytics';
// OR directly access at /admin/notifications
```

## Key Files

| File | Purpose |
|------|---------|
| `NotificationAnalytics.tsx` | Main dashboard component (21.4 KB) |
| `notificationsAPI.ts` | API client for analytics endpoints |
| `useNotificationAnalytics.ts` | React Query hooks for data fetching |
| `App.tsx` | Route configuration |
| `AdminSidebar.tsx` | Menu navigation |

## API Endpoints

All require admin authentication (`is_staff=True`)

```
GET /api/notifications/analytics/metrics/
  ?date_from=2025-12-20
  &date_to=2025-12-27
  &granularity=day
  &channel=email
  &type=assignment_new

GET /api/notifications/analytics/performance/
  ?date_from=2025-12-20
  &date_to=2025-12-27

GET /api/notifications/analytics/top-types/
  ?date_from=2025-12-20
  &date_to=2025-12-27
  &limit=5
```

## Component Props

The component accepts no props (uses route context and admin authentication)

## State Management

Uses React Query with these query keys:
- `notificationMetrics` - Main metrics data
- `channelPerformance` - Channel breakdown
- `topNotificationTypes` - Top performing types

## Custom Hooks

### useNotificationMetrics
```tsx
const { data, isLoading, error } = useNotificationMetrics(filters);
```

### useChannelPerformance
```tsx
const { data, isLoading, error } = useChannelPerformance(filters);
```

### useTopNotificationTypes
```tsx
const { data, isLoading, error } = useTopNotificationTypes(filters);
```

### useAllNotificationAnalytics (Combined)
```tsx
const { metrics, channelPerformance, topTypes, isLoading, error, refetch } =
  useAllNotificationAnalytics(filters);
```

## Filter Interface

```typescript
interface AnalyticsQueryParams {
  date_from?: string;      // YYYY-MM-DD format
  date_to?: string;        // YYYY-MM-DD format
  type?: string;           // notification type
  channel?: string;        // 'email' | 'push' | 'sms' | 'in_app'
  granularity?: 'hour' | 'day' | 'week';
  limit?: number;
}
```

## Default Filters

```typescript
{
  date_from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  date_to: new Date().toISOString().split('T')[0],
  granularity: 'day'
}
```

## Response Types

### NotificationAnalyticsResponse
```typescript
{
  date_from: string;
  date_to: string;
  total_sent: number;
  total_delivered: number;
  total_opened: number;
  delivery_rate: number;
  open_rate: number;
  by_type: Record<string, TypeMetrics>;
  by_channel: Record<string, ChannelMetrics>;
  by_time: TimeMetricsItem[];
  summary: SummaryMetrics;
}
```

### ChannelPerformanceResponse
```typescript
{
  channels: ChannelPerformance[];
  best_channel: ChannelPerformance | null;
  worst_channel: ChannelPerformance | null;
}
```

### TopTypesResponse
```typescript
{
  top_types: TopPerformingType[];
}
```

## Color Scheme

| Purpose | Color | Hex |
|---------|-------|-----|
| Primary | Blue | #3b82f6 |
| Success | Green | #10b981 |
| Warning | Amber | #f59e0b |
| Danger | Red | #ef4444 |
| Secondary | Purple | #8b5cf6 |
| Tertiary | Pink | #ec4899 |

## Channel Colors

```typescript
{
  email: '#3b82f6',      // Blue
  push: '#10b981',       // Green
  sms: '#f59e0b',        // Amber
  in_app: '#8b5cf6'      // Purple
}
```

## Chart Types Used

1. **LineChart**: Time series data (sent, processed, opened)
2. **BarChart**: Channel performance comparison
3. **PieChart**: Top notification types distribution

## Common Issues & Solutions

### No data showing?
1. Verify date range has notifications
2. Check admin permissions (`is_staff=True`)
3. Verify backend endpoints are returning data
4. Check browser console for API errors

### Charts not rendering?
1. Verify Recharts is installed
2. Check data format matches expected structure
3. Ensure ResponsiveContainer has parent with width

### Slow performance?
1. Reduce date range
2. Use daily granularity instead of hourly
3. Check backend query performance
4. Monitor React Query cache size

## Testing

### Manual Test Cases

1. **Load Dashboard**
   - Navigate to `/admin/notifications`
   - Verify charts load with data
   - Check metric cards display correctly

2. **Filter Testing**
   - Change date range
   - Switch granularity (hour/day/week)
   - Filter by channel
   - Click Apply and Reset buttons

3. **Responsiveness**
   - Test on mobile (< 768px)
   - Test on tablet (768-1024px)
   - Test on desktop (> 1024px)

4. **Error Handling**
   - Disconnect network (check error message)
   - Use invalid date range
   - Test with no data period

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance Metrics

- Initial load: < 2 seconds
- Chart render: < 500ms
- Filter apply: < 1 second
- Bundle size: ~25KB (gzipped)

## Troubleshooting Commands

```bash
# Check if component builds
cd frontend && npm run build

# Run dev server with notifications route
npm run dev

# Check TypeScript errors
npx tsc --noEmit

# View browser console for API calls
# DevTools > Network tab > filter by /api/notifications/
```

## Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] CSV/PDF export
- [ ] User segmentation filters
- [ ] Alerts for performance drops
- [ ] A/B test comparison
- [ ] Custom date range presets
- [ ] Drill-down capabilities
- [ ] Week-over-week/month-over-month comparison

## Related Tasks

- **T_NOTIF_008A**: Backend analytics implementation
- **T_NOTIF_007**: Notification system core features
- **T_ADMIN_001**: Admin panel framework

## Support

For issues or questions:
1. Check FEEDBACK_T_NOTIF_008B.md for detailed documentation
2. Review component JSDoc comments
3. Check API responses in Network tab
4. Verify backend endpoints are accessible
5. Check admin user permissions

---

**Version**: 1.0.0
**Last Updated**: December 27, 2025
