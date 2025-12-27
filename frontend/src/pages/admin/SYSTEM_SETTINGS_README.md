# System Settings Page Documentation

## Overview

The System Settings page (`SystemSettings.tsx`) provides administrators with a centralized interface to manage all platform-wide configuration settings. This page is accessible at `/admin/settings` and is restricted to admin users via the `ProtectedAdminRoute` component.

## Features

### 1. Feature Flags Tab
Manage which features are enabled or disabled across the platform.

**Settings:**
- Assignments Enabled - Allow/disable assignment submission feature
- Payments Enabled - Enable/disable payment processing
- Notifications Enabled - Enable/disable notification system
- Chat Enabled - Enable/disable real-time messaging
- Knowledge Graph Enabled - Enable/disable knowledge graph system

Each feature has:
- Toggle switch for easy on/off control
- Description explaining the feature's purpose
- Last updated timestamp
- Updated by admin name

### 2. Rate Limits Tab
Configure API and authentication rate limiting.

**Settings:**
- API Requests Per Minute (1-1000) - Throttle API access
- Login Attempts Per Minute (1-60) - Limit login attempts
- Brute Force Lockout Duration (1-1440 minutes) - Account lockout duration

**Validation:**
- Number inputs with min/max constraints
- Real-time validation
- Error messages for invalid values

### 3. Email Settings Tab
Configure SMTP for email notifications.

**Settings:**
- SMTP Host - Email server hostname
- SMTP Port (1-65535) - Email server port
- From Address - Sender email address
- Use TLS - Enable/disable TLS encryption

**Features:**
- Test email connection button
- Send test email to verify configuration
- Validation of email format
- Connection status feedback

### 4. Payment Settings Tab
Configure YooKassa payment processing.

**Settings:**
- YooKassa Shop ID - Merchant shop identifier (password-masked)
- YooKassa Enabled - Enable/disable payments
- Supported Payment Methods - Select: Card, Digital Wallet, Bank Transfer
- Currency - Choose: RUB, USD, EUR

**Features:**
- Multiple payment method selection
- Secure password field for sensitive credentials
- Currency dropdown with common options

### 5. Notifications Tab
Configure notification channels and event preferences.

**Notification Channels:**
- Email Notifications
- SMS Notifications
- Push Notifications

**Event Types:**
- Assignment Submissions
- Chat Messages
- Grade Posted
- Schedule Changes

### 6. UI Settings Tab
Customize platform appearance.

**Settings:**
- Company Name - Display name for the platform
- Logo URL - URL to company logo
- Primary Color - Brand color (hex picker + text input)
- Theme - Light, Dark, or Auto

**Features:**
- Color picker with hex validation
- Logo preview
- Theme selection

### 7. Security Settings Tab
Configure security policies and requirements.

**Password Policy:**
- Minimum Password Length (8-20 characters)
- Require Uppercase Letters (toggle)
- Require Numbers (toggle)
- Require Special Characters (toggle)

**Session Management:**
- Session Timeout (5-1440 minutes)

**Additional Security:**
- HTTPS Enforcement
- Require 2FA for Admins

## API Endpoints

### Get All Settings
```
GET /api/admin/config/
Response: {
  feature_flags: {...},
  rate_limits: {...},
  email_settings: {...},
  payment_settings: {...},
  notifications: {...},
  ui_settings: {...},
  security_settings: {...},
  metadata: {...}
}
```

### Get Settings Schema
```
GET /api/admin/config/schema/
Response: Available configuration keys and types
```

### Update Single Setting Group
```
PUT /api/admin/config/{key}/
Body: {...setting values...}
Response: {success: true/false, data: {...}}
```

### Reset to Defaults
```
POST /api/admin/config/reset/
Response: {success: true/false, message: "..."}
```

### Test Email Connection
```
POST /api/admin/config/test-email/
Body: {test_email: "admin@example.com"}
Response: {success: true/false, message: "..."}
```

## Component Architecture

### State Management
- Uses `react-hook-form` for form management
- Separate form instance for each settings group
- Zod schemas for validation
- Unsaved changes warning using `hasChanges` state

### Form Validation
Each form has a Zod schema for type-safe validation:

```typescript
const featureFlagsSchema = z.object({
  assignments_enabled: z.boolean().default(true),
  payments_enabled: z.boolean().default(true),
  // ...
});

const rateLimitsSchema = z.object({
  api_requests_per_minute: z.number().min(1).max(1000),
  // ...
});
```

### Loading & Saving States
- `loading` state shows during initial load
- `saving` state disables buttons during save operations
- Toast notifications for success/error feedback

## Usage Examples

