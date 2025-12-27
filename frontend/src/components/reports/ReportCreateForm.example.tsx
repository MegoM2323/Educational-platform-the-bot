/**
 * ReportCreateForm Usage Examples
 *
 * This file demonstrates how to use the ReportCreateForm component
 * in different scenarios.
 */

import { ReportCreateForm, GeneratedReport } from './ReportCreateForm';
import { useNavigate } from 'react-router-dom';

/**
 * Example 1: Basic usage without filters
 */
export const BasicReportFormExample = () => {
  const navigate = useNavigate();

  const handleSuccess = (report: GeneratedReport) => {
    console.log('Report created:', report);
    // Navigate to report detail page
    navigate(`/reports/${report.id}`);
  };

  const handleCancel = () => {
    navigate(-1);
  };

  return (
    <div className="p-8">
      <ReportCreateForm
        onSuccess={handleSuccess}
        onCancel={handleCancel}
      />
    </div>
  );
};

/**
 * Example 2: With student filtering
 */
export const ReportFormWithStudentsExample = () => {
  const students = [
    { id: 1, name: 'John Doe' },
    { id: 2, name: 'Jane Smith' },
    { id: 3, name: 'Bob Johnson' },
  ];

  const handleSuccess = (report: GeneratedReport) => {
    console.log('Report created:', report);
  };

  return (
    <div className="p-8">
      <ReportCreateForm
        students={students}
        onSuccess={handleSuccess}
      />
    </div>
  );
};

/**
 * Example 3: With class filtering
 */
export const ReportFormWithClassesExample = () => {
  const classes = [
    { id: 1, name: '9A' },
    { id: 2, name: '9B' },
    { id: 3, name: '10A' },
  ];

  return (
    <div className="p-8">
      <ReportCreateForm classes={classes} />
    </div>
  );
};

/**
 * Example 4: With both student and class filters
 */
export const ReportFormWithAllFiltersExample = () => {
  const students = [
    { id: 1, name: 'John Doe' },
    { id: 2, name: 'Jane Smith' },
  ];

  const classes = [
    { id: 1, name: '9A' },
    { id: 2, name: '9B' },
  ];

  const handleSuccess = (report: GeneratedReport) => {
    console.log('Report created:', report);
    // Show success message
    alert(`Report "${report.name}" created successfully!`);
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <ReportCreateForm
        students={students}
        classes={classes}
        onSuccess={handleSuccess}
      />
    </div>
  );
};

/**
 * Example 5: In a dialog/modal
 */
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useState } from 'react';

export const ReportFormInDialogExample = () => {
  const [isOpen, setIsOpen] = useState(false);

  const handleSuccess = (report: GeneratedReport) => {
    console.log('Report created:', report);
    setIsOpen(false);
  };

  return (
    <>
      <button onClick={() => setIsOpen(true)}>Create Report</button>

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create Custom Report</DialogTitle>
          </DialogHeader>
          <ReportCreateForm
            onSuccess={handleSuccess}
            onCancel={() => setIsOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

/**
 * Example 6: Responsive layout with sidebar
 */
export const ReportFormResponsiveExample = () => {
  const students = [
    { id: 1, name: 'Student 1' },
    { id: 2, name: 'Student 2' },
  ];

  return (
    <div className="flex gap-4">
      {/* Sidebar */}
      <aside className="hidden md:block w-64 bg-muted p-4 rounded-lg">
        <h3 className="font-bold mb-4">Instructions</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>1. Select a report template</li>
          <li>2. Enter report name</li>
          <li>3. Select date range</li>
          <li>4. (Optional) Filter by student/class</li>
          <li>5. Click "Create Report"</li>
        </ul>
      </aside>

      {/* Form */}
      <main className="flex-1 min-w-0">
        <ReportCreateForm students={students} />
      </main>
    </div>
  );
};
