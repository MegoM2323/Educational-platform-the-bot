/**
 * Analytics Dashboard - Usage Examples
 *
 * This file demonstrates various ways to use the AnalyticsDashboard component
 * and its related components (ExportButton, MetricCard) with different
 * configurations and use cases.
 */

import React from 'react';
import { AnalyticsDashboard } from './AnalyticsDashboard';
import { ExportButton } from './ExportButton';
import { MetricCard } from './MetricCard';
import {
  Users,
  Target,
  Award,
  Zap,
  BookOpen,
  TrendingUp,
} from 'lucide-react';

/**
 * Example 1: Basic Dashboard with Default Settings
 *
 * Displays dashboard with default date range (last 30 days)
 * No filters applied.
 */
export const BasicDashboardExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <h1 className="text-3xl font-bold mb-6">Analytics Dashboard</h1>
      <AnalyticsDashboard />
    </div>
  );
};

/**
 * Example 2: Dashboard with Specific Date Range
 *
 * Shows dashboard for a specific date range (January 2025)
 */
export const DateRangeDashboardExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <h1 className="text-3xl font-bold mb-6">January 2025 Analytics</h1>
      <AnalyticsDashboard
        initialDateFrom="2025-01-01"
        initialDateTo="2025-01-31"
      />
    </div>
  );
};

/**
 * Example 3: Class-Specific Analytics
 *
 * Displays analytics for a specific class only
 */
export const ClassAnalyticsExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <h1 className="text-3xl font-bold mb-6">Mathematics 101 - Analytics</h1>
      <AnalyticsDashboard
        classId={5}
        initialDateFrom="2025-01-01"
        initialDateTo="2025-01-31"
      />
    </div>
  );
};

/**
 * Example 4: Student-Specific Analytics
 *
 * Shows analytics for a specific student
 * Useful for parent/guardian view
 */
export const StudentAnalyticsExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <h1 className="text-3xl font-bold mb-6">John Doe - Progress Analytics</h1>
      <AnalyticsDashboard
        studentId={42}
        initialDateFrom="2024-09-01"
        initialDateTo="2025-01-31"
      />
    </div>
  );
};

/**
 * Example 5: Combined Filters
 *
 * Shows analytics for specific class and date range
 */
export const FilteredDashboardExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <h1 className="text-3xl font-bold mb-6">
        Science 102 - Q4 2024 Performance
      </h1>
      <AnalyticsDashboard
        classId={8}
        initialDateFrom="2024-10-01"
        initialDateTo="2024-12-31"
      />
    </div>
  );
};

/**
 * Example 6: Export Button Usage
 *
 * Different ways to use the ExportButton component
 */
export const ExportButtonExamplesExample: React.FC = () => {
  const mockData = {
    students: [
      { name: 'John Doe', score: 95, progress: 95 },
      { name: 'Jane Smith', score: 90, progress: 90 },
      { name: 'Bob Johnson', score: 85, progress: 85 },
    ],
    class: 'Mathematics 101',
    period: 'January 2025',
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-4">Export Button Examples</h2>
      </div>

      {/* Example 1: Dropdown export */}
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">
          Dropdown Export (Multiple Formats)
        </h3>
        <ExportButton
          data={mockData}
          filename="analytics_report"
          formats={['csv', 'xlsx', 'json']}
          variant="outline"
        />
      </div>

      {/* Example 2: Single format CSV */}
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Single Format (CSV)</h3>
        <ExportButton
          data={mockData}
          filename="students_list"
          formats={['csv']}
          asDropdown={false}
          variant="default"
        />
      </div>

      {/* Example 3: API endpoint export */}
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">
          Export from API Endpoint
        </h3>
        <ExportButton
          endpoint="/api/reports/analytics-data/export/"
          queryParams={{ classId: 5, format: 'xlsx' }}
          filename="class_report_2025"
          formats={['csv', 'xlsx', 'pdf']}
          onExportSuccess={(format) =>
            console.log(`Successfully exported as ${format}`)
          }
          onExportError={(error, format) =>
            console.error(`Failed to export as ${format}:`, error)
          }
        />
      </div>

      {/* Example 4: Excel export with progress tracking */}
      <div className="border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">
          Excel Export with Progress
        </h3>
        <ExportButton
          endpoint="/api/reports/analytics-data/export/"
          queryParams={{ format: 'xlsx', includeCharts: true }}
          filename="comprehensive_analytics"
          formats={['xlsx']}
          showProgress={true}
          variant="secondary"
        />
      </div>
    </div>
  );
};

/**
 * Example 7: MetricCard Usage
 *
 * Various configurations of the MetricCard component
 */
