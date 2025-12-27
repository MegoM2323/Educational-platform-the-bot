import React from 'react';
import { ExportButton } from './ExportButton';

/**
 * ExportButton Component Examples
 *
 * This file demonstrates various ways to use the ExportButton component
 * across the application.
 */

/**
 * Example 1: Basic Usage with Default Props
 *
 * Simple export button with default styling and full functionality
 */
export const BasicExportButton = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Basic Export</h2>
      <ExportButton />
    </div>
  );
};

/**
 * Example 2: Compact Export Button
 *
 * Smaller button suitable for compact layouts like tables or toolbars
 */
export const CompactExportButton = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Compact Export</h2>
      <ExportButton size="sm" variant="outline" showHistory={false} />
    </div>
  );
};

/**
 * Example 3: Export Button with Callback
 *
 * Demonstrates handling export completion events
 */
export const ExportWithCallback = () => {
  const handleExportComplete = (jobId: string) => {
    console.log('Export initiated with job ID:', jobId);
    // You can trigger additional actions here:
    // - Show a notification
    // - Update parent component state
    // - Log analytics
  };

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Export with Callback</h2>
      <ExportButton onExportComplete={handleExportComplete} />
    </div>
  );
};

/**
 * Example 4: Secondary Variant
 *
 * For less prominent export actions
 */
export const SecondaryExportButton = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Secondary Style</h2>
      <ExportButton variant="secondary" />
    </div>
  );
};

/**
 * Example 5: Ghost Variant (Minimal)
 *
 * For toolbar or inline contexts
 */
export const GhostExportButton = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Ghost Style (Minimal)</h2>
      <ExportButton variant="ghost" size="sm" />
    </div>
  );
};

/**
 * Example 6: Hide History Option
 *
 * When you don't want users to see export history
 */
export const ExportWithoutHistory = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Without History</h2>
      <ExportButton showHistory={false} />
    </div>
  );
};

/**
 * Example 7: Large Button
 *
 * For prominent actions on dashboards
 */
export const LargeExportButton = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Large Button</h2>
      <ExportButton size="lg" variant="default" />
    </div>
  );
};

/**
 * Example 8: In a Toolbar Context
 *
 * Shows how to use ExportButton alongside other action buttons
 */
export const ExportButtonInToolbar = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">In Toolbar</h2>
      <div className="flex gap-2 items-center p-3 bg-gray-100 rounded-lg">
        <span className="text-sm font-medium text-gray-700">Data Actions:</span>
        <ExportButton size="sm" variant="outline" showHistory={false} />
        {/* Other action buttons would go here */}
      </div>
    </div>
  );
};

/**
 * Example 9: In a Settings Page
 *
 * Demonstrates usage in a settings/preferences context
 */
export const ExportButtonInSettings = () => {
  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="border rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-2">Data Export</h3>
        <p className="text-gray-600 mb-4">
          Download your personal data in a structured format. Your data will be available for 7 days.
        </p>
        <ExportButton variant="default" />
      </div>
    </div>
  );
};

/**
 * Example 10: Responsive Layout
 *
 * Shows how ExportButton adapts to different screen sizes
 */
export const ResponsiveExportButton = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Responsive</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-600 mb-2">Mobile Size</p>
          <ExportButton size="sm" />
        </div>
        <div>
          <p className="text-sm text-gray-600 mb-2">Desktop Size</p>
          <ExportButton size="md" />
        </div>
      </div>
    </div>
  );
};

/**
 * Example 11: With Loading State
 *
 * Shows the button behavior during export
 */
export const ExportButtonWithLoadingState = () => {
  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">
        Loading State (automatic)
      </h2>
      <p className="text-sm text-gray-600 mb-4">
        The button automatically shows loading state during export initiation
      </p>
      <ExportButton />
    </div>
  );
};

/**
 * Example 12: Complete Admin Dashboard Usage
 *
 * Real-world scenario showing ExportButton in an admin context
 */
export const AdminDashboardExample = () => {
  const [lastExportTime, setLastExportTime] = React.useState<Date | null>(null);

  return (
    <div className="p-6 bg-white rounded-lg border">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-2xl font-bold mb-2">System Data Management</h2>
          <p className="text-gray-600">
            Export system data for backups, compliance, or analysis
          </p>
        </div>
        <ExportButton
          onExportComplete={(jobId) => {
            setLastExportTime(new Date());
            console.log('Export job started:', jobId);
          }}
          variant="default"
        />
      </div>

      {lastExportTime && (
        <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800">
          Last export initiated: {lastExportTime.toLocaleString()}
        </div>
      )}
    </div>
  );
};

/**
 * Export All Examples
 *
 * This object maps example names to components for use in storybook or demo pages
 */
export const ExportButtonExamples = {
  'Basic Usage': <BasicExportButton />,
  'Compact Size': <CompactExportButton />,
  'With Callback': <ExportWithCallback />,
  'Secondary Style': <SecondaryExportButton />,
  'Ghost Style': <GhostExportButton />,
  'Without History': <ExportWithoutHistory />,
  'Large Button': <LargeExportButton />,
  'In Toolbar': <ExportButtonInToolbar />,
  'In Settings': <ExportButtonInSettings />,
  'Responsive': <ResponsiveExportButton />,
  'Loading States': <ExportButtonWithLoadingState />,
  'Admin Dashboard': <AdminDashboardExample />,
};

/**
 * Default export for use as a standalone demo component
 */
export default function ExportButtonShowcase() {
  const [selectedExample, setSelectedExample] = React.useState<string>(
    'Basic Usage'
  );

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">ExportButton Component</h1>
          <p className="text-gray-600">
            Reusable export functionality with format selection, download progress,
            and export history management
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Example Selector */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg border p-4 sticky top-4">
              <h3 className="font-semibold mb-3">Examples</h3>
              <nav className="space-y-2">
                {Object.keys(ExportButtonExamples).map((name) => (
                  <button
                    key={name}
                    onClick={() => setSelectedExample(name)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition ${
                      selectedExample === name
                        ? 'bg-blue-100 text-blue-900 font-medium'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    {name}
                  </button>
                ))}
              </nav>
            </div>
          </div>

          {/* Example Display */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg border p-6">
              <h2 className="text-xl font-semibold mb-4">{selectedExample}</h2>
              <div className="border-t pt-4">
                {ExportButtonExamples[selectedExample as keyof typeof ExportButtonExamples]}
              </div>
            </div>
          </div>
        </div>

        {/* Documentation */}
        <div className="mt-8 bg-white rounded-lg border p-6">
          <h3 className="text-lg font-semibold mb-4">Component Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-2">Supported Formats</h4>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>✓ JSON (single file)</li>
                <li>✓ CSV (multiple files in ZIP)</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Export History</h4>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>✓ View previous exports</li>
                <li>✓ Download completed exports</li>
                <li>✓ Delete exports</li>
                <li>✓ Track status in real-time</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Download Management</h4>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>✓ Progress tracking</li>
                <li>✓ Large file support</li>
                <li>✓ Error handling</li>
                <li>✓ Automatic filename generation</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Customization</h4>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>✓ Multiple size variants</li>
                <li>✓ Multiple style variants</li>
                <li>✓ Optional history display</li>
                <li>✓ Completion callbacks</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
