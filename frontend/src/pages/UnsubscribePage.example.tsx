/**
 * UnsubscribePage Component Examples
 *
 * This file demonstrates usage patterns for the UnsubscribePage component.
 * The component provides a token-based unsubscribe mechanism for email notifications.
 */

import { UnsubscribePage } from './UnsubscribePage';

/**
 * Example 1: Basic Usage
 *
 * The UnsubscribePage is designed to be used as a standalone route that
 * users access via email links. No props are needed.
 *
 * Router Setup:
 * ```tsx
 * import { UnsubscribePage } from '@/pages/UnsubscribePage';
 *
 * const router = createBrowserRouter([
 *   {
 *     path: '/unsubscribe',
 *     element: <UnsubscribePage />,
 *   },
 * ]);
 * ```
 *
 * Email Link Example:
 * ```
 * Click here to unsubscribe from notifications:
 * https://example.com/unsubscribe?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
 * ```
 */
export const Example1_BasicUsage = () => <UnsubscribePage />;

/**
 * Example 2: Token Validation
 *
 * The component automatically validates the token from the URL parameters.
 *
 * Token Format:
 * - Location: URL query parameter ?token=...
 * - Type: Base64url-encoded JWT
 * - Expiry: 30 days from generation
 * - Signature: HMAC-SHA256 using Django SECRET_KEY
 *
 * Backend Token Generation:
 * ```python
 * from notifications.unsubscribe import UnsubscribeTokenGenerator
 *
 * token = UnsubscribeTokenGenerator.generate(
 *     user_id=123,
 *     notification_types=['assignments', 'materials']
 * )
 * # token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
 *
 * # Validate token
 * is_valid, data = UnsubscribeTokenGenerator.validate(token)
 * if is_valid:
 *     print(f"Valid token for user {data['user_id']}")
 *     print(f"Notification types: {data['notification_types']}")
 * ```
 */
export const Example2_TokenValidation = () => (
  <div>
    <p>Token is validated automatically on page load.</p>
    <p>If token is missing or invalid, an error page is displayed.</p>
    <UnsubscribePage />
  </div>
);

/**
 * Example 3: User Flows
 *
 * The component supports three main user flows:
 *
 * Flow 1: Unsubscribe from All
 * - User checks "Unsubscribe from All Notifications"
 * - Individual selections are hidden
 * - POST /api/notifications/unsubscribe/ with unsubscribe_from=['all']
 * - Success page shows confirmation
 *
 * Flow 2: Selective Channel Unsubscribe
 * - User selects channels (email, SMS, push)
 * - POST /api/notifications/unsubscribe/ with channels=['email', 'sms']
 * - Settings update to disable selected channels
 *
 * Flow 3: Selective Type Unsubscribe
 * - User selects types (assignments, materials, messages)
 * - POST /api/notifications/unsubscribe/ with unsubscribe_from=['assignments']
 * - Settings update to disable selected types
 */
export const Example3_UserFlows = () => (
  <div>
    <h2>User Flows</h2>
    <ol>
      <li>
        <strong>Unsubscribe from All:</strong>
        <br />
        Check "Unsubscribe from All Notifications" → Confirm
      </li>
      <li>
        <strong>Selective Unsubscribe:</strong>
        <br />
        Check individual channels/types → Confirm
      </li>
      <li>
        <strong>Cancel and Return:</strong>
        <br />
        Click "Cancel" to return home without changes
      </li>
    </ol>
    <UnsubscribePage />
  </div>
);

