import React from 'react';
import { NotificationBadge } from './NotificationBadge';

/**
 * NotificationBadge Component Examples
 *
 * Demonstrates different configurations and use cases of the NotificationBadge component
 */

export function NotificationBadgeExamples() {
  return (
    <div className="space-y-8 p-6 bg-gray-50">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">NotificationBadge Component</h1>
        <p className="text-gray-600">
          Real-time notification badge with unread count, animations, and preview functionality
        </p>
      </div>

      {/* Example 1: Basic Badge */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Basic Badge</h2>
        <p className="text-sm text-gray-600 mb-4">
          Simple badge showing unread notification count with real-time updates via WebSocket.
        </p>
        <div className="flex items-center gap-4 p-4 bg-gray-50 rounded border border-gray-200">
          <NotificationBadge />
        </div>
      </section>

      {/* Example 2: Icon Variant */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Icon Variant</h2>
        <p className="text-sm text-gray-600 mb-4">
          Compact icon-only variant with bell icon and badge overlay. Perfect for navigation headers.
        </p>
        <div className="flex items-center gap-8 p-4 bg-gray-50 rounded border border-gray-200">
          <NotificationBadge variant="icon" />
          <NotificationBadge variant="icon" className="opacity-60" />
        </div>
      </section>

      {/* Example 3: Compact Variant */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Compact Variant</h2>
        <p className="text-sm text-gray-600 mb-4">
          Minimal badge variant showing just the count. Good for space-constrained areas.
        </p>
        <div className="flex items-center gap-4 p-4 bg-gray-50 rounded border border-gray-200">
          <NotificationBadge variant="compact" />
        </div>
      </section>

      {/* Example 4: With Preview */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">With Preview (Hover)</h2>
        <p className="text-sm text-gray-600 mb-4">
          Shows a popover preview of the latest notifications when hovering. Hover over the badge below.
        </p>
        <div className="p-4 bg-gray-50 rounded border border-gray-200 min-h-64">
          <NotificationBadge showPreview={true} previewCount={3} />
        </div>
      </section>

      {/* Example 5: Without Preview */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Without Preview</h2>
        <p className="text-sm text-gray-600 mb-4">
          Badge without hover preview. Use when preview is not needed or in compact layouts.
        </p>
        <div className="flex items-center gap-4 p-4 bg-gray-50 rounded border border-gray-200">
          <NotificationBadge showPreview={false} />
        </div>
      </section>

      {/* Example 6: Show Zero Unread */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Show Zero Count</h2>
        <p className="text-sm text-gray-600 mb-4">
          Display badge even when there are no unread notifications. Useful for consistent layout.
        </p>
        <div className="flex items-center gap-4 p-4 bg-gray-50 rounded border border-gray-200">
          <NotificationBadge showZero={true} />
        </div>
      </section>

      {/* Example 7: Different Preview Counts */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Preview Count Variations</h2>
        <p className="text-sm text-gray-600 mb-4">
          Control how many notifications appear in the preview. Hover to see the difference.
        </p>
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded border border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">previewCount={'{1}'}</p>
            <NotificationBadge showPreview={true} previewCount={1} />
          </div>
          <div className="p-4 bg-gray-50 rounded border border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">previewCount={'{3}'}</p>
            <NotificationBadge showPreview={true} previewCount={3} />
          </div>
          <div className="p-4 bg-gray-50 rounded border border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">previewCount={'{5}'}</p>
            <NotificationBadge showPreview={true} previewCount={5} />
          </div>
        </div>
      </section>

      {/* Example 8: Usage in Header */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">In Header Layout</h2>
        <p className="text-sm text-gray-600 mb-4">
          Typical use case in a navigation header. Icon variant works best in this context.
        </p>
        <div className="bg-gray-900 text-white p-4 rounded flex items-center justify-between">
          <div className="font-semibold">Dashboard</div>
          <div className="flex items-center gap-4">
            <NotificationBadge variant="icon" />
            <div className="w-8 h-8 bg-gray-700 rounded-full"></div>
          </div>
        </div>
      </section>

      {/* Example 9: Multiple Variants Together */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Variant Comparison</h2>
        <p className="text-sm text-gray-600 mb-4">
          All three variants showing the same notification count for comparison.
        </p>
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded border border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">variant="default"</p>
            <NotificationBadge variant="default" showPreview={false} />
          </div>
          <div className="p-4 bg-gray-50 rounded border border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">variant="icon"</p>
            <NotificationBadge variant="icon" />
          </div>
          <div className="p-4 bg-gray-50 rounded border border-gray-200">
            <p className="text-xs font-medium text-gray-600 mb-2">variant="compact"</p>
            <NotificationBadge variant="compact" />
          </div>
        </div>
      </section>

      {/* Example 10: Custom Styling */}
      <section className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Custom Styling</h2>
        <p className="text-sm text-gray-600 mb-4">
          Apply custom CSS classes through the className prop for tailored styling.
        </p>
        <div className="space-y-4">
          <div className="p-4 bg-gray-50 rounded border border-gray-200">
            <NotificationBadge className="text-lg" variant="compact" />
          </div>
        </div>
      </section>

      {/* Features Documentation */}
      <section className="bg-blue-50 rounded-lg p-6 border border-blue-200">
        <h2 className="text-lg font-semibold text-blue-900 mb-4">Features</h2>
        <ul className="space-y-2 text-sm text-blue-800">
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Real-time unread count with WebSocket updates</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Animated pulse effect on new notifications</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Hover preview with latest notifications</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Type-based color coding in preview</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Responsive sizing (desktop/tablet/mobile)</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Three variant options (default, icon, compact)</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Offline detection and auto-reconnection</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-blue-600 font-bold">✓</span>
            <span>Count capping with 99+ indicator</span>
          </li>
        </ul>
      </section>

      {/* API Documentation */}
      <section className="bg-amber-50 rounded-lg p-6 border border-amber-200">
        <h2 className="text-lg font-semibold text-amber-900 mb-4">Component Props</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-amber-900">
            <thead className="border-b border-amber-200">
              <tr>
                <th className="text-left font-semibold py-2 px-3">Prop</th>
                <th className="text-left font-semibold py-2 px-3">Type</th>
                <th className="text-left font-semibold py-2 px-3">Default</th>
                <th className="text-left font-semibold py-2 px-3">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-amber-200">
              <tr>
                <td className="py-2 px-3 font-mono text-xs">className</td>
                <td className="py-2 px-3 font-mono text-xs">string</td>
                <td className="py-2 px-3 font-mono text-xs">-</td>
                <td className="py-2 px-3">Custom CSS classes</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-mono text-xs">showZero</td>
                <td className="py-2 px-3 font-mono text-xs">boolean</td>
                <td className="py-2 px-3 font-mono text-xs">false</td>
                <td className="py-2 px-3">Show badge when count is 0</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-mono text-xs">showPreview</td>
                <td className="py-2 px-3 font-mono text-xs">boolean</td>
                <td className="py-2 px-3 font-mono text-xs">true</td>
                <td className="py-2 px-3">Show preview on hover</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-mono text-xs">previewCount</td>
                <td className="py-2 px-3 font-mono text-xs">number</td>
                <td className="py-2 px-3 font-mono text-xs">3</td>
                <td className="py-2 px-3">Number of notifications in preview</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-mono text-xs">variant</td>
                <td className="py-2 px-3 font-mono text-xs">enum</td>
                <td className="py-2 px-3 font-mono text-xs">default</td>
                <td className="py-2 px-3">Visual style (default, icon, compact)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Integration Guide */}
      <section className="bg-green-50 rounded-lg p-6 border border-green-200">
        <h2 className="text-lg font-semibold text-green-900 mb-4">Integration Guide</h2>
        <pre className="bg-green-900 text-green-100 p-4 rounded text-xs overflow-x-auto">
{`// 1. Import the component
import { NotificationBadge } from '@/components/notifications/NotificationBadge';

// 2. Add to header
<header>
  <nav className="flex justify-between items-center">
    <h1>App Name</h1>
    <NotificationBadge variant="icon" />
  </nav>
</header>

// 3. With custom configuration
<NotificationBadge
  variant="default"
  showPreview={true}
  previewCount={5}
  className="ml-auto"
/>

// 4. In a sidebar
<aside className="space-y-4">
  <div className="flex items-center gap-2">
    <span>Messages</span>
    <NotificationBadge variant="compact" showZero={false} />
  </div>
</aside>`}
        </pre>
      </section>
    </div>
  );
}

export default NotificationBadgeExamples;