export const MetricCardExamplesExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <h1 className="text-3xl font-bold mb-8">MetricCard Examples</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Simple metric */}
        <MetricCard
          title="Total Students"
          value={128}
          icon={Users}
          description="All enrolled students"
        />

        {/* Percentage metric with trend */}
        <MetricCard
          title="Completion Rate"
          value={82}
          format="percentage"
          icon={Target}
          trend={{ value: 12, isPositive: true, label: 'vs last month' }}
        />

        {/* Score metric with badges */}
        <MetricCard
          title="Average Score"
          value={74.5}
          format="percentage"
          decimals={1}
          icon={Award}
          badges={[
            { label: 'Max', value: 98, variant: 'default' },
            { label: 'Min', value: 45, variant: 'outline' },
          ]}
        />

        {/* Engagement metric with negative trend */}
        <MetricCard
          title="Engagement Level"
          value={68}
          format="percentage"
          icon={Zap}
          trend={{ value: 3, isPositive: false, label: 'vs last week' }}
        />

        {/* Interactive metric */}
        <MetricCard
          title="Active Classes"
          value={12}
          icon={BookOpen}
          interactive
          onClick={() => console.log('Navigating to classes...')}
          footer="Click to view details"
        />

        {/* Metric with currency format */}
        <MetricCard
          title="Revenue"
          value={5250}
          format="currency"
          decimals={2}
          icon={TrendingUp}
          trend={{ value: 25, isPositive: true }}
        />

        {/* Metric with custom color */}
        <MetricCard
          title="Pending Tasks"
          value={14}
          icon={Target}
          bgColor="#fef2f2"
          badges={[{ label: 'High Priority', value: 5, variant: 'destructive' }]}
        />

        {/* Metric with footer content */}
        <MetricCard
          title="Monthly Growth"
          value={23}
          format="percentage"
          icon={TrendingUp}
          footer="Updated 2 hours ago"
          trend={{ value: 7, isPositive: true }}
        />
      </div>
    </div>
  );
};

/**
 * Example 8: Custom Dashboard Layout
 *
 * Building a custom analytics layout using dashboard components
 */
export const CustomLayoutExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background">
      {/* Header with export */}
      <div className="border-b bg-white p-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              January 2025 Performance Report
            </p>
          </div>
          <ExportButton
            endpoint="/api/reports/analytics-data/export/"
            queryParams={{ month: 'January', year: 2025 }}
            filename="january_report"
            formats={['csv', 'xlsx', 'pdf']}
          />
        </div>
      </div>

      {/* Main content */}
      <div className="p-6">
        {/* KPI Summary */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">Key Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard
              title="Total Students"
              value={450}
              icon={Users}
            />
            <MetricCard
              title="Avg Progress"
              value={68.5}
              format="percentage"
              icon={Target}
            />
            <MetricCard
              title="Avg Score"
              value={72}
              format="percentage"
              icon={Award}
            />
            <MetricCard
              title="Engagement"
              value={75.3}
              format="percentage"
              icon={Zap}
            />
          </div>
        </div>

        {/* Full Dashboard */}
        <AnalyticsDashboard
          initialDateFrom="2025-01-01"
          initialDateTo="2025-01-31"
        />
      </div>
    </div>
  );
};

/**
 * Example 9: Teacher Dashboard View
 *
 * Customized view for teachers showing their class analytics
 */
export const TeacherDashboardExample: React.FC = () => {
  // Teacher's class ID would come from user context
  const teacherClassId = 5;
  const currentMonth = new Date();
  const dateFrom = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
  const dateTo = new Date(
    currentMonth.getFullYear(),
    currentMonth.getMonth() + 1,
    0
  );

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Class Analytics</h1>
        <p className="text-muted-foreground">
          Mathematics 101 - Performance Overview
        </p>
      </div>

      <AnalyticsDashboard
        classId={teacherClassId}
        initialDateFrom={dateFrom.toISOString().split('T')[0]}
        initialDateTo={dateTo.toISOString().split('T')[0]}
      />
    </div>
  );
};

/**
 * Example 10: Admin System-Wide Analytics
 *
 * System-wide analytics for administrators
 */
export const AdminAnalyticsExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">System Analytics</h1>
        <p className="text-muted-foreground">
          Platform-wide performance and engagement metrics
        </p>
      </div>

      {/* No filters - shows all data */}
      <AnalyticsDashboard />
    </div>
  );
};

// Export all examples
export default {
  BasicDashboardExample,
  DateRangeDashboardExample,
  ClassAnalyticsExample,
  StudentAnalyticsExample,
  FilteredDashboardExample,
  ExportButtonExamplesExample,
  MetricCardExamplesExample,
  CustomLayoutExample,
  TeacherDashboardExample,
  AdminAnalyticsExample,
};