/**
 * Example 4: API Request/Response
 *
 * The component makes a POST request to the backend unsubscribe endpoint.
 *
 * Request Format:
 * ```typescript
 * interface UnsubscribeRequest {
 *   token: string;                    // Token from URL
 *   unsubscribe_from: string[];       // Types: ['assignments', 'all', etc]
 *   channels?: string[];               // Optional: ['email', 'sms', 'push']
 * }
 *
 * // Example payload for unsubscribing from assignments via email
 * {
 *   token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
 *   unsubscribe_from: ['assignments'],
 *   channels: ['email']
 * }
 * ```
 *
 * Response Format:
 * ```typescript
 * interface UnsubscribeResponse {
 *   success: boolean;
 *   message: string;
 *   disabled_types?: string[];   // Types that were disabled
 *   user_email?: string;          // User's email for confirmation
 * }
 *
 * // Example successful response
 * {
 *   success: true,
 *   message: 'Successfully unsubscribed from: assignments',
 *   disabled_types: ['assignments'],
 *   user_email: 'john@example.com'
 * }
 * ```
 */
export const Example4_ApiRequestResponse = () => (
  <div>
    <h2>API Request/Response</h2>
    <p>POST /api/notifications/unsubscribe/</p>
    <p>Endpoint validates token and updates NotificationSettings</p>
    <UnsubscribePage />
  </div>
);

/**
 * Example 5: Error Handling
 *
 * The component handles multiple error scenarios:
 *
 * 1. Missing Token:
 *    - URL has no ?token= parameter
 *    - Display: "No unsubscribe token provided"
 *    - User can return to home
 *
 * 2. Invalid Token:
 *    - Token signature verification failed
 *    - Token is corrupted or tampered
 *    - Display: "Unsubscribe link invalid"
 *
 * 3. Expired Token:
 *    - Token is older than 30 days
 *    - Display: "The link may be expired or invalid"
 *    - User can log in and change settings manually
 *
 * 4. User Not Found:
 *    - Token valid but user deleted or deactivated
 *    - Display: "User not found"
 *
 * 5. API Error:
 *    - Network error during submission
 *    - Display: Error message from backend
 *    - User can retry
 */
export const Example5_ErrorHandling = () => (
  <div>
    <h2>Error Scenarios</h2>
    <ul>
      <li>Missing token → Error page with helpful info</li>
      <li>Invalid/expired token → Error page suggesting login</li>
      <li>Network error → Error display with retry option</li>
      <li>Validation error → Form-level error message</li>
    </ul>
    <UnsubscribePage />
  </div>
);

/**
 * Example 6: Email Template Integration
 *
 * The component is typically accessed via email links generated by the backend.
 *
 * Email Template Example (Django template):
 * ```html
 * <body>
 *   <h1>Hello {{ user.first_name }}!</h1>
 *
 *   <!-- Email content -->
 *   <p>You have received an assignment: {{ assignment.title }}</p>
 *
 *   <!-- Footer with unsubscribe link -->
 *   <footer>
 *     <hr>
 *     <p style="font-size: 12px; color: #666;">
 *       Don't want to receive these emails?
 *       <a href="{{ unsubscribe_url }}">Click here to manage your notification preferences</a>
 *     </p>
 *     <p style="font-size: 12px; color: #999;">
 *       This link is valid for 30 days. After that, you can manage preferences in your account settings.
 *     </p>
 *   </footer>
 * </body>
 * ```
 *
 * Backend Code to Generate Link:
 * ```python
 * from notifications.unsubscribe import generate_unsubscribe_token, get_unsubscribe_url
 *
 * # In notification service
 * token = generate_unsubscribe_token(user_id=user.id)
 * unsubscribe_url = get_unsubscribe_url(token)
 *
 * # Pass to email template
 * context = {
 *     'user': user,
 *     'assignment': assignment,
 *     'unsubscribe_url': unsubscribe_url,
 * }
 * ```
 */
export const Example6_EmailIntegration = () => (
  <div>
    <h2>Email Integration</h2>
    <p>Generated link format:</p>
    <code>https://example.com/unsubscribe?token=eyJ...</code>
    <p>User clicks link in email → UnsubscribePage loads → User can unsubscribe</p>
    <UnsubscribePage />
  </div>
);