### Accessing the Page
```typescript
import { useNavigate } from 'react-router-dom';

const navigate = useNavigate();
navigate('/admin/settings');
```

### Testing Settings Changes
```typescript
// Test disabling a feature
const assignmentsToggle = screen.getByRole('switch', {
  name: /Assignments Enabled/i,
});
await userEvent.click(assignmentsToggle);

// Save changes
const saveButton = screen.getByRole('button', { name: /Save Changes/i });
await userEvent.click(saveButton);
```

## Validation Rules

### Feature Flags
- All booleans, no additional validation

### Rate Limits
- API Requests: 1-1000 (number)
- Login Attempts: 1-60 (number)
- Lockout Duration: 1-1440 (number)

### Email Settings
- SMTP Host: Required, non-empty string
- SMTP Port: 1-65535 (number)
- From Address: Valid email format
- Use TLS: Boolean

### Payment Settings
- Shop ID: Required, non-empty string
- Enabled: Boolean
- Payment Methods: Array of strings
- Currency: Enum (RUB, USD, EUR)

### Notifications
- All settings: Boolean or checkbox arrays

### UI Settings
- Company Name: Required, non-empty string
- Logo URL: Valid URL or empty
- Primary Color: Hex format (#RRGGBB)
- Theme: Enum (light, dark, auto)

### Security Settings
- Password Length: 8-20 (number)
- Session Timeout: 5-1440 (number)
- All others: Boolean

## Error Handling

The component includes comprehensive error handling:

```typescript
// API errors
try {
  const response = await unifiedAPI.request('/admin/config/');
  if (response.success) {
    // Update forms
  } else {
    toast.error('Failed to load settings');
  }
} catch (error) {
  logger.error('[SystemSettings] Failed to load settings:', error);
  toast.error('Failed to load settings');
}
```

## Testing

### Unit Tests
- `SystemSettings.test.tsx` - Component tests
- Tests for each tab
- Validation tests
- Save/load functionality
- Error handling

### Integration Tests
- `SystemSettings.integration.test.tsx` - Full workflow tests
- Multi-tab navigation
- Multiple saves
- Error recovery
- Responsive design tests

### Test Coverage
- All setting types tested
- Validation tested
- Save/reset operations
- Error scenarios
- Responsive design

## Responsive Design

The component is fully responsive:

```typescript
// Tabs with responsive grid
<TabsList className="grid w-full grid-cols-4 lg:grid-cols-7">
  {/* Tab triggers with responsive text */}
  <TabsTrigger className="text-xs sm:text-sm">
    <Flag className="h-4 w-4 mr-2" />
    <span className="hidden sm:inline">Features</span>
  </TabsTrigger>
</TabsList>
```

## Browser Support

- Chrome/Edge: Full support
- Firefox: Full support
- Safari: Full support
- Mobile browsers: Responsive design

## Performance Optimizations

1. **Lazy Form Loading**: Forms loaded on tab switch
2. **Debounced Saves**: Prevent duplicate API calls
3. **Toast Notifications**: Non-blocking feedback
4. **Form Validation**: Client-side before API call

## Security Considerations

1. **Password Fields**: Sensitive values use `type="password"`
2. **CSRF Protection**: Handled by backend
3. **Rate Limiting**: Can be configured per platform needs
4. **Admin-Only Access**: Protected by `ProtectedAdminRoute`
5. **Validation**: Both client and server-side

## Troubleshooting

### Settings not loading
- Check API endpoint: `/admin/config/`
- Verify admin permissions
- Check network tab for errors

### Save fails silently
- Check browser console for errors
- Verify form validation passed
- Check API response status

### Toast notifications not showing
- Verify `sonner` toast provider in layout
- Check toast implementation

## Future Enhancements

1. **Settings History**: Track all changes with timestamps
2. **Bulk Operations**: Apply changes to multiple settings
3. **Settings Export**: Export current configuration
4. **Settings Import**: Import from JSON file
5. **Audit Logging**: Log all settings changes
6. **Scheduled Changes**: Schedule settings changes for future time
7. **A/B Testing**: Test different settings configurations
8. **Performance Monitoring**: Monitor impact of settings changes

## Related Documentation

- [API_GUIDE.md](../../docs/API_GUIDE.md) - API usage guide
- [API_ENDPOINTS.md](../../docs/API_ENDPOINTS.md) - Complete endpoint reference
- [ADMIN_PANEL.md](../../docs/ADMIN_PANEL.md) - Admin panel documentation
- [CLAUDE.md](../../CLAUDE.md) - Project configuration

## Support

For issues or questions:
1. Check this documentation
2. Review test files for usage examples
3. Check backend API logs
4. Open issue with error details