/**
 * Example 7: State Management
 *
 * Component manages the following state:
 *
 * Loading States:
 * - Initial page load: Shows spinner while loading
 * - Submission: Shows "Updating..." with disabled button
 * - Success: Shows success page with email confirmation
 *
 * Selection State:
 * - selectedChannels: Array of selected channel IDs
 * - selectedTypes: Array of selected notification type IDs
 * - unsubscribeFromAll: Boolean flag for "unsubscribe all" option
 *
 * Error State:
 * - loadError: Error while validating token
 * - submitError: Error while submitting unsubscribe request
 */
export const Example7_StateManagement = () => (
  <div>
    <h2>State Management</h2>
    <p>Form state:</p>
    <ul>
      <li>selectedChannels: string[]</li>
      <li>selectedTypes: string[]</li>
      <li>unsubscribeFromAll: boolean</li>
      <li>isLoading: boolean (token validation)</li>
      <li>isSubmitting: boolean (form submission)</li>
      <li>success: boolean (completion status)</li>
    </ul>
    <UnsubscribePage />
  </div>
);

/**
 * Example 8: Responsive Design
 *
 * The component is fully responsive:
 *
 * Desktop (1024px+):
 * - 2-column grid for notification types
 * - Full-width form layout
 * - Horizontal button layout
 *
 * Tablet (768px+):
 * - Responsive grid adjustments
 * - Touch-friendly checkbox sizing
 * - Readable font sizes
 *
 * Mobile (< 768px):
 * - Single-column layout
 * - Full-width buttons
 * - Larger touch targets
 * - Optimized padding and spacing
 *
 * Features:
 * - No horizontal scroll
 * - Readable text at all sizes
 * - Touch-friendly controls
 * - Proper spacing on small screens
 */
export const Example8_ResponsiveDesign = () => (
  <div>
    <h2>Responsive Design</h2>
    <p>Desktop: 2-column layout</p>
    <p>Tablet: Responsive grid</p>
    <p>Mobile: Single-column layout</p>
    <UnsubscribePage />
  </div>
);

/**
 * Example 9: Accessibility Features
 *
 * The component includes accessibility features:
 *
 * - Semantic HTML: proper heading hierarchy, labels linked to inputs
 * - ARIA: roles, labels for screen readers
 * - Keyboard Navigation: Tab through all interactive elements
 * - Color Contrast: WCAG AA compliant color combinations
 * - Form Validation: Clear error messages
 * - Focus Management: Visual focus indicators
 * - Button States: Disabled state clearly indicated
 */
export const Example9_Accessibility = () => (
  <div>
    <h2>Accessibility</h2>
    <ul>
      <li>Semantic HTML with proper labels</li>
      <li>ARIA attributes for screen readers</li>
      <li>Keyboard navigation support</li>
      <li>WCAG AA color contrast</li>
      <li>Clear error messages</li>
      <li>Focus indicators</li>
    </ul>
    <UnsubscribePage />
  </div>
);

/**
 * Example 10: Routing Setup
 *
 * How to integrate the component in your application:
 *
 * Option 1: React Router v6
 * ```tsx
 * import { createBrowserRouter } from 'react-router-dom';
 * import { UnsubscribePage } from '@/pages/UnsubscribePage';
 *
 * const router = createBrowserRouter([
 *   {
 *     path: '/unsubscribe',
 *     element: <UnsubscribePage />,
 *   },
 * ]);
 * ```
 *
 * Option 2: With Layout
 * ```tsx
 * {
 *   path: '/unsubscribe',
 *   element: <MainLayout><UnsubscribePage /></MainLayout>,
 * }
 * ```
 *
 * Option 3: Standalone (No auth required)
 * ```tsx
 * {
 *   path: '/unsubscribe',
 *   element: <UnsubscribePage />,
 *   // Don't wrap with ProtectedRoute - this is a public page
 * }
 * ```
 */
export const Example10_RoutingSetup = () => (
  <div>
    <h2>Routing Setup</h2>
    <p>Add to your router configuration:</p>
    <code>
      {`{
  path: '/unsubscribe',
  element: <UnsubscribePage />
}`}
    </code>
    <p>No ProtectedRoute wrapper needed - this is a public page</p>
    <UnsubscribePage />
  </div>
);
